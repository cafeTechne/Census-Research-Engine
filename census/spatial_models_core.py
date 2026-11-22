# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 93 spatial models with ACS uncertainty (frozen with the criterion,
docs/audits/spatial_models_validation_criterion.md).

Walker, *Analyzing US Census Data* (2023), chapter 8: geographically weighted regression (exploratory, with
collinearity and edge-effect caveats), geodemographic classification (k-means on principal components),
regionalization (SKATER) and diversity indices.

- R1 GWR (Brunsdon, Fotheringham and Charlton 1996): Gaussian kernel on distances (km), fixed bandwidth chosen by
  AICc over a log grid; local coefficients b_i = (X'W_iX)^-1 X'W_i y with a heteroskedasticity-robust local variance
  C_i diag(e^2) C_i' (C_i = (X'W_iX)^-1 X'W_i; e the GWR residuals scaled by 1/(1 - h_jj)), which carries the
  ACS sampling error (heteroskedastic by area). Monte Carlo non-stationarity test for one coefficient: the variance
  of its local estimates against 99 permutations of the locations (bandwidth held at the observed choice).
- C1 geodemographic classification: k-means (k given in advance) on standardized principal components explaining
  >= 80% of variance, 20 k-means++ restarts. Stability: refit on each replicate data set, match labels to the main
  fit (Hungarian assignment on overlap), per-area share of replicates agreeing.
- C2 SKATER (Assuncao et al. 2006): minimum spanning tree of the neighbour graph with edge costs equal to attribute
  distances; k - 1 greedy cuts each maximizing the reduction in total within-region sum of squares, regions of at
  least ``min_size`` areas; same replicate stability.
- D1 entropy diversity index E = -sum_g p_g ln p_g (natural log; maximum ln G) per area, replicate SE; D1bc adds the
  second-order bias correction sum_g Var(p_g)/(2 p_g) (delta method, variances from replicates).
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats
from scipy.cluster.vq import kmeans2
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, minimum_spanning_tree

Z90 = stats.norm.ppf(.95)
SDR = 4/80


# ---------------------------------------------------------------- R1 GWR
def _design(X):
    X = np.asarray(X, float)
    return np.column_stack([np.ones(len(X)), X.reshape(len(X), -1)])


def _gwr_fit(y, X, D, bw):
    W = np.exp(-.5*(D/bw)**2)
    n, p = X.shape
    B = np.zeros((n, p)); S_diag = np.zeros(n); C = np.zeros((n, p, n))
    for i in range(n):
        XtW = X.T*W[i]
        A = np.linalg.solve(XtW @ X, XtW)          # p x n  (C_i)
        C[i] = A
        B[i] = A @ y
        S_diag[i] = X[i] @ A[:, i]
    return B, S_diag, C


def aicc(y, X, D, bw):
    B, s, _ = _gwr_fit(y, X, D, bw)
    e = y-np.sum(X*B, 1); n = len(y); tr = s.sum()
    sig = np.sqrt(np.sum(e**2)/n)
    return 2*n*np.log(sig)+n*np.log(2*np.pi)+n*(n+tr)/(n-2-tr)


def choose_bandwidth(y, X, D, grid=None):
    grid = grid if grid is not None else np.geomspace(np.percentile(D[D > 0], 2), np.percentile(D, 60), 15)
    scores = [aicc(y, X, D, b) for b in grid]
    return float(grid[int(np.nanargmin(scores))])


def gwr(y, X, D, bw: Optional[float] = None, perms: int = 99, test_col: int = 1, rng=None) -> Dict[str, Any]:
    y = np.asarray(y, float); Xd = _design(X); D = np.asarray(D, float)
    bw = bw or choose_bandwidth(y, Xd, D)
    B, s, C = _gwr_fit(y, Xd, D, bw)
    e = (y-np.sum(Xd*B, 1))/np.clip(1-s, .05, None)
    V = np.einsum("ipn,n,iqn->ipq", C, e**2, C)
    se = np.sqrt(np.clip(np.einsum("ipp->ip", V), 0, None))
    stat = float(np.var(B[:, test_col]))
    p = None
    if perms:
        rng = rng or np.random.default_rng(0)
        ge = 0
        for _ in range(perms):
            o = rng.permutation(len(y))
            Bp, _, _ = _gwr_fit(y[o], Xd[o], D, bw)
            ge += np.var(Bp[:, test_col]) >= stat
        p = (ge+1)/(perms+1)
    return dict(bandwidth_km=bw, coef=B, se=se, lower=B-Z90*se, upper=B+Z90*se, effective_params=float(s.sum()),
                nonstationarity_stat=stat, nonstationarity_p=p)


# ---------------------------------------------------------------- C1 / C2 classification
def _pcs(F, share=.8):
    Z = (F-F.mean(0))/F.std(0, ddof=1)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    k = int(np.searchsorted(np.cumsum(S**2)/np.sum(S**2), share)+1)
    return Z @ Vt[:k].T, (F.mean(0), F.std(0, ddof=1), Vt[:k])


def kmeans(F, k, rng, restarts=20):
    P, _ = _pcs(np.asarray(F, float))
    best, lab = np.inf, None
    for _ in range(restarts):
        c, l = kmeans2(P, k, minit="++", seed=rng)
        if len(np.unique(l)) < k:
            continue
        sse = sum(np.sum((P[l == j]-c[j])**2) for j in range(k))
        if sse < best:
            best, lab = sse, l
    if lab is None:
        raise ValueError("k-means found no solution with k non-empty groups")
    return lab


def match_labels(ref, lab, k):
    M = np.zeros((k, k))
    for a, b in zip(ref, lab):
        M[a, b] += 1
    r, c = linear_sum_assignment(-M)
    mp = dict(zip(c, r))
    return np.array([mp[x] for x in lab])


def skater(F, edges: Sequence[Tuple[int, int]], k: int, min_size: int = 5) -> np.ndarray:
    P, _ = _pcs(np.asarray(F, float))
    n = len(P)
    i, j = np.array(edges).T
    cost = np.linalg.norm(P[i]-P[j], axis=1)+1e-12
    G = csr_matrix((cost, (i, j)), shape=(n, n))
    T = minimum_spanning_tree(G+G.T).tocoo()
    adj: List[set] = [set() for _ in range(n)]
    for a, b in zip(T.row.tolist(), T.col.tolist()):
        adj[a].add(b); adj[b].add(a)
    lab = connected_components(csr_matrix((np.ones(len(T.row)), (T.row, T.col)), shape=(n, n)), directed=False)[1]
    sq = np.sum(P**2, 1)

    def ssd(cnt, sm, ss):
        return ss-float(sm @ sm)/cnt if cnt else 0.0
    while len(np.unique(lab)) < k:
        best = None
        for r in np.unique(lab):
            nodes = np.flatnonzero(lab == r)
            if len(nodes) < 2*min_size:
                continue
            root = int(nodes[0]); order = [root]; parent = {root: -1}
            for u in order:                                  # breadth-first order
                for v in adj[u]:
                    if v not in parent:
                        parent[v] = u; order.append(v)
            cnt = {u: 1 for u in order}; sm = {u: P[u].copy() for u in order}; ss = {u: sq[u] for u in order}
            for u in reversed(order[1:]):                    # subtree aggregates
                pu = parent[u]
                cnt[pu] += cnt[u]; sm[pu] = sm[pu]+sm[u]; ss[pu] += ss[u]
            N, S, Q = cnt[root], sm[root], ss[root]
            total = ssd(N, S, Q)
            for u in order[1:]:
                c = cnt[u]
                if min(c, N-c) < min_size:
                    continue
                gain = total-ssd(c, sm[u], ss[u])-ssd(N-c, S-sm[u], Q-ss[u])
                if best is None or gain > best[0]:
                    best = (gain, u, parent[u], order)
        if best is None:
            raise ValueError("no further cut respects min_size")
        _, u, pu, order = best
        adj[u].discard(pu); adj[pu].discard(u)
        sub, todo = {u}, [u]                                  # nodes on u's side
        while todo:
            for v in adj[todo.pop()]:
                if v not in sub:
                    sub.add(v); todo.append(v)
        lab = lab.copy(); lab[list(sub)] = lab.max()+1
    _, lab = np.unique(lab, return_inverse=True)
    return lab


def stability(main, replicate_labels: Sequence[np.ndarray], k) -> np.ndarray:
    """Per-area share of replicate classifications agreeing with the main one (labels matched)."""
    agree = np.zeros(len(main))
    for lab in replicate_labels:
        agree += match_labels(main, lab, k) == main
    return agree/len(replicate_labels)


def adjusted_rand(a, b) -> float:
    from math import comb
    ct = {}
    for x, y in zip(a, b):
        ct[(x, y)] = ct.get((x, y), 0)+1
    sa = {}; sb = {}
    for (x, y), v in ct.items():
        sa[x] = sa.get(x, 0)+v; sb[y] = sb.get(y, 0)+v
    idx = sum(comb(v, 2) for v in ct.values()); n = len(a)
    ea = sum(comb(v, 2) for v in sa.values()); eb = sum(comb(v, 2) for v in sb.values())
    exp = ea*eb/comb(n, 2); mx = (ea+eb)/2
    return float((idx-exp)/(mx-exp)) if mx != exp else 1.0


# ---------------------------------------------------------------- D1 diversity
def entropy(P):
    P = np.clip(np.asarray(P, float), 1e-12, 1)
    return -np.sum(P*np.log(P), axis=-1)


def diversity(P, P_reps, bias_correct=False) -> Dict[str, np.ndarray]:
    """P: (n, G) shares; P_reps: (R, n, G) replicate shares (SDR factor 4/R)."""
    P = np.asarray(P, float); Pr = np.asarray(P_reps, float)
    f = 4/Pr.shape[0]
    E = entropy(P); Er = entropy(Pr)
    if bias_correct:
        varp = f*np.sum((Pr-P)**2, 0)
        corr = np.sum(varp/(2*np.clip(P, 1e-6, None)), -1)
        E, Er = E+corr, Er+corr
    se = np.sqrt(f*np.sum((Er-E)**2, 0))
    return dict(estimate=E, se=se, lower=E-Z90*se, upper=E+Z90*se)

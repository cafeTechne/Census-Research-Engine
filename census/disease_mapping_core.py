# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 96 frozen core: BYM2 Poisson disease mapping with a Laplace approximation (backlog N73; Moraga 2023,
chapters 9-10; Riebler et al. 2016; Besag, York and Mollie 1991).

Model: y_i ~ Poisson(E_i theta_i), log theta_i = x_i' beta + b_i, b = sigma (sqrt(1 - phi) v + sqrt(phi) u*), v iid
N(0, I), u* the intrinsic CAR field scaled so the geometric mean of its marginal variances is 1 (Sorbye and Rue
2014), with the sum-to-zero constraint (the intercept carries the mean). Hence b ~ N(0, Sigma), Sigma =
sigma^2 ((1 - phi) I + phi Q*^+), computed in the eigenbasis of the scaled ICAR covariance Q*^+ (connected graph
required). beta has a vague N(0, 100^2 I) prior.

Laplace approximation for hyperparameters theta = (sigma, phi) on a fixed grid (sigma: 10 log-spaced values .03 to
1.5; phi: .05 .2 .35 .5 .65 .8 .95): Newton mode of the latent field z = (beta, b), log marginal likelihood
l(y | theta) ~= sum (y eta - E e^eta) - z'Qz/2 + log|Q|/2 - log|H|/2, H = A'WA + Q.
- B1 (empirical Bayes): theta at the grid maximum; eta_i ~ N(eta_hat_i, a_i' H^-1 a_i).
- B2 (grid integration): mixture over the grid with weights proportional to exp(l), flat prior on the grid (grid
  points with weight below 1e-4 dropped and the rest renormalised); moments of eta_i matched to a normal.
Outputs per area: relative risk exp(eta_hat_i) - here exp(x_i'beta + b_i) - with 90% intervals exp(m +/- z s), and
exceedance probabilities P(theta_i > c) = 1 - Phi((log c - m)/s).
"""
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)
SIGMA_GRID = np.geomspace(.03, 1.5, 10)
PHI_GRID = np.array([.05, .2, .35, .5, .65, .8, .95])
BETA_PRIOR_SD = 100.0


def graph_components(n: int, edges: Sequence[Tuple[int, int]]):
    """Return list of sorted node-index lists, one per connected component of an undirected graph."""
    adj = [set() for _ in range(n)]
    for a, b in edges:
        if 0 <= a < n and 0 <= b < n and a != b:
            adj[a].add(b)
            adj[b].add(a)
    seen = [False] * n
    comps = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        comps.append(sorted(comp))
    return comps


def scaled_icar_eigen(n: int, edges: Sequence[Tuple[int, int]], *, allow_disconnected: bool = False):
    """Eigenvectors and eigenvalues of the scaled ICAR covariance Q*^+ (zero for each component's constant vector).

    When ``allow_disconnected=True`` (Round 200 / N132; Freni-Sterrantino et al. 2018), each connected
    component of size >= 2 is scaled independently to unit geometric-mean marginal variance, and isolated
    islands (size 1) receive zero structured variance (pure unstructured IID prior).
    """
    Q = np.zeros((n, n))
    for a, b in edges:
        if a != b:
            Q[a, b] = Q[b, a] = -1
    np.fill_diagonal(Q, 0); np.fill_diagonal(Q, -Q.sum(1))
    if not allow_disconnected:
        lam, V = np.linalg.eigh(Q)
        if np.sum(lam < 1e-8) != 1:
            raise ValueError("the neighbour graph must be connected (one component)")
        inv = np.where(lam > 1e-8, 1/np.where(lam > 1e-8, lam, 1), 0.0)
        marg = (V**2) @ inv
        s = np.exp(np.mean(np.log(marg)))
        return V, inv/s

    comps = graph_components(n, edges)
    if len(comps) == 1 and len(comps[0]) == n:
        return scaled_icar_eigen(n, edges, allow_disconnected=False)

    V_full = np.zeros((n, n), dtype=float)
    inv_full = np.zeros(n, dtype=float)
    col = 0
    for comp in comps:
        m = len(comp)
        idx = np.asarray(comp, dtype=int)
        if m == 1:
            V_full[idx[0], col] = 1.0
            inv_full[col] = 0.0
            col += 1
            continue
        Qc = Q[np.ix_(idx, idx)]
        lam_c, V_c = np.linalg.eigh(Qc)
        inv_c = np.where(lam_c > 1e-8, 1.0 / np.where(lam_c > 1e-8, lam_c, 1.0), 0.0)
        marg_c = (V_c ** 2) @ inv_c
        s_c = float(np.exp(np.mean(np.log(np.maximum(marg_c, 1e-300)))))
        V_full[idx[:, None], col + np.arange(m)[None, :]] = V_c
        inv_full[col : col + m] = inv_c / s_c
        col += m
    return V_full, inv_full


def _parts(X, V, lam, sigma, phi):
    n, p = X.shape
    d = sigma**2*((1-phi)+phi*lam)                       # Sigma = V diag(d) V'
    Qz = np.zeros((p+n, p+n)); Qz[:p, :p] = np.eye(p)/BETA_PRIOR_SD**2; Qz[p:, p:] = (V/d) @ V.T
    return d, Qz


def _fit(y, E, X, V, lam, sigma, phi, z0=None, iters=50):
    """Newton mode and Laplace log marginal likelihood (Cholesky); returns (ll, z, H factor)."""
    from scipy.linalg import cho_factor, cho_solve
    n, p = X.shape
    d, Qz = _parts(X, V, lam, sigma, phi)
    A = np.hstack([X, np.eye(n)])
    z = np.zeros(p+n) if z0 is None else z0.copy()
    if z0 is None:
        z[0] = np.log(max(y.sum(), .5)/E.sum())
    for _ in range(iters):
        eta = A @ z; mu = E*np.exp(eta)
        g = A.T @ (y-mu) - Qz @ z
        H = A.T @ (A*mu[:, None]) + Qz
        step = cho_solve(cho_factor(H), g)
        z += step
        if np.max(np.abs(step)) < 1e-8:
            break
    eta = A @ z; mu = E*np.exp(eta)
    H = A.T @ (A*mu[:, None]) + Qz
    cf = cho_factor(H)
    ldH = 2*np.sum(np.log(np.diag(cf[0])))
    ldQ = -p*2*np.log(BETA_PRIOR_SD) - np.sum(np.log(d))
    ll = float(np.sum(y*eta - mu) - z @ Qz @ z/2 + ldQ/2 - ldH/2)
    return ll, z, eta, cf, A


def _var(cf, A):
    from scipy.linalg import cho_solve
    return np.einsum("ij,ji->i", A, cho_solve(cf, A.T))


def bym2(y, E, X=None, eigen=None, edges=None) -> Dict[str, Dict[str, Any]]:
    """Both estimators from one grid pass: {"B1": ..., "B2": ...}."""
    y = np.asarray(y, float); E = np.asarray(E, float); n = len(y)
    X = np.ones((n, 1)) if X is None else np.column_stack([np.ones(n), np.asarray(X, float).reshape(n, -1)])
    V, lam = eigen if eigen is not None else scaled_icar_eigen(n, edges)
    fits, z0 = [], None
    for s in SIGMA_GRID:
        for ph in PHI_GRID:
            ll, z, eta, cf, A = _fit(y, E, X, V, lam, s, ph, z0)
            z0 = z
            fits.append([ll, s, ph, eta, cf, A])
    lls = np.array([f[0] for f in fits])
    k = int(np.argmax(lls))
    w = np.exp(lls-lls.max()); w /= w.sum()
    keep = np.flatnonzero(w > 1e-4)                         # negligible grid points do not affect the mixture
    w2 = w[keep]/w[keep].sum()
    var = {int(i): _var(fits[i][4], fits[i][5]) for i in set(keep.tolist()) | {k}}
    M = np.array([fits[i][3] for i in keep]); S2 = np.array([var[int(i)] for i in keep])
    m2 = w2 @ M; v2 = w2 @ (S2+M**2) - m2**2
    out = {}
    for name, m, v in (("B1", fits[k][3], var[k]), ("B2", m2, v2)):
        sd = np.sqrt(np.clip(v, 1e-12, None))
        out[name] = dict(log_rr=m, se=sd, rr=np.exp(m), lower=np.exp(m-Z90*sd), upper=np.exp(m+Z90*sd),
                         sigma=float(fits[k][1]), phi=float(fits[k][2]), loglik=float(lls[k]), method=name)
    return out


def exceedance(fit: Dict[str, Any], c: float) -> np.ndarray:
    return 1-stats.norm.cdf((np.log(c)-fit["log_rr"])/fit["se"])


def simulate_field(rng, eigen, sigma, phi):
    V, lam = eigen
    n = len(lam)
    u = V @ (np.sqrt(lam)*rng.standard_normal(n))
    return sigma*(np.sqrt(1-phi)*rng.standard_normal(n)+np.sqrt(phi)*u)

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 97 frozen core: spatial block cross-validation and MAUP sensitivity (backlog N74; Moraga 2023, chapters 11
and 16; Roberts et al. 2017; Openshaw 1984).

Scores of held-out predictions with predictive mean m and SD s: MAE, RMSE, 90% interval coverage, and the Gaussian
CRPS s (z (2 Phi(z) - 1) + 2 phi(z) - 1/sqrt(pi)), z = (y - m)/s.
Folds: V1 spatial blocks = k-means (k blocks, 20 restarts) on projected coordinates; V0 random = a random partition
into k equal folds.
Validation model ("ols_knn"): OLS of y on x, plus the mean OLS residual of the 5 nearest training areas; predictive
SD = the training RMSE of that predictor computed by leave-one-out within the training set.
MAUP sensitivity (S1): random contiguous zonings by cutting a random spanning tree of the neighbour graph into
zones of about ``size`` areas (greedy largest-subtree cuts); a declared statistic recomputed on population-weighted
zone means.
"""
from typing import Callable, Dict, Sequence, Tuple

import numpy as np
from scipy import stats
from scipy.cluster.vq import kmeans2
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree

Z90 = stats.norm.ppf(.95)


def scores(y, m, s) -> Dict[str, float]:
    y, m, s = map(lambda a: np.asarray(a, float), (y, m, s))
    z = (y-m)/s
    crps = s*(z*(2*stats.norm.cdf(z)-1)+2*stats.norm.pdf(z)-1/np.sqrt(np.pi))
    return dict(mae=float(np.mean(np.abs(y-m))), rmse=float(np.sqrt(np.mean((y-m)**2))),
                coverage=float(np.mean(np.abs(z) <= Z90)), crps=float(np.mean(crps)))


def block_folds(xy, k, rng) -> np.ndarray:
    best, lab = np.inf, None
    for _ in range(20):
        c, l = kmeans2(np.asarray(xy, float), k, minit="++", seed=rng)
        if len(np.unique(l)) < k:
            continue
        sse = sum(np.sum((xy[l == j]-c[j])**2) for j in range(k))
        if sse < best:
            best, lab = sse, l
    if lab is None:
        raise ValueError("could not form k spatial blocks")
    return lab


def random_folds(n, k, rng) -> np.ndarray:
    return rng.permutation(np.arange(n) % k)


def _knn_resid(xy_tr, r_tr, xy_te, k=5):
    D = np.hypot(xy_te[:, :1]-xy_tr[:, 0], xy_te[:, 1:]-xy_tr[:, 1])
    idx = np.argsort(D, 1)[:, :k]
    return r_tr[idx].mean(1)


def ols_knn_fit_predict(y_tr, X_tr, xy_tr, X_te, xy_te, k=5):
    """Prediction mean and SD for held-out areas (see module docstring)."""
    A = np.column_stack([np.ones(len(y_tr)), X_tr]); B = np.column_stack([np.ones(len(X_te)), X_te])
    beta = np.linalg.lstsq(A, y_tr, rcond=None)[0]
    r = y_tr-A @ beta
    # leave-one-out residual smoothing error within the training set (the predictive SD)
    D = np.hypot(xy_tr[:, :1]-xy_tr[:, 0], xy_tr[:, 1:]-xy_tr[:, 1]); np.fill_diagonal(D, np.inf)
    loo = r-r[np.argsort(D, 1)[:, :k]].mean(1)
    sd = float(np.sqrt(np.mean(loo**2)))
    return B @ beta+_knn_resid(xy_tr, r, xy_te, k), np.full(len(X_te), sd)


def cross_validate(y, X, xy, folds, fit_predict: Callable = ols_knn_fit_predict) -> Dict[str, float]:
    y = np.asarray(y, float); X = np.asarray(X, float).reshape(len(y), -1); xy = np.asarray(xy, float)
    m = np.zeros(len(y)); s = np.zeros(len(y))
    for f in np.unique(folds):
        te = folds == f; tr = ~te
        m[te], s[te] = fit_predict(y[tr], X[tr], xy[tr], X[te], xy[te])
    return scores(y, m, s)


def random_zoning(n, edges: Sequence[Tuple[int, int]], size: int, rng) -> np.ndarray:
    """Zone labels from a random spanning tree cut into contiguous zones of about ``size`` areas."""
    e = np.array(edges)
    w = rng.random(len(e))+1e-9
    T = minimum_spanning_tree(csr_matrix((w, (e[:, 0], e[:, 1])), shape=(n, n))).tocoo()
    adj = [set() for _ in range(n)]
    for a, b in zip(T.row.tolist(), T.col.tolist()):
        adj[a].add(b); adj[b].add(a)
    lab = -np.ones(n, int); zone = 0
    for root in range(n):
        if lab[root] >= 0:
            continue
        order, parent = [root], {root: -1}
        for u in order:
            for v in adj[u]:
                if v not in parent and lab[v] < 0:
                    parent[v] = u; order.append(v)
        cnt = {u: 1 for u in order}
        cut = set()
        for u in reversed(order[1:]):           # leaves up: a subtree becomes a zone once it reaches the target size
            if cnt[u] >= size:
                cut.add(u)                       # contributes nothing further up
            else:
                cnt[parent[u]] += cnt[u]
        for u in order:                          # label: walk down, new zone at the root and at each cut
            if u == root or u in cut:
                stack = [u]
                while stack:
                    x = stack.pop(); lab[x] = zone
                    stack += [v for v in adj[x] if parent.get(v) == x and v not in cut]
                zone += 1
    return lab


def zone_means(values, weights, labels):
    v = np.asarray(values, float); w = np.asarray(weights, float)
    k = labels.max()+1
    tw = np.bincount(labels, w, k)
    return np.bincount(labels, v*w, k)/tw, tw


def maup_slope(y, x, weights, labels) -> float:
    """Weighted least-squares slope of zone mean y on zone mean x (zones weighted by population)."""
    my, w = zone_means(y, weights, labels); mx, _ = zone_means(x, weights, labels)
    mxw, myw = np.average(mx, weights=w), np.average(my, weights=w)
    return float(np.sum(w*(mx-mxw)*(my-myw))/np.sum(w*(mx-mxw)**2))

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 35 corrected (EIV) slope inference under spatial dependence (PLAN_ROUND_35).

Frozen with the validation criterion. D: (R, n, k) replicate deviations of the design columns,
e: (R, n) replicate deviations of the outcome; f = 4/80. Fuller's estimator and sandwich are
census.models.fit_eiv's formulas.
"""
import numpy as np
from scipy import optimize, stats

F = 4/80


def fuller(X, y, D, e, f=F):
    X, y = np.asarray(X, float), np.asarray(y, float)
    n, k = X.shape
    S_sum = f*np.einsum("rnj,rnl->jl", D, D)
    s_sum = f*np.einsum("rnj,rn->j", D, e)
    M = X.T @ X-S_sum
    np.linalg.cholesky((M+M.T)/2)          # refuse a non-positive-definite corrected moment matrix
    b = np.linalg.solve(M, X.T @ y-s_sum)
    resid = y-X @ b
    s_i = f*np.einsum("rnj,rn->nj", D, e)
    Sb_i = f*np.einsum("rnj,rn->nj", D, D @ b)
    psi = X*resid[:, None]-(s_i-Sb_i)
    Minv = np.linalg.inv(M)
    return b, Minv @ (psi.T @ psi) @ Minv*n/(n-k)


def knn_weights(lon, lat, k=6):
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    d = 2*np.arcsin(np.sqrt(np.sin((lat[:, None]-lat[None, :])/2)**2
                            + np.cos(lat[:, None])*np.cos(lat[None, :])*np.sin((lon[:, None]-lon[None, :])/2)**2))
    np.fill_diagonal(d, np.inf)
    W = np.zeros_like(d)
    idx = np.argsort(d, axis=1, kind="stable")[:, :k]
    np.put_along_axis(W, idx, 1., axis=1)
    return W/W.sum(axis=1, keepdims=True)


def sem_lambda(X, y, W, eig):
    """ML of the spatial-error parameter (concentrated likelihood; log|I - lW| from eigenvalues)."""
    n = len(y)
    def negll(lam):
        B = np.eye(n)-lam*W
        Xw, yw = B @ X, B @ y
        r = yw-Xw @ np.linalg.lstsq(Xw, yw, rcond=None)[0]
        return n/2*np.log(r @ r/n)-np.sum(np.log(np.abs(1-lam*eig)))
    res = optimize.minimize_scalar(negll, bounds=(-.95, .95), method="bounded", options={"xatol": 1e-6})
    return float(res.x)


def g2(X, y, D, e, W, eig):
    lam = sem_lambda(X, y, W, eig)
    B = np.eye(len(y))-lam*W
    b, V = fuller(B @ X, B @ y, np.einsum("mn,rnj->rmj", B, D), e @ B.T)
    return b, V, lam


def g1(Xs, y, Ds, e, labels, f=F):
    """Xs: (n, q) slope columns; Ds: (R, n, q) their replicate deviations. Returns (8, q) corrected slopes."""
    Xs, y, labels = np.asarray(Xs, float), np.asarray(y, float), np.asarray(labels)
    groups = np.unique(labels)
    q = Xs.shape[1]
    Q = np.zeros((q, q)); Sw = np.zeros((q, q)); sw = np.zeros(q); b = []
    for g in groups:
        m = labels == g; ng = int(m.sum())
        if ng < max(5, q+2):
            raise ValueError("every cluster needs at least five areas")
        Xc = Xs[m]-Xs[m].mean(axis=0); yc = y[m]-y[m].mean()
        Q += Xc.T @ Xc
        Sw += (1-1/ng)*f*np.einsum("rnj,rnl->jl", Ds[:, m], Ds[:, m])
        sw += (1-1/ng)*f*np.einsum("rnj,rn->j", Ds[:, m], e[:, m])
        b.append(np.linalg.lstsq(Xc, yc, rcond=None)[0])
    M = Q-Sw
    np.linalg.cholesky((M+M.T)/2)
    A = np.linalg.solve(M, Q); c = np.linalg.solve(M, sw)
    return np.asarray(b) @ A.T-c


def im_summary(estimates, level=.90):
    est = np.asarray(estimates, float)
    G = len(est)
    mean, se = est.mean(axis=0), est.std(axis=0, ddof=1)/np.sqrt(G)
    crit = stats.t.ppf((1+level)/2, G-1)
    return dict(estimate=mean, se=se, lower=mean-crit*se, upper=mean+crit*se, df=G-1)

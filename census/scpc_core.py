# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 58 frozen core: SCPC spatial-correlation-robust inference (Mueller and Watson 2022, Econometrica 90(6)).

For a scalar parameter with influence values e_l at n locations with distances d (km):
- benchmark c0: mean_{l != k} exp(-c0 d_lk) = rho_bar;
- W: unit-norm eigenvectors of the q largest eigenvalues of M Sigma(c0) M (M demeans; Sigma(c) = exp(-c d));
- tau = (iota'e / sqrt(n)) / sqrt(q^-1 sum_j (w_j'e)^2);
- critical value: max over c in a grid of c >= c0 (30 log-spaced values up to an average correlation of 1e-4,
  plus independence) of the 1 - alpha quantile of |tau| when e ~ N(0, Sigma(c)), from Imhof's formula;
- q in 1..qmax minimises cv(q) E sqrt(chi2_q / q) (expected length under independence);
- interval: theta_hat +- cv sqrt(q^-1 sum_j (w_j'e)^2) / sqrt(n).
Influence values: OLS e_l = n [(X'X)^-1 x_l u_l]_j; binomial (trials) / Poisson (exposure) GLMs with canonical
links e_l = n [I^-1 x_l s_l]_j with s_l the score contribution.
"""
from functools import lru_cache

import numpy as np
from scipy import integrate, optimize, special, stats


def haversine(lon, lat):
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    dlon = lon[:, None]-lon[None, :]; dlat = lat[:, None]-lat[None, :]
    a = np.sin(dlat/2)**2+np.cos(lat[:, None])*np.cos(lat[None, :])*np.sin(dlon/2)**2
    return 2*6371.0088*np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _avg_corr(c, D, off):
    return float(np.exp(-c*D[off]).mean())


def benchmark_c(D, rho_bar):
    off = ~np.eye(len(D), dtype=bool)
    lo, hi = 1e-8, 1e3
    f = lambda lc: _avg_corr(np.exp(lc), D, off)-rho_bar
    return float(np.exp(optimize.brentq(f, np.log(lo), np.log(hi), xtol=1e-12)))


def _imhof_tail(lams):
    """P(sum lam_i chi2_1 > 0)."""
    lams = lams[np.abs(lams) > 1e-14]
    def integrand(u):
        theta = .5*np.sum(np.arctan(lams*u))
        rho = np.prod((1+(lams*u)**2)**.25)
        return np.sin(theta)/(u*rho)
    val, _ = integrate.quad(integrand, 0, np.inf, limit=500)
    return .5+val/np.pi


def _size(V, q, cv):
    """P(|tau| > cv) when (iota'e/sqrt n, W'e) ~ N(0, V)."""
    d = np.r_[1., -cv**2/q*np.ones(q)]
    L = np.linalg.cholesky(V+1e-12*np.eye(len(V)))
    lams = np.linalg.eigvalsh(L.T @ np.diag(d) @ L)
    return _imhof_tail(lams)


def _quantile(V, q, alpha):
    t = stats.t.ppf(1-alpha/2, q)
    f = lambda cv: _size(V, q, cv)-alpha
    hi = t
    while f(hi) > 0:
        hi *= 1.5
    lo = 1e-6 if f(1e-6) > 0 else 1e-6
    return float(optimize.brentq(f, lo, hi, xtol=1e-6))


def setup(D, rho_bar=.02, qmax=20, alpha=.10, grid=30, floor=1e-4):
    """Geometry-only part: W (n, q), cv, q, c0. Deterministic."""
    D = np.asarray(D, float); n = len(D)
    c0 = benchmark_c(D, rho_bar)
    c_end = benchmark_c(D, floor)
    cs = np.exp(np.linspace(np.log(c0), np.log(c_end), grid))
    M = np.eye(n)-1/n
    vals, vecs = np.linalg.eigh(M @ np.exp(-c0*D) @ M)
    order = np.argsort(vals)[::-1]
    Wall = vecs[:, order[:qmax]]
    B_all = np.column_stack((np.ones(n)/np.sqrt(n), Wall))
    Vs = [B_all.T @ np.exp(-c*D) @ B_all for c in cs]+[np.eye(qmax+1)]
    best = None
    for q in range(1, qmax+1):
        idx = np.r_[0, 1:q+1]
        cv = max(_quantile(V[np.ix_(idx, idx)], q, alpha) for V in Vs)
        elen = cv*np.sqrt(2/q)*np.exp(special.gammaln((q+1)/2)-special.gammaln(q/2))
        if best is None or elen < best[0]:
            best = (elen, q, cv)
    _, q, cv = best
    idx = np.r_[0, 1:q+1]
    return dict(W=Wall[:, :q], q=q, cv=cv, c0=c0, rho_bar=rho_bar, alpha=alpha,
                V=[V[np.ix_(idx, idx)] for V in Vs])   # grid covariances for p-values (Round 61)


def p_value(theta, e, S, null=0.):
    """Round 61: worst case over the benchmark grid of P(|tau| > |t|), t = (theta - null)/se (Imhof). Consistent
    with the interval: p < alpha exactly when the interval excludes ``null``."""
    e = np.asarray(e, float); n = len(e)
    s = float(np.sqrt(np.mean((S["W"].T @ e)**2))/np.sqrt(n))
    t = abs(float(theta)-null)/s
    return float(min(1., max(_size(V, S["q"], t) for V in S["V"])))


def interval(theta, e, S):
    e = np.asarray(e, float); n = len(e)
    s = float(np.sqrt(np.mean((S["W"].T @ e)**2))/np.sqrt(n))
    return dict(estimate=float(theta), se=s, lower=float(theta-S["cv"]*s), upper=float(theta+S["cv"]*s),
                q=S["q"], cv=S["cv"])


def influence(X, y, model, j=1, trials=None, exposure=None):
    """(theta_j, influence values) for OLS / binomial (y proportion, trials) / Poisson (counts, exposure)."""
    import statsmodels.api as sm
    X, y = np.asarray(X, float), np.asarray(y, float); n = len(y)
    if model == "linear":
        XtX = X.T @ X; b = np.linalg.solve(XtX, X.T @ y); u = y-X @ b
        e = n*(np.linalg.solve(XtX, (X*u[:, None]).T))[j]
        return float(b[j]), e
    if model == "binomial":
        r = sm.GLM(y, X, family=sm.families.Binomial(), var_weights=np.asarray(trials, float)).fit()
        p = r.fittedvalues; w = np.asarray(trials, float)
        info = X.T @ (X*(w*p*(1-p))[:, None]); s = X*(w*(y-p))[:, None]
    elif model == "poisson":
        r = sm.GLM(y, X, family=sm.families.Poisson(), offset=np.log(np.asarray(exposure, float))).fit()
        mu = r.fittedvalues
        info = X.T @ (X*mu[:, None]); s = X*(y-mu)[:, None]
    else:
        raise ValueError("model must be linear, binomial or poisson")
    if not r.converged:
        raise ValueError("GLM did not converge")
    e = n*np.linalg.solve(info, s.T)[j]
    return float(np.asarray(r.params)[j]), e

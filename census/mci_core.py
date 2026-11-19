# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 42 procedures (frozen with the criterion; PLAN_ROUND_42): multiple imputation of one incomplete
covariate (chained equations reduce to proper Bayesian regression imputation), an interval-censored
Poisson likelihood for hidden counts, and interrupted time-series regressions."""
import warnings

import numpy as np
import statsmodels.api as sm
from scipy import optimize, special, stats

Z90 = stats.norm.ppf(.95)


def _ci(b, se, crit=Z90):
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite estimate or SE")
    return dict(estimate=float(b), se=float(se), lower=float(b-crit*se), upper=float(b+crit*se))


def complete_case(y, X, j=1):
    ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
    r = sm.OLS(y[ok], X[ok]).fit(cov_type="HC3")
    return _ci(r.params[j], r.bse[j])


def multiple_imputation(y, X, miss_col, rng, m=20, j=1):
    """Impute X[:, miss_col] from the other columns and y (proper draws), fit OLS (HC3), Rubin's rules."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    miss = ~np.isfinite(X[:, miss_col]); obs = ~miss
    P = np.column_stack([np.delete(X, miss_col, axis=1), y])
    fit = sm.OLS(X[obs, miss_col], P[obs]).fit()
    n_obs, k = P[obs].shape
    XtX_inv = np.linalg.inv(P[obs].T @ P[obs])
    est, var = [], []
    for _ in range(m):
        sigma2 = fit.ssr/rng.chisquare(n_obs-k)
        beta = rng.multivariate_normal(fit.params, sigma2*XtX_inv)
        Xi = X.copy(); Xi[miss, miss_col] = P[miss] @ beta+rng.standard_normal(miss.sum())*np.sqrt(sigma2)
        r = sm.OLS(y, Xi).fit(cov_type="HC3")
        est.append(r.params[j]); var.append(r.bse[j]**2)
    qbar, ubar, bvar = np.mean(est), np.mean(var), np.var(est, ddof=1)
    T = ubar+(1+1/m)*bvar
    df = (m-1)*(1+ubar/((1+1/m)*bvar))**2 if bvar > 0 else np.inf
    return _ci(qbar, np.sqrt(T), stats.t.ppf(.95, df))


def _censored_loglik_obs(beta, y, X, logE, censored, lo=1, hi=9):
    mu = np.exp(logE+X @ beta)
    ll = np.where(censored, 0., y*np.log(mu)-mu-special.gammaln(y+1))
    pc = special.pdtr(hi, mu)-np.exp(-mu)                       # P(1 <= Y <= 9)
    return np.where(censored, np.log(np.clip(pc, 1e-300, None)), ll)


def censored_poisson(y, X, exposure, censored, j=1):
    """Interval-censored Poisson MLE (hidden counts in [1, 9]) with a sandwich (numerical score) SE."""
    y = np.where(censored, 0., np.asarray(y, float)); X = np.asarray(X, float); logE = np.log(np.asarray(exposure, float))
    obj = lambda b: -np.sum(_censored_loglik_obs(b, y, X, logE, censored))
    start = sm.GLM(y[~censored], X[~censored], family=sm.families.Poisson(), offset=logE[~censored]).fit().params
    res = optimize.minimize(obj, start, method="BFGS", options={"gtol": 1e-8, "maxiter": 1000})
    b = res.x
    eps = 1e-5; k = len(b)
    S = np.zeros((len(y), k)); H = np.zeros((k, k))
    for a in range(k):
        e = np.zeros(k); e[a] = eps
        S[:, a] = (_censored_loglik_obs(b+e, y, X, logE, censored)-_censored_loglik_obs(b-e, y, X, logE, censored))/(2*eps)
    for a in range(k):
        e = np.zeros(k); e[a] = eps
        ga = lambda bb: np.array([(_censored_loglik_obs(bb+np.eye(k)[c]*eps, y, X, logE, censored)
                                   - _censored_loglik_obs(bb-np.eye(k)[c]*eps, y, X, logE, censored)).sum()/(2*eps) for c in range(k)])
        H[:, a] = (ga(b+e)-ga(b-e))/(2*eps)
    Hinv = np.linalg.inv(-H)
    V = Hinv @ (S.T @ S) @ Hinv
    return _ci(b[j], np.sqrt(V[j, j]))


def poisson_complete_case(y, X, exposure, censored, j=1):
    keep = ~censored
    r = sm.GLM(y[keep], X[keep], family=sm.families.Poisson(), exposure=np.asarray(exposure)[keep]).fit(cov_type="HC3")
    return _ci(r.params[j], r.bse[j])


def its_design(T, start):
    t = np.arange(1, T+1, dtype=float); post = (t >= start).astype(float)
    return np.column_stack((np.ones(T), t, post, post*(t-start+1)))


def interrupted(y, X, method):
    """Returns intervals for the level change (column 2) and slope change (column 3)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if method == "ols":
            r = sm.OLS(y, X).fit()
        elif method == "hac":
            r = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        elif method == "ar1":
            r = sm.GLSAR(y, X, rho=1).iterative_fit(maxiter=20)
        else:
            raise ValueError("method must be ols, hac or ar1")
    crit = stats.t.ppf(.95, r.df_resid) if method != "hac" else Z90
    return [_ci(r.params[c], r.bse[c], crit) for c in (2, 3)]

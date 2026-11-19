# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 45 procedures (frozen with the criterion; PLAN_ROUND_45): interval-censored NB2, IM-8 count slopes,
and the fixed-offset count fits used to judge noisy exposures."""
import warnings

import numpy as np
import statsmodels.api as sm
from scipy import optimize, special, stats

Z90 = stats.norm.ppf(.95)


def _ci(b, se, crit=Z90):
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite estimate or SE")
    return dict(estimate=float(b), se=float(se), lower=float(b-crit*se), upper=float(b+crit*se))


def _nb_logpmf(y, mu, r):
    return special.gammaln(y+r)-special.gammaln(r)-special.gammaln(y+1)+r*np.log(r/(r+mu))+y*np.log(mu/(r+mu))


def _censored_nb_obs(theta, y, X, logE, censored, lo=1, hi=9):
    beta, r = theta[:-1], np.exp(-theta[-1])            # theta[-1] = log alpha; r = 1/alpha
    mu = np.exp(logE+X @ beta)
    full = _nb_logpmf(y, mu, r)
    p = r/(r+mu)
    pc = special.betainc(r, hi+1, p)-np.exp(r*np.log(p))  # P(Y <= 9) - P(Y = 0) for NB(r, p)
    return np.where(censored, np.log(np.clip(pc, 1e-300, None)), full)


def nb2_fit(y, X, exposure):
    """NB2 maximum likelihood (statsmodels BFGS; Nelder-Mead fallback as census.count_models, Round 44)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.NegativeBinomial(y, X, exposure=exposure)
        fit = model.fit(disp=0, maxiter=200)
        if not (fit.mle_retvals.get("converged", False) and np.all(np.isfinite(fit.params))):
            nm = model.fit(start_params=fit.params, method="nm", disp=0, maxiter=20000)
            fit = model.fit(start_params=nm.params, method="bfgs", disp=0, maxiter=2000)
            if not (fit.mle_retvals.get("converged", False) and np.all(np.isfinite(fit.params))):
                fit = nm
        if not (fit.mle_retvals.get("converged", False) and np.all(np.isfinite(fit.params)) and fit.params[-1] > 0):
            raise ValueError("NB alpha did not converge")
    return np.asarray(fit.params, float)


def _sandwich(f_obs, theta):
    k = len(theta); eps = 1e-5
    S = np.zeros((len(f_obs(theta)), k))
    for a in range(k):
        e = np.zeros(k); e[a] = eps
        S[:, a] = (f_obs(theta+e)-f_obs(theta-e))/(2*eps)
    def grad(t):
        return np.array([(f_obs(t+np.eye(k)[c]*eps)-f_obs(t-np.eye(k)[c]*eps)).sum()/(2*eps) for c in range(k)])
    H = np.zeros((k, k))
    for a in range(k):
        e = np.zeros(k); e[a] = eps
        H[:, a] = (grad(theta+e)-grad(theta-e))/(2*eps)
    Hinv = np.linalg.inv(-(H+H.T)/2)
    return Hinv @ (S.T @ S) @ Hinv


def censored_negbin(y, X, exposure, censored, j=1):
    """K1a: interval-censored NB2 (hidden counts in [1, 9]) with a numerical sandwich."""
    y = np.where(censored, 0., np.asarray(y, float)); X = np.asarray(X, float)
    E = np.asarray(exposure, float); logE = np.log(E)
    keep = ~censored
    start = nb2_fit(y[keep], X[keep], E[keep])
    theta0 = np.r_[start[:-1], np.log(start[-1])]
    f_obs = lambda t: _censored_nb_obs(t, y, X, logE, censored)
    res = optimize.minimize(lambda t: -np.sum(f_obs(t)), theta0, method="BFGS", options={"gtol": 1e-7, "maxiter": 2000})
    if not np.all(np.isfinite(res.x)):
        raise ValueError("censored NB2 did not converge")
    V = _sandwich(f_obs, res.x)
    return _ci(res.x[j], np.sqrt(V[j, j]))


def negbin_hc3(y, X, exposure, j=1):
    """NB2-HC3 (alpha by ML, then GLM with HC3): K1c (complete case), K2c, K3a."""
    alpha = nb2_fit(y, X, exposure)[-1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), exposure=exposure).fit(cov_type="HC3")
    return _ci(np.asarray(r.params)[j], np.asarray(r.bse)[j])


def poisson_hc3(y, X, exposure, j=1):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = sm.GLM(y, X, family=sm.families.Poisson(), exposure=exposure).fit(cov_type="HC3")
    return _ci(np.asarray(r.params)[j], np.asarray(r.bse)[j])


def im_counts(y, X, exposure, labels, family, j=1):
    """K2a/K2b: IM-8 mean of per-cluster slopes, t(G-1). Columns constant within a cluster are dropped there.

    family 'negbin': alpha from the full-sample NB2 ML, then each cluster's NB GLM with that alpha;
    'poisson': each cluster's Poisson GLM."""
    y, X, E = np.asarray(y, float), np.asarray(X, float), np.asarray(exposure, float)
    fam = (sm.families.NegativeBinomial(alpha=nb2_fit(y, X, E)[-1]) if family == "negbin" else sm.families.Poisson())
    slopes = []
    for g in np.unique(labels):
        m = labels == g
        cols = [0]+[c for c in range(1, X.shape[1]) if np.ptp(X[m, c]) > 0]
        if j not in cols:
            raise ValueError("slope column constant within a cluster")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = sm.GLM(y[m], X[m][:, cols], family=fam, exposure=E[m]).fit()
        b = float(np.asarray(r.params)[cols.index(j)])
        if not np.isfinite(b):
            raise ValueError("non-finite cluster slope")
        slopes.append(b)
    slopes = np.array(slopes); G = len(slopes)
    return _ci(slopes.mean(), slopes.std(ddof=1)/np.sqrt(G), stats.t.ppf(.95, G-1))

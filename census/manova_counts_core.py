# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 39 procedures (frozen with the criterion; PLAN_ROUND_39): a multivariate wild score bootstrap
for group effects on several outcomes, Pillai's trace (comparison), and count-model slope fits."""
import warnings

import numpy as np
import statsmodels.api as sm
from scipy import stats

DRAWS = 399


def _contrib(X, Y, test):
    """Per-area restricted-score contributions stacked over outcomes: (n, q*m)."""
    keep = np.setdiff1d(np.arange(X.shape[1]), test)
    Xr = X[:, keep]
    R = Y-Xr @ np.linalg.lstsq(Xr, Y, rcond=None)[0]
    Jinv = np.linalg.inv(X.T @ X)
    return np.concatenate([(Jinv @ (X*R[:, [j]]).T)[test].T for j in range(Y.shape[1])], axis=1)


def stacked_coefficients(X, Y, test):
    B = np.linalg.lstsq(X, Y, rcond=None)[0]
    return B[test].T.ravel()                     # outcome-major, matching _contrib


def mv_wild_score(X, Y, test, V_sampling, rng, draws=DRAWS):
    a = _contrib(np.asarray(X, float), np.asarray(Y, float), np.asarray(test))
    omega = a.T @ a+np.asarray(V_sampling, float)
    L = np.linalg.cholesky((omega+omega.T)/2)
    W = np.linalg.solve(L, a.T)                  # whitened (qm, n)
    S = float(np.sum(W.sum(axis=1)**2))
    signs = rng.choice((-1., 1.), size=(draws, a.shape[0]))
    Sb = np.sum((signs @ W.T)**2, axis=1)
    return dict(statistic=S, p=float((1+np.sum(Sb >= S))/(draws+1)), df=a.shape[1])


def pillai(X, Y, test):
    """Pillai's trace with the usual F approximation (iid; comparison only)."""
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    n, p = X.shape; m = Y.shape[1]; q = len(test)
    keep = np.setdiff1d(np.arange(p), test)
    E = (Y-X @ np.linalg.lstsq(X, Y, rcond=None)[0]).T @ (Y-X @ np.linalg.lstsq(X, Y, rcond=None)[0])
    Rr = Y-X[:, keep] @ np.linalg.lstsq(X[:, keep], Y, rcond=None)[0]
    H = Rr.T @ Rr-E
    V = float(np.trace(H @ np.linalg.inv(H+E)))
    s = min(m, q); mm = (abs(m-q)-1)/2; nn = (n-p-m-1)/2
    F = (2*nn+s+1)/(2*mm+s+1)*V/(s-V)
    df1, df2 = s*(2*mm+s+1), s*(2*nn+s+1)
    return dict(statistic=V, F=float(F), p=float(stats.f.sf(F, df1, df2)), df1=df1, df2=df2)


def count_slope(y, X, exposure, family, level=.90):
    """Slope (column 1) and its interval: poisson (HC3), negbin (NB2 alpha by ML, then GLM HC3), zip (HC0)."""
    y, X, E = np.asarray(y, float), np.asarray(X, float), np.asarray(exposure, float)
    z = stats.norm.ppf((1+level)/2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if family == "poisson":
            r = sm.GLM(y, X, family=sm.families.Poisson(), exposure=E).fit(cov_type="HC3")
        elif family == "negbin":
            nb = sm.NegativeBinomial(y, X, exposure=E).fit(disp=0, maxiter=200)
            if not nb.mle_retvals.get("converged", True):
                raise ValueError("NB alpha did not converge")
            alpha = float(nb.params[-1])
            r = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), exposure=E).fit(cov_type="HC3")
        elif family == "zip":
            r = sm.ZeroInflatedPoisson(y, X, exog_infl=np.ones((len(y), 1)), exposure=E, inflation="logit").fit(
                disp=0, maxiter=500, cov_type="HC0", method="newton")
            if not r.mle_retvals.get("converged", True):
                raise ValueError("ZIP did not converge")
        else:
            raise ValueError("family must be poisson, negbin or zip")
    names = list(range(len(r.params)))
    j = 1 if family != "zip" else 2              # zip params: inflate_const, const, slope
    b, se = float(np.asarray(r.params)[j]), float(np.asarray(r.bse)[j])
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite slope or SE")
    return dict(estimate=b, se=se, lower=b-z*se, upper=b+z*se)

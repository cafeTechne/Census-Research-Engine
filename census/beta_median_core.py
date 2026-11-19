# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 40 beta and median regression procedures (frozen with the criterion; PLAN_ROUND_40)."""
import warnings

import numpy as np
from scipy import stats
from statsmodels.othermod.betareg import BetaModel
from statsmodels.regression.quantile_regression import QuantReg

Z = stats.norm.ppf(.95)


def beta_fit(y, X, cov="model"):
    y = np.clip(np.asarray(y, float), 1e-3, 1-1e-3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = BetaModel(y, np.asarray(X, float)).fit(disp=0, **({"cov_type": "HC0"} if cov == "hc0" else {}))
    if not r.mle_retvals.get("converged", True):
        raise ValueError("beta regression did not converge")
    k = np.asarray(X).shape[1]
    return np.asarray(r.params)[:k], np.asarray(r.bse)[:k]


def median_fit(y, X):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = QuantReg(np.asarray(y, float), np.asarray(X, float)).fit(q=.5, max_iter=5000)
    return np.asarray(r.params), np.asarray(r.bse)


def interval(b, se, j=1, extra_var=0.):
    s = float(np.sqrt(se[j]**2+extra_var))
    if not (np.isfinite(b[j]) and np.isfinite(s) and s > 0):
        raise ValueError("non-finite estimate or SE")
    return dict(estimate=float(b[j]), se=s, lower=float(b[j]-Z*s), upper=float(b[j]+Z*s))


def replicate_variance(fitter, Y_reps, X_reps, b, j=1):
    """4/80 sum over replicate refits of coefficient j. Y_reps: (80, n); X_reps: (80, n, p)."""
    br = np.array([fitter(Y_reps[r], X_reps[r])[0][j] for r in range(len(Y_reps))])
    return float(.05*np.sum((br-b[j])**2))

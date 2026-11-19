# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 41 causal procedures (frozen with the criterion; PLAN_ROUND_41)."""
import warnings

import numpy as np
import statsmodels.api as sm
from scipy import stats

Z90 = stats.norm.ppf(.95)


def treatment_effect(y, T, Z, method):
    """ATE of binary T given confounders Z via statsmodels TreatmentEffect (ipw | aipw | ra)."""
    from statsmodels.treatment.treatment_effects import TreatmentEffect
    y, T, Z = np.asarray(y, float), np.asarray(T, int), np.asarray(Z, float)
    exog = sm.add_constant(Z)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sel = sm.Logit(T, exog).fit(disp=0)
        te = TreatmentEffect(sm.OLS(y, exog), T, results_select=sel)
        fr = getattr(te, method)().summary_frame()
    b, se = float(fr.loc["ATE", "coef"]), float(fr.loc["ATE", "std err"])
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite ATE or SE")
    return dict(estimate=b, se=se, lower=b-Z90*se, upper=b+Z90*se)


def iv_2sls(y, x, instrument, controls=None):
    """2SLS slope of x with one instrument; HC0 sandwich."""
    y = np.asarray(y, float); n = len(y)
    C = np.ones((n, 1)) if controls is None else np.column_stack((np.ones(n), np.asarray(controls, float)))
    X = np.column_stack((C, np.asarray(x, float))); W = np.column_stack((C, np.asarray(instrument, float)))
    Pz = W @ np.linalg.solve(W.T @ W, W.T)
    Xh = Pz @ X
    A = np.linalg.inv(Xh.T @ X)
    b = A @ Xh.T @ y
    e = y-X @ b
    V = A @ (Xh.T*e**2) @ Xh @ A.T
    j = X.shape[1]-1; se = float(np.sqrt(V[j, j]))
    return dict(estimate=float(b[j]), se=se, lower=float(b[j]-Z90*se), upper=float(b[j]+Z90*se))


def ols_slope(y, x, controls=None):
    n = len(y)
    X = np.column_stack((np.ones(n),) + (() if controls is None else (np.asarray(controls, float),)) + (np.asarray(x, float),))
    r = sm.OLS(np.asarray(y, float), X).fit(cov_type="HC0")
    b, se = float(r.params[-1]), float(r.bse[-1])
    return dict(estimate=b, se=se, lower=b-Z90*se, upper=b+Z90*se)


def _paths(x, m, y, controls=None):
    n = len(y)
    C = np.ones((n, 1)) if controls is None else np.column_stack((np.ones(n), controls))
    ra = sm.OLS(m, np.column_stack((C, x))).fit(cov_type="HC0")
    rb = sm.OLS(y, np.column_stack((C, x, m))).fit(cov_type="HC0")
    return float(ra.params[-1]), float(ra.bse[-1]), float(rb.params[-1]), float(rb.bse[-1])


def mediation(x, m, y, method="sobel", rng=None, draws=1000, controls=None):
    """Indirect effect a*b: Sobel delta method or percentile bootstrap (HC0 path models)."""
    x, m, y = (np.asarray(v, float) for v in (x, m, y))
    a, sa, b, sb = _paths(x, m, y, controls)
    ab = a*b
    if method == "sobel":
        se = float(np.sqrt(b**2*sa**2+a**2*sb**2))
        return dict(estimate=ab, se=se, lower=ab-Z90*se, upper=ab+Z90*se)
    n = len(y); est = []
    for _ in range(draws):
        i = rng.integers(0, n, n)
        aa, _, bb, _ = _paths(x[i], m[i], y[i], None if controls is None else np.asarray(controls)[i])
        est.append(aa*bb)
    lo, hi = np.quantile(est, [.05, .95])
    return dict(estimate=ab, se=float(np.std(est, ddof=1)), lower=float(lo), upper=float(hi))

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 73 frozen core: three-level random-intercept models (bottom in middle in top; backlog N51, was N46).

REML fit with statsmodels MixedLM (groups = top level, variance component = middle level). Candidates:
M1 fixed-effect intervals with t(G_top - 1) critical values; M3 variance-share intervals from a delete-one-top-unit
jackknife (normal on the logit of each share). M2 (parametric bootstrap) was dropped before the run: one fit takes
1-3.5 s, so 199 refits per draw were infeasible, and MixedLM's covariance of the variance parameters was NaN for the
top level in a probe.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats


def fit3(data: pd.DataFrame, formula: str, top: str, mid: str):
    import statsmodels.formula.api as smf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = smf.mixedlm(formula, data, groups=top, re_formula="1", vc_formula={mid: f"0 + C({mid})"}).fit(
            reml=True, method=["lbfgs", "powell"])
    v = dict(top=float(m.cov_re.iloc[0, 0]), mid=float(m.vcomp[0]), bottom=float(m.scale))
    return m, v


def shares(v):
    tot = sum(v.values())
    return {k: x/tot for k, x in v.items()}


def fixed_intervals(m, n_top: int, level=.90):
    """M1: Wald intervals for the fixed effects with t(n_top - 1) critical values."""
    t = stats.t.ppf(.5+level/2, max(n_top-1, 1))
    fe = m.fe_params; se = m.bse_fe
    return pd.DataFrame(dict(term=fe.index, estimate=fe.values, se=se.values, lower=fe.values-t*se.values,
                             upper=fe.values+t*se.values, df=n_top-1))


def jackknife_shares(data: pd.DataFrame, formula: str, top: str, mid: str, level=.90):
    """M3: delete-one-top-unit jackknife of logit(shares); normal interval, back-transformed."""
    _, v = fit3(data, formula, top, mid)
    full = shares(v)
    units = data[top].unique(); G = len(units)
    reps = []
    for u in units:
        _, vj = fit3(data[data[top] != u], formula, top, mid)
        reps.append(shares(vj))
    z = stats.norm.ppf(.5+level/2)
    out = {}
    for k in full:
        lg = lambda p: np.log(np.clip(p, 1e-9, 1-1e-9)/(1-np.clip(p, 1e-9, 1-1e-9)))  # noqa: E731
        r = np.array([lg(x[k]) for x in reps]); c = lg(full[k])
        se = float(np.sqrt((G-1)/G*np.sum((r-r.mean())**2)))
        out[k] = dict(estimate=full[k], lower=float(1/(1+np.exp(-(c-z*se)))), upper=float(1/(1+np.exp(-(c+z*se)))))
    return out

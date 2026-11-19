# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 37 agreement procedures (frozen with the validation criterion; PLAN_ROUND_37).

x: source A, y: source B, d = y - x. aSE/bSE: known per-area standard errors (bSE may be 0).
Errors of the two sources are assumed independent. Limits of agreement use 1.645 SD (90%).
"""
import numpy as np
from scipy import stats

ZL = 1.645


def _t(level, df):
    return stats.t.ppf((1+level)/2, df)


def bias(x, y, level=.90):
    d = np.asarray(y, float)-np.asarray(x, float); n = len(d)
    m, sd = d.mean(), d.std(ddof=1); se = sd/np.sqrt(n); c = _t(level, n-1)
    return dict(estimate=float(m), lower=float(m-c*se), upper=float(m+c*se))


def limits_observed(x, y, level=.90):
    d = np.asarray(y, float)-np.asarray(x, float); n = len(d)
    m, sd = d.mean(), d.std(ddof=1)
    se = sd*np.sqrt(1/n+ZL**2/(2*(n-1))); c = _t(level, n-1)
    lo, hi = m-ZL*sd, m+ZL*sd
    return dict(lower_limit=float(lo), upper_limit=float(hi), lower_ci=(float(lo-c*se), float(lo+c*se)),
                upper_ci=(float(hi-c*se), float(hi+c*se)))


def limits_true(x, y, a_se, b_se=None, level=.90):
    d = np.asarray(y, float)-np.asarray(x, float); n = len(d)
    m, s2 = d.mean(), d.var(ddof=1)
    err = np.mean(np.asarray(a_se, float)**2+(0 if b_se is None else np.asarray(b_se, float)**2))
    st2 = s2-err
    if not st2 > 0:
        raise ValueError("sampling error explains all the disagreement; error-free limits undefined")
    st = np.sqrt(st2)
    var_st = 2*s2**2/(n-1)/(4*st2)          # delta method for sqrt(s_d^2 - err)
    se = np.sqrt(s2/n+ZL**2*var_st); c = _t(level, n-1)
    lo, hi = m-ZL*st, m+ZL*st
    return dict(lower_limit=float(lo), upper_limit=float(hi), lower_ci=(float(lo-c*se), float(lo+c*se)),
                upper_ci=(float(hi-c*se), float(hi+c*se)), sd_true=float(st))


def _ccc_parts(x, y, a_err=0., b_err=0.):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    sx2, sy2 = x.var()-a_err, y.var()-b_err
    sxy = np.mean((x-mx)*(y-my))
    if not (sx2 > 0 and sy2 > 0):
        raise ValueError("error variance exceeds a source's variance")
    rc = 2*sxy/(sx2+sy2+(mx-my)**2)
    r = sxy/np.sqrt(sx2*sy2)
    u = (mx-my)/np.sqrt(np.sqrt(sx2*sy2))
    return rc, r, u


def ccc(x, y, a_se=None, b_se=None, level=.90):
    """C1 (no SEs) or C2 (error variances removed). Lin's (1989) z-transform interval."""
    a_err = 0. if a_se is None else float(np.mean(np.asarray(a_se, float)**2))
    b_err = 0. if b_se is None else float(np.mean(np.asarray(b_se, float)**2))
    rc, r, u = _ccc_parts(x, y, a_err, b_err)
    if not (abs(rc) < 1 and abs(r) < 1):
        raise ValueError("concordance at +-1")
    n = len(np.asarray(x))
    var = ((1-r**2)*rc**2/((1-rc**2)*r**2)+2*rc**3*(1-rc)*u**2/(r*(1-rc**2)**2)
           - rc**4*u**4/(2*r**2*(1-rc**2)**2))/(n-2)
    z = np.arctanh(rc); se = np.sqrt(var); c = stats.norm.ppf((1+level)/2)
    return dict(estimate=float(rc), lower=float(np.tanh(z-c*se)), upper=float(np.tanh(z+c*se)), pearson=float(r))


def kappa_quintiles(x, y, level=.90):
    from statsmodels.stats.inter_rater import cohens_kappa
    qx = np.digitize(x, np.quantile(x, [.2, .4, .6, .8])); qy = np.digitize(y, np.quantile(y, [.2, .4, .6, .8]))
    table = np.zeros((5, 5)); np.add.at(table, (qx, qy), 1)
    res = cohens_kappa(table)
    se = float(np.sqrt(res["var_kappa"])); c = stats.norm.ppf((1+level)/2)
    return dict(estimate=float(res["kappa"]), lower=float(res["kappa"]-c*se), upper=float(res["kappa"]+c*se))

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 38 procedures for combining evidence (frozen with the criterion; PLAN_ROUND_38)."""
import numpy as np
from scipy import optimize, stats


def _arr(theta, se):
    theta, se = np.asarray(theta, float), np.asarray(se, float)
    if len(theta) < 2 or len(theta) != len(se) or not (np.isfinite(theta).all() and (se > 0).all()):
        raise ValueError("need at least two estimates with positive standard errors")
    return theta, se


def heterogeneity(theta, se):
    theta, se = _arr(theta, se)
    w = 1/se**2; mu = np.sum(w*theta)/w.sum()
    Q = float(np.sum(w*(theta-mu)**2)); k = len(theta)
    return dict(Q=Q, df=k-1, p=float(stats.chi2.sf(Q, k-1)), I2=float(max(0., (Q-(k-1))/Q)) if Q > 0 else 0.)


def tau2_dl(theta, se):
    theta, se = _arr(theta, se)
    w = 1/se**2; Q = heterogeneity(theta, se)["Q"]
    C = w.sum()-np.sum(w**2)/w.sum()
    return float(max(0., (Q-(len(theta)-1))/C))


def tau2_pm(theta, se):
    theta, se = _arr(theta, se)
    k = len(theta)
    def g(t2):
        w = 1/(se**2+t2); mu = np.sum(w*theta)/w.sum()
        return float(np.sum(w*(theta-mu)**2)-(k-1))
    if g(0.) <= 0:
        return 0.
    hi = max(1., float(np.var(theta))*10)
    while g(hi) > 0:
        hi *= 10
    return float(optimize.brentq(g, 0., hi, xtol=1e-12))


def pooled(theta, se, method, level=.90):
    """M1 fixed / M2 DerSimonian-Laird normal / M3 Paule-Mandel + Hartung-Knapp t(k-1)."""
    theta, se = _arr(theta, se)
    k = len(theta)
    if method == "fixed":
        t2 = 0.
    elif method == "dl":
        t2 = tau2_dl(theta, se)
    elif method == "hksj":
        t2 = tau2_pm(theta, se)
    else:
        raise ValueError("method must be fixed, dl or hksj")
    w = 1/(se**2+t2); mu = float(np.sum(w*theta)/w.sum())
    if method == "hksj":
        var = float(np.sum(w*(theta-mu)**2)/((k-1)*w.sum()))
        crit = stats.t.ppf((1+level)/2, k-1)
    else:
        var = float(1/w.sum()); crit = stats.norm.ppf((1+level)/2)
    se_mu = np.sqrt(var)
    out = dict(estimate=mu, se=float(se_mu), lower=mu-crit*se_mu, upper=mu+crit*se_mu, tau2=t2, method=method)
    if k >= 3 and method != "fixed":
        c = stats.t.ppf((1+level)/2, k-2); s = np.sqrt(t2+var)
        out["prediction_interval"] = (mu-c*s, mu+c*s)
    return out


def tost(e1, s1, e2, s2, margin, alpha=.05):
    d = float(e2-e1); s = float(np.hypot(s1, s2))
    p_lower = float(stats.norm.sf((d+margin)/s)); p_upper = float(stats.norm.cdf((d-margin)/s))
    z = stats.norm.ppf(1-alpha)
    return dict(difference=d, se=s, p_lower=p_lower, p_upper=p_upper, p=max(p_lower, p_upper),
                equivalent=bool(max(p_lower, p_upper) < alpha), ci=(d-z*s, d+z*s), margin=margin)


def power_z(effect, se, alpha=.10):
    z = stats.norm.ppf(1-alpha/2); r = abs(effect)/se
    return float(stats.norm.cdf(r-z)+stats.norm.cdf(-r-z))


def mde_z(se, power=.80, alpha=.10):
    return float((stats.norm.ppf(1-alpha/2)+stats.norm.ppf(power))*se)

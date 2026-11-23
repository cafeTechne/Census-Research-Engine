# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 102 frozen core: meta-analysis completeness (backlog N79; Harrer, Cuijpers, Furukawa and Ebert 2021;
Higgins, Thompson and Spiegelhalter 2009; Viechtbauer 2005, 2007; Knapp and Hartung 2003; Egger et al. 1997).

Estimates y_i with within-study variances v_i.
- tau^2: Paule-Mandel (``evidence_core.tau2_pm``) or REML (Fisher scoring, truncated at 0).
- Pooled mean: inverse-variance weights 1/(v_i + tau^2); Hartung-Knapp variance sum w (y - mu)^2 / ((k - 1) sum w)
  with t(k - 1) (as ``evidence_core.pooled``, method "hksj").
- P1 prediction interval for a new estimate: mu +/- t_(k-2) sqrt(tau^2 + SE(mu)^2).
- H1 Q-profile interval for tau^2: {tau^2 : chi2_(k-1)(a/2) <= Q_gen(tau^2) <= chi2_(k-1)(1-a/2)}, Q_gen(t) =
  sum (y - mu(t))^2 / (v + t); bounds truncated at 0.
- R1 meta-regression: y = X b + u + e, tau^2 by REML; Knapp-Hartung covariance s^2 (X'WX)^-1 with
  s^2 = sum w e^2 / (k - p) (not truncated), t(k - p); permutation p-value for each moderator from ``perms``
  permutations of the moderator rows (refitting tau^2).
- E1 Egger test: OLS of y/se on 1/se; t test of the intercept, t(k - 2).
- D1 leave-one-out pooled estimates.
"""
from typing import Dict, Optional

import numpy as np
from scipy import optimize, stats

from .evidence_core import pooled, tau2_pm


def tau2_reml(y, v, X=None, iters=100):
    y = np.asarray(y, float); v = np.asarray(v, float); k = len(y)
    X = np.ones((k, 1)) if X is None else np.asarray(X, float)
    t2 = max(0.0, float(np.var(y, ddof=1)-np.mean(v)))
    for _ in range(iters):
        w = 1/(v+t2)
        XtWX = X.T @ (X*w[:, None]); P = np.diag(w)-(X*w[:, None]) @ np.linalg.solve(XtWX, (X*w[:, None]).T)
        Py = P @ y
        score = .5*(Py @ Py-np.trace(P))
        info = .5*np.trace(P @ P)
        step = score/info
        new = max(0.0, t2+step)
        if abs(new-t2) < 1e-10:
            t2 = new; break
        t2 = new
    return float(t2)


def meta(y, v, tau2: str = "pm", level: float = .90) -> Dict[str, float]:
    y = np.asarray(y, float); v = np.asarray(v, float); k = len(y)
    se = np.sqrt(v)
    if tau2 == "pm":
        out = pooled(y, se, "hksj", level)
        out.pop("prediction_interval", None)
    elif tau2 == "reml":
        t2 = tau2_reml(y, v); w = 1/(v+t2); mu = float(np.sum(w*y)/w.sum())
        var = float(np.sum(w*(y-mu)**2)/((k-1)*w.sum())); c = stats.t.ppf((1+level)/2, k-1); s = np.sqrt(var)
        out = dict(estimate=mu, se=s, lower=mu-c*s, upper=mu+c*s, tau2=t2, method="reml_hk")
    else:
        raise ValueError("tau2 must be 'pm' or 'reml'")
    c = stats.t.ppf((1+level)/2, k-2) if k >= 3 else np.inf
    s = np.sqrt(out["tau2"]+out["se"]**2)
    out["pi_lower"], out["pi_upper"] = out["estimate"]-c*s, out["estimate"]+c*s
    return out


def q_profile(y, v, level: float = .90):
    y = np.asarray(y, float); v = np.asarray(v, float); k = len(y)

    def Q(t):
        w = 1/(v+t); mu = np.sum(w*y)/w.sum()
        return float(np.sum(w*(y-mu)**2))
    lo_c, hi_c = stats.chi2.ppf(1-(1-level)/2, k-1), stats.chi2.ppf((1-level)/2, k-1)
    big = max(1.0, 100*float(np.var(y)))

    def root(target):
        if Q(0.0) <= target:
            return 0.0
        hi = big
        while Q(hi) > target:
            hi *= 10
        return float(optimize.brentq(lambda t: Q(t)-target, 0.0, hi, xtol=1e-12))
    return root(lo_c), root(hi_c)


def meta_regression(y, v, X, perms: int = 199, rng=None, level: float = .90) -> Dict[str, np.ndarray]:
    y = np.asarray(y, float); v = np.asarray(v, float)
    Xm = np.column_stack([np.ones(len(y)), np.asarray(X, float).reshape(len(y), -1)])
    k, p = Xm.shape

    def fit(Xf):
        t2 = tau2_reml(y, v, Xf); w = 1/(v+t2)
        XtWX = Xf.T @ (Xf*w[:, None]); b = np.linalg.solve(XtWX, Xf.T @ (w*y))
        e = y-Xf @ b; s2 = float(np.sum(w*e**2)/(k-p))
        se = np.sqrt(np.diag(s2*np.linalg.inv(XtWX)))
        return b, se, t2
    b, se, t2 = fit(Xm)
    tstat = b/se; c = stats.t.ppf((1+level)/2, k-p)
    rng = rng or np.random.default_rng(0)
    exceed = np.zeros(p)
    for _ in range(perms):
        o = rng.permutation(k)
        Xp = Xm.copy(); Xp[:, 1:] = Xm[o, 1:]
        bp, sep, _ = fit(Xp)
        exceed += np.abs(bp/sep) >= np.abs(tstat)-1e-12
    pperm = (exceed+1)/(perms+1); pperm[0] = np.nan
    return dict(coef=b, se=se, lower=b-c*se, upper=b+c*se, t=tstat, p_permutation=pperm, tau2=t2, df=k-p)


def egger(y, v) -> Dict[str, float]:
    y = np.asarray(y, float); se = np.sqrt(np.asarray(v, float)); k = len(y)
    X = np.column_stack([np.ones(k), 1/se]); z = y/se
    b, *_ = np.linalg.lstsq(X, z, rcond=None); r = z-X @ b
    s2 = float(r @ r)/(k-2); V = s2*np.linalg.inv(X.T @ X)
    t = b[0]/np.sqrt(V[0, 0])
    return dict(intercept=float(b[0]), se=float(np.sqrt(V[0, 0])), t=float(t), p=float(2*stats.t.sf(abs(t), k-2)), k=k)


def leave_one_out(y, v, tau2: str = "pm"):
    y = np.asarray(y, float); v = np.asarray(v, float)
    return [meta(np.delete(y, i), np.delete(v, i), tau2) for i in range(len(y))]

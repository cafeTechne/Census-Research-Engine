# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 90 positivity procedures (frozen with the criterion, docs/audits/positivity_validation_criterion.md).

Hernán and Robins, *What If*, chapters 3.3 (positivity), 12 (IP weighting, stabilized weights) and 13 and 15
(standardization, the g-formula); Li, Morgan and Zaslavsky (2018) for overlap weights; Lunceford and Davidian
(2004) for the sandwich variance of weighted estimators with an estimated propensity score.

- ``propensity``: logistic regression by Newton-Raphson (intercept plus confounders).
- ``weighted_effect``: Hajek (normalized) weighted difference in means, with weights
  W1 ``stabilized`` P(T=t)/P(T=t | Z), W2 ``truncated`` (stabilized weights truncated at their 1st and 99th
  percentiles) or W3 ``overlap`` (1 - e for treated, e for untreated; the estimand is the overlap-population effect).
  Variance: stacked M-estimation sandwich (propensity score equations plus the two weighted means; truncation
  points held fixed), numerical Jacobian.
- ``g_formula``: standardization with separate linear outcome models per arm, averaged over all units; stacked
  sandwich variance.
- ``diagnostics``: propensity quantiles by group, the share outside [.05, .95], the overlap coefficient (shared
  area of the two propensity histograms, 20 bins on [0, 1]), standardized mean differences before and after
  weighting, maximum weight and the effective sample size (Kish) per group.
"""
from typing import Any, Dict, Optional

import numpy as np
from scipy import stats

Z90 = stats.norm.ppf(.95)
BOUNDS = (.05, .95)


def _design(Z):
    Z = np.asarray(Z, float)
    return np.column_stack([np.ones(len(Z)), Z.reshape(len(Z), -1)])


def propensity(T, Z, iters=50):
    """Logistic regression coefficients and fitted probabilities; raises on separation or non-convergence."""
    X = _design(Z); T = np.asarray(T, float)
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        e = 1/(1+np.exp(-np.clip(X @ b, -30, 30)))
        W = e*(1-e)
        H = X.T @ (X*W[:, None])
        step = np.linalg.solve(H, X.T @ (T-e))
        b = b+step
        if np.max(np.abs(step)) < 1e-10:
            break
    else:
        raise ValueError("propensity model did not converge (possible separation: a positivity violation)")
    e = 1/(1+np.exp(-np.clip(X @ b, -30, 30)))
    if e.min() < 1e-8 or e.max() > 1-1e-8:
        raise ValueError("propensity scores of 0 or 1: a deterministic positivity violation")
    return b, e


def _weights(kind, T, e, p1, cut=None):
    if kind in ("stabilized", "truncated"):
        w = np.where(T == 1, p1/e, (1-p1)/(1-e))
        if kind == "truncated":
            lo, hi = cut
            w = np.clip(w, lo, hi)
        return w
    if kind == "overlap":
        return np.where(T == 1, 1-e, e)
    raise ValueError("weights must be 'stabilized', 'truncated' or 'overlap'")


def _sandwich(psi, theta):
    """Sandwich covariance for estimating functions psi(theta) -> (n, k), numerical Jacobian."""
    P = psi(theta); n = len(P)
    k = len(theta); A = np.zeros((k, k))
    for j in range(k):
        h = 1e-6*max(1., abs(theta[j]))
        tp, tm = theta.copy(), theta.copy(); tp[j] += h; tm[j] -= h
        A[:, j] = (psi(tp).mean(0)-psi(tm).mean(0))/(2*h)
    B = P.T @ P/n
    Ai = np.linalg.inv(A)
    return Ai @ B @ Ai.T/n


def weighted_effect(y, T, Z, kind="stabilized"):
    """Hajek weighted effect with a stacked sandwich SE (propensity estimated)."""
    y, T = np.asarray(y, float), np.asarray(T, float)
    X = _design(Z)
    b, e = propensity(T, Z)
    p1 = T.mean()
    cut = None
    if kind == "truncated":
        w0 = _weights("stabilized", T, e, p1)
        cut = tuple(np.quantile(w0, [.01, .99]))
    w = _weights(kind, T, e, p1, cut)
    m1 = np.sum(w*T*y)/np.sum(w*T); m0 = np.sum(w*(1-T)*y)/np.sum(w*(1-T))
    kb = len(b)

    def psi(th):
        bb, a1, a0 = th[:kb], th[kb], th[kb+1]
        ee = 1/(1+np.exp(-np.clip(X @ bb, -30, 30)))
        ww = _weights(kind, T, ee, p1, cut)
        return np.column_stack([X*(T-ee)[:, None], ww*T*(y-a1), ww*(1-T)*(y-a0)])
    th = np.concatenate([b, [m1, m0]])
    V = _sandwich(psi, th)
    g = np.zeros(len(th)); g[kb], g[kb+1] = 1, -1
    est, se = m1-m0, float(np.sqrt(g @ V @ g))
    if not (np.isfinite(est) and np.isfinite(se) and se > 0):
        raise ValueError("non-finite weighted estimate")
    return dict(estimate=float(est), se=se, lower=float(est-Z90*se), upper=float(est+Z90*se),
                estimand="overlap-population effect" if kind == "overlap" else "average treatment effect",
                weights=kind), e, w


def g_formula(y, T, Z):
    """Standardization (g-formula) with arm-specific linear outcome models; stacked sandwich SE."""
    y, T = np.asarray(y, float), np.asarray(T, float)
    X = _design(Z); k = X.shape[1]
    b1 = np.linalg.lstsq(X[T == 1], y[T == 1], rcond=None)[0]
    b0 = np.linalg.lstsq(X[T == 0], y[T == 0], rcond=None)[0]
    tau = float(np.mean(X @ b1 - X @ b0))

    def psi(th):
        c1, c0, t = th[:k], th[k:2*k], th[2*k]
        return np.column_stack([X*(T*(y-X @ c1))[:, None], X*((1-T)*(y-X @ c0))[:, None], X @ c1 - X @ c0 - t])
    th = np.concatenate([b1, b0, [tau]])
    se = float(np.sqrt(_sandwich(psi, th)[-1, -1]))
    return dict(estimate=tau, se=se, lower=tau-Z90*se, upper=tau+Z90*se, estimand="average treatment effect")


def _overlap_coef(e, T, bins=20):
    h1 = np.histogram(e[T == 1], bins=bins, range=(0, 1))[0]/max(1, (T == 1).sum())
    h0 = np.histogram(e[T == 0], bins=bins, range=(0, 1))[0]/max(1, (T == 0).sum())
    return float(np.minimum(h1, h0).sum())


def _smd(x, T, w=None):
    w = np.ones(len(x)) if w is None else w
    m1 = np.average(x[T == 1], weights=w[T == 1]); m0 = np.average(x[T == 0], weights=w[T == 0])
    s = np.sqrt((x[T == 1].var(ddof=1)+x[T == 0].var(ddof=1))/2)
    return float((m1-m0)/s) if s > 0 else 0.0


def diagnostics(T, Z, e, w):
    T = np.asarray(T, float); Z = np.asarray(Z, float).reshape(len(T), -1)
    q = [0, .01, .05, .25, .5, .75, .95, .99, 1]
    ess = {g: float(w[T == v].sum()**2/np.sum(w[T == v]**2)) for g, v in (("treated", 1), ("untreated", 0))}
    return dict(
        propensity_quantiles={g: dict(zip([f"q{int(100*x)}" for x in q], map(float, np.quantile(e[T == v], q))))
                              for g, v in (("treated", 1), ("untreated", 0))},
        share_outside=float(np.mean((e < BOUNDS[0]) | (e > BOUNDS[1]))), bounds=list(BOUNDS),
        overlap_coefficient=_overlap_coef(e, T),
        smd_before=[_smd(Z[:, j], T) for j in range(Z.shape[1])],
        smd_after=[_smd(Z[:, j], T, w) for j in range(Z.shape[1])],
        max_weight=float(w.max()), effective_n=ess, n={"treated": int(T.sum()), "untreated": int((1-T).sum())})


def agreement(ipw: Dict[str, Any], g: Dict[str, Any]) -> Dict[str, Any]:
    """IPW versus g-formula: flagged when the estimates differ by more than the sum of their SEs."""
    d = abs(ipw["estimate"]-g["estimate"])
    return dict(difference=float(ipw["estimate"]-g["estimate"]), threshold=float(ipw["se"]+g["se"]),
                flagged=bool(d > ipw["se"]+g["se"]))

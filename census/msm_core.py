# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 91 IP-weighted marginal structural models for annual policy panels (frozen with the criterion,
docs/audits/msm_validation_criterion.md).

Hernán and Robins, *What If*, chapters 19-21 (time-varying treatments, treatment-confounder feedback, IP weighting of
marginal structural models); Robins, Hernán and Brumback (2000); Cole and Hernán (2008) for weight truncation.

Panel: units i (states) observed in years t = 1..K; all untreated at the first year (time zero); treatment strategy
"start and stay on" (A_it = 1 from a unit's first treated year on). L_it is a time-varying confounder, possibly
affected by past treatment.

- Stabilized weights: SW_it = prod_{s<=t, at risk at s} P(A_is | year) / P(A_is | year, L_is), from pooled logistic
  models over unit-years still untreated (after the first treated year the factor is 1: treatment is not withdrawn).
- MSM (weighted least squares): Y_it ~ year fixed effects + an indicator for every observed treatment duration
  d_it = 1, 2, ... (years since the first treated year, counting it; saturated, so no duration pattern is assumed).
  psi_d is the effect of being in the d-th treated year versus never treated; the first ``report`` durations are
  returned.
- M1: stabilized weights, percentile cluster bootstrap over units (re-estimating the weights; B resamples).
- M2: the same with weights truncated at their 1st and 99th percentiles (Cole and Hernán 2008).
- Comparisons (reported only): regression adjusting for current L (biased under feedback: L is then on the causal
  path) and no adjustment.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np

REPORT = 3


def _logit(X, y, iters=60):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1/(1+np.exp(-np.clip(X @ b, -30, 30)))
        H = X.T @ (X*(p*(1-p))[:, None]) + 1e-9*np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y-p))
        b += step
        if np.max(np.abs(step)) < 1e-9:
            return b
    raise ValueError("treatment model did not converge")


def _year_dummies(year, K):
    return (year[:, None] == np.arange(1, K+1)[None, :]).astype(float)


def durations(A, unit, year):
    """Years since first treatment (1 in the first treated year), 0 when untreated."""
    d = np.zeros(len(A))
    first = {}
    for i in np.argsort(year, kind="stable"):
        if A[i] == 1:
            first.setdefault(unit[i], year[i])
            d[i] = year[i]-first[unit[i]]+1
    return d


def weights(A, L, unit, year, K, truncate=False):
    """Stabilized IP weights (cumulative product within unit over at-risk years). Time zero is year 1, when no unit
    is treated, so the risk set is years 2.. up to and including each unit's first treated year. Pooled logistic
    models: numerator intercept + year (linear); denominator intercept + year + L."""
    first = {}
    for i in np.argsort(year, kind="stable"):
        if A[i] == 1:
            first.setdefault(unit[i], year[i])
    if any(v == 1 for v in first.values()):
        raise ValueError("units treated in the first year: time zero must precede treatment")
    risk = np.array([1 < year[i] <= first.get(unit[i], np.inf) for i in range(len(A))])
    t = (year-1)/K
    Xn = np.column_stack([np.ones(len(A)), t]); Xd = np.column_stack([Xn, L])
    a = A[risk].astype(float)
    bn = _logit(Xn[risk], a); bd = _logit(Xd[risk], a)
    pn = 1/(1+np.exp(-Xn @ bn)); pd_ = 1/(1+np.exp(-Xd @ bd))
    f = np.where(risk, np.where(A == 1, pn/pd_, (1-pn)/(1-pd_)), 1.0)
    w = np.ones(len(A))
    order = np.lexsort((year, unit))
    run, prev = 1.0, None
    for i in order:
        if unit[i] != prev:
            run, prev = 1.0, unit[i]
        run *= f[i]
        w[i] = run
    if truncate:
        lo, hi = np.quantile(w, [.01, .99])
        w = np.clip(w, lo, hi)
    return w


def _wls(Y, X, w):
    sw = np.sqrt(w)
    return np.linalg.lstsq(X*sw[:, None], Y*sw, rcond=None)[0]


def msm_point(Y, A, L, unit, year, K, truncate=False, adjust_L=False, unweighted=False, report=REPORT):
    d = durations(A, unit, year)
    for k in range(1, report+1):
        if not (d == k).any():
            raise ValueError(f"no unit-year with treatment duration {k}")
    D = np.column_stack([d == k for k in range(1, K)]).astype(float)
    D = D[:, D.sum(0) > 0]
    X = np.column_stack([_year_dummies(year, K), D] + ([L] if adjust_L else []))
    w = np.ones(len(Y)) if unweighted or adjust_L else weights(A, L, unit, year, K, truncate)
    b = _wls(Y, X, w)
    ny = int((_year_dummies(year, K).sum(0) > 0).sum())
    return b[ny:ny+report], w


def msm(Y, A, L, unit, year, K, truncate=False, B=200, rng=None, adjust_L=False, unweighted=False, level=.90,
        report=REPORT):
    """Point estimates psi_1..psi_report and percentile cluster-bootstrap intervals (units resampled)."""
    rng = rng or np.random.default_rng(0)
    est, w = msm_point(Y, A, L, unit, year, K, truncate, adjust_L, unweighted, report)
    units = np.unique(unit)
    idx = {u: np.flatnonzero(unit == u) for u in units}
    reps = []
    for _ in range(B):
        pick = rng.choice(units, len(units))
        rows = np.concatenate([idx[u] for u in pick])
        newu = np.repeat(np.arange(len(pick)), [len(idx[u]) for u in pick])
        try:
            reps.append(msm_point(Y[rows], A[rows], L[rows], newu, year[rows], K, truncate, adjust_L, unweighted,
                                  report)[0])
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(reps) < .9*B:
        raise ValueError("too many failed bootstrap resamples")
    R = np.array(reps)
    a = (1-level)/2
    lo, hi = np.nanquantile(R, [a, 1-a], axis=0)
    return dict(estimate=est.tolist(), lower=lo.tolist(), upper=hi.tolist(), se=np.nanstd(R, 0, ddof=1).tolist(),
                durations=list(range(1, report+1)), max_weight=float(w.max()), resamples=len(reps))

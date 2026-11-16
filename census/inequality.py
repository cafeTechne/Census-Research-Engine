# SPDX-License-Identifier: AGPL-3.0-or-later
"""Population-weighted area inequality, not individual-level inequality.

Areas have positive weights. Required ``higher_is_more_deprived`` declares
whether increasing x means greater deprivation. Weighted ridits run from least
(0) to most (1) deprived; ties share their block's weighted mid-rank. Positive
SII, log RII and C mean higher outcomes among more deprived areas. C therefore
has the reverse sign of the usual income-ranked concentration convention.
HC3 treats areas as independent; rank-error attenuation is not corrected.
"""
import numpy as np
import pandas as pd

from .results import ModelResult, precheck_replicates

TERMS = ("sii", "log_rii", "concentration_index")
DIRECTION_NOTE = ("Positive indices mean higher outcomes among more deprived areas; concentration "
                  "has the reverse sign of the usual income-ranked convention.")
RANK_ERROR_NOTE = "Median rank CV exceeds 15%; estimates may be attenuated by rank error."
# Set only from the pre-specified validation report, never from the example study.
INEQUALITY_VALIDATED = True  # docs/audits/inequality_validation.md (60330e3 criterion)


def _vectors(y, x, w, hi):
    if not isinstance(hi, (bool, np.bool_)):
        raise ValueError("higher_is_more_deprived must be a boolean")
    x, w = np.asarray(x, float), np.asarray(w, float)
    if x.ndim != 1 or x.shape != w.shape or not x.size:
        raise ValueError("rank and weights must be non-empty vectors of equal length")
    if not np.isfinite(x).all() or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError("rank and weights must be finite; weights must be positive")
    if y is not None:
        y = np.asarray(y, float)
        if y.shape != x.shape or not np.isfinite(y).all():
            raise ValueError("outcome must be a finite vector matching rank and weights")
    return y, x, w


def _ridits_batch(x, w, hi):
    """Rows are refits; sorting and tied-block mid-mass are vectorized."""
    order = np.argsort(x if hi else -x, axis=1, kind="stable")
    sx, sw = np.take_along_axis(x, order, 1), np.take_along_axis(w, order, 1)
    cum = np.cumsum(sw, axis=1)
    starts = np.concatenate((np.ones((len(x), 1), bool), sx[:, 1:] != sx[:, :-1]), axis=1)
    ends = np.concatenate((sx[:, 1:] != sx[:, :-1], np.ones((len(x), 1), bool)), axis=1)
    below = np.maximum.accumulate(np.where(starts, cum - sw, 0), axis=1)
    above = np.minimum.accumulate(np.where(ends, cum, np.inf)[:, ::-1], axis=1)[:, ::-1]
    sorted_r = (below + above) / (2 * cum[:, -1:])
    r = np.empty_like(sorted_r)
    np.put_along_axis(r, order, sorted_r, 1)
    return r


def ridits(x, w, higher_is_more_deprived):
    """Weighted mid-ranks from least to most deprived; tied blocks share a ridit."""
    _, x, w = _vectors(None, x, w, higher_is_more_deprived)
    return _ridits_batch(x[None], w[None], higher_is_more_deprived)[0]


def _indices(y, x, w, hi, model_se=False):
    """Batch WLS identities; HC3 uses the whitened WLS leverage and sandwich.

    Centering the design permits scalar bread/meat operations identical to
    statsmodels WLS(cov_type='HC3'), without 80 Python model fits per draw.
    """
    r = _ridits_batch(x, w, hi)
    W = w.sum(axis=1)
    rm, ym = (w*r).sum(axis=1)/W, (w*y).sum(axis=1)/W
    dr = r-rm[:, None]
    srr = (w*dr**2).sum(axis=1)
    if (srr <= 0).any():
        raise ValueError("inequality needs at least two distinct deprivation ranks")
    b = (w*dr*(y-ym[:, None])).sum(axis=1)/srr
    a = ym-b*rm
    valid = (a > 0) & (a+b > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_rii = np.where(valid, np.log((a+b)/a), np.nan)
        k = np.where(ym != 0, 2*srr/W/ym, np.nan)
        c = k*b
    estimates = np.column_stack((b, log_rii, c))
    if not model_se:
        return estimates
    if y.shape[1] < 3:
        raise ValueError("HC3 inequality requires at least three areas")
    h = w*(1/W[:, None] + dr**2/srr[:, None])
    if (h >= 1-1e-12).any():
        raise ValueError("HC3 is undefined for unit leverage")
    q2 = (w*(y-a[:, None]-b[:, None]*r)/(1-h))**2
    vb = (q2*dr**2).sum(axis=1)/srr**2
    vm = q2.sum(axis=1)/W**2
    cmb = (q2*dr).sum(axis=1)/(W*srr)
    with np.errstate(divide="ignore", invalid="ignore"):
        ga = 1/(a+b)-1/a
        gb = 1/(a+b)-ga*rm
        vl = ga**2*vm+gb**2*vb+2*ga*gb*cmb
        se = np.column_stack((np.sqrt(vb), np.where(valid, np.sqrt(np.maximum(0, vl)), np.nan),
                              np.abs(k)*np.sqrt(vb)))
    return estimates, se, a, b


def slope_index(y, x, w, higher_is_more_deprived):
    """SII and log RII from weighted ridits, with HC3 and delta-method SEs.

    Returns estimates, SEs, intercept/slope and notes. log RII is undefined
    when either fitted endpoint is nonpositive; no clipping is applied.
    """
    y, x, w = _vectors(y, x, w, higher_is_more_deprived)
    e, se, a, b = _indices(y[None], x[None], w[None], higher_is_more_deprived, True)
    notes = [DIRECTION_NOTE]
    if not np.isfinite(e[0, 1]):
        notes.append("log RII undefined: a fitted endpoint is nonpositive.")
    return dict(sii=float(e[0, 0]), se_sii=float(se[0, 0]), log_rii=float(e[0, 1]),
                se_log_rii=float(se[0, 1]), intercept=float(a[0]), slope=float(b[0]), notes=notes)


def concentration_index(y, x, w, higher_is_more_deprived):
    """C=2 cov_w(y,r)/mean_w(y), with approximate convenient-regression HC3 SE."""
    y, x, w = _vectors(y, x, w, higher_is_more_deprived)
    e, se, _, _ = _indices(y[None], x[None], w[None], higher_is_more_deprived, True)
    notes = [DIRECTION_NOTE, "Concentration SE is the convenient-regression HC3 approximation."]
    if not np.isfinite(e[0, 2]):
        notes.append("Concentration undefined: weighted outcome mean is zero.")
    return dict(concentration_index=float(e[0, 2]), se_concentration_index=float(se[0, 2]), notes=notes)


def inequality_replicate(frame, outcome, rank_by, weights, higher_is_more_deprived,
                         replicates, fixed=(), level=0.90, target="conservative"):
    """Three indices, refitting all 80 ACS replicates with fresh weighted ridits.

    Frame/long replicate keys are GEOID (+Year), as in fit_replicate. Missing
    stochastic variables/rows and invalid refits are refused, never held fixed
    silently. ``fixed`` explicitly declares external quantities held constant.
    Target population uses HC3, these_areas replicate SE, conservative their
    quadrature sum. No replicate source means model-only (reported in notes).
    """
    from .models import _replicate_matrices, _table
    from .results import stochastic_variables, IncompleteReplicatesError
    if target not in ("population", "these_areas", "conservative") or not 0 < level < 1:
        raise ValueError("invalid target or confidence level")
    variables = list(dict.fromkeys((outcome, rank_by, weights)))
    if set(fixed)-set(variables):
        raise ValueError("fixed must name outcome, rank_by or weights")
    y, x, w = _vectors(frame[outcome], frame[rank_by], frame[weights], higher_is_more_deprived)
    estimates, model, _, _ = _indices(y[None], x[None], w[None], higher_is_more_deprived, True)
    notes = [DIRECTION_NOTE, "HC3 assumes independent areas; no correction for rank-error attenuation."]
    mats, held = {}, {}
    active = [v for v in variables if v not in fixed]
    if replicates is not None and len(replicates):
        keys = ["GEOID"] + (["Year"] if "Year" in frame and "Year" in replicates else [])
        if frame.duplicated(keys).any() or replicates.duplicated(keys+["variable"]).any():
            raise ValueError("duplicate area/variable replicate keys")
        mats, held = _replicate_matrices(frame, replicates, active)
    missing = [v for v in stochastic_variables(frame, active) if v not in mats]
    precheck_replicates("strict", rows_held_fixed=held, variables_without_replicates=missing,
                       context="inequality")
    sampling = np.full(3, np.nan)
    if mats:
        batch = [mats.get(v, np.broadcast_to(frame[v].to_numpy(float)[:, None], (len(frame), 80))).T
                 for v in (outcome, rank_by, weights)]
        if not all(np.isfinite(b).all() for b in batch) or (batch[2] <= 0).any():
            raise IncompleteReplicatesError("inequality: invalid replicate values or nonpositive weights")
        try:
            rep = _indices(*batch, higher_is_more_deprived)
        except ValueError as exc:
            raise IncompleteReplicatesError(f"inequality: replicate refit failed: {exc}") from exc
        # Undefined full-sample log RII/C remain undefined, rather than failing SII.
        defined = np.isfinite(estimates[0])
        if not np.isfinite(rep[:, defined]).all():
            raise IncompleteReplicatesError("inequality: an estimable full-sample statistic has undefined refits")
        sampling = np.sqrt(.05*np.sum((rep-estimates)**2, axis=0))
    else:
        notes.append("No replicates: sampling SE unavailable; conservative intervals use model SE only.")
        if target == "these_areas":
            raise IncompleteReplicatesError("inequality: these_areas requires replicates")
    if not np.isfinite(estimates[0, 1]):
        notes.append("log RII undefined: a fitted endpoint is nonpositive.")
    if not np.isfinite(estimates[0, 2]):
        notes.append("Concentration undefined: weighted outcome mean is zero.")
    cv = np.full(len(frame), np.nan)
    if rank_by+"_se" in frame:
        rank_se = frame[rank_by+"_se"].to_numpy(float)
    elif rank_by in mats:
        rank_se = np.sqrt(.05*np.sum((mats[rank_by]-x[:, None])**2, axis=1))
    else:
        rank_se = np.zeros(len(frame))  # explicitly nonstochastic rank
    np.divide(100*rank_se, np.abs(x), out=cv, where=x != 0)
    cv[(x == 0) & (rank_se > 0)] = np.inf
    median = float(np.nanmedian(cv)) if (~np.isnan(cv)).any() else float("nan")
    if median > 15:
        notes.append(RANK_ERROR_NOTE)
    coefs = _table(pd.Series(estimates[0], index=TERMS), pd.Series(model[0], index=TERMS),
                    pd.Series(sampling, index=TERMS), level, target)
    return ModelResult("inequality", f"{outcome} ~ ridit({rank_by})", len(frame), coefs,
                       "inequality", ["model"]+(["sampling_replicate"] if mats else []), level,
                       notes=notes, diagnostics={"interval_target": target, "rank_cv_median": median,
                                               "fixed_variables": list(fixed)})

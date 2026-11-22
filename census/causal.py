# SPDX-License-Identifier: AGPL-3.0-or-later
"""Treatment effects, instrumental variables and mediation for area data (Round 41).

Validated by ``docs/audits/causal_validation.md`` (criterion b7464e5), 145 independent areas:
- average treatment effects (IPW, AIPW, regression adjustment): .894-.899 with exact or reliability-0.9
  confounders. The design did not test residual confounding from noisy confounders (their biases
  cancelled), so error-prone confounders remain a stated risk;
- 2SLS with an independent second measurement of an error-prone covariate as the instrument:
  .882-.907, removing the attenuation that drops naive OLS coverage to .30;
- mediation (Sobel, percentile bootstrap) with an exactly measured mediator: .876-.891; with mediator
  sampling error (reliability 0.8) coverage fell to .69-.72, so error-prone mediators are exploratory.
Round 47 (``docs/audits/causal_robustness_validation.md``, criterion cbdc97f) added, all passing:
- ``calibrate=True`` treatment effects: AIPW on confounders regression-calibrated within treatment
  groups, percentile bootstrap (.889-.905 with same-sign noisy confounders at reliability .7-.9, where
  plain AIPW fell to .77-.87);
- the Anderson-Rubin interval for ``iv_slope`` (.894-.908 in every first-stage F bin, F from 0 to 30+);
  the 2SLS Wald interval also covered at every F in this design (cut-off 0), but its point estimate is
  unstable below F = 10;
- ``calibrate=True`` mediation: calibrated mediator path with a percentile bootstrap (.883-.898).
Causal readings require the stated assumptions; a registered design is needed for confirmatory claims.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import causal_core as cc
from . import causal_robustness_core as cr

AUDIT = "docs/audits/causal_validation.md"
ROBUST_AUDIT = "docs/audits/causal_robustness_validation.md"
# Round 47 outcomes (tests/test_round47.py checks these against the audit JSON)
CALIBRATED_TREATMENT_VALIDATED = True
CALIBRATED_MEDIATION_VALIDATED = True
AR_VALIDATED = True
IV_WALD_F_CUTOFF = 0      # smallest first-stage F at which the 2SLS Wald interval covered (pre-set bins)
IV_UNSTABLE_F = 10        # below this, 2SLS point estimates were unstable in validation (mean bias ~ +-1)


def _cols(frame, cols):
    f = frame.dropna(subset=list(cols)).reset_index(drop=True)
    return f, [pd.to_numeric(f[c], errors="coerce").to_numpy(float) for c in cols]


def _has_error(frame, col, replicates):
    return f"{col}_se" in frame or f"{col}_moe" in frame or (
        replicates is not None and col in set(replicates["variable"].astype(str)))


def _error_variance(f, col):
    """Per-area error variance from ``<col>_se`` or ``<col>_moe`` (90% MOE / 1.645)."""
    if f"{col}_se" in f:
        se = pd.to_numeric(f[f"{col}_se"], errors="coerce").to_numpy(float)
    elif f"{col}_moe" in f:
        se = pd.to_numeric(f[f"{col}_moe"], errors="coerce").to_numpy(float)/1.645
    else:
        raise ValueError(f"calibrate=True needs {col}_se or {col}_moe for {col!r}")
    if not (np.isfinite(se).all() and (se >= 0).all()):
        raise ValueError(f"{col}: standard errors must be finite and non-negative")
    return se**2


def estimate_effect(frame: pd.DataFrame, outcome: str, treatment: str, confounders: Sequence[str],
                    method: str = "aipw", replicates: Optional[pd.DataFrame] = None,
                    calibrate: bool = False, seed: int = 20270501, weights: Optional[str] = None) -> Dict[str, Any]:
    """Average effect of a binary area-level treatment (0/1) adjusting for ``confounders``.

    ``calibrate=True`` (AIPW only; Round 47, validated) replaces every confounder with an SE column
    (``_se`` or ``_moe``) by E[Z | W, T], calibrated within each treatment group, and reports a 90%
    percentile bootstrap (200 resamples re-estimating the calibration). Validated with all confounders
    error-prone; error-free confounders are kept as they are and do not enter the calibration."""
    if method not in ("ipw", "aipw", "ra"):
        raise ValueError("method must be 'aipw' (doubly robust; default), 'ipw' or 'ra'")
    if calibrate and method != "aipw":
        raise ValueError("calibrate=True is validated for method='aipw' only")
    f, vals = _cols(frame, [outcome, treatment]+list(confounders))
    y, T, Z = vals[0], vals[1], np.column_stack(vals[2:])
    if set(np.unique(T)) - {0., 1.}:
        raise ValueError("treatment must be coded 0/1")
    if min(T.sum(), (1-T).sum()) < 10:
        raise ValueError("each treatment group needs at least 10 areas")
    noisy = [c for c in confounders if _has_error(f, c, replicates)]
    from . import positivity as pz  # Round 90
    if weights is not None:
        if calibrate:
            raise ValueError("weights= and calibrate=True cannot be combined (not validated together)")
        if weights not in ("stabilized", "truncated", "overlap"):
            raise ValueError("weights must be 'stabilized', 'truncated' or 'overlap'")
        out = pz.weighted(y, T, Z, weights)
        out["notes"] = ["Assumes no unmeasured confounding; areas independent."]+out["notes"]
        if noisy:
            out["notes"].append(f"Confounders with sampling error {noisy} leave residual confounding (Round 47).")
            out["validated"] = False
        return dict(out, n=len(y), n_treated=int(T.sum()))
    positivity = pz.diagnose(T, Z)
    notes = ["Assumes no unmeasured confounding and overlap; areas independent. Propensity diagnostics are in "
             "'positivity' (Round 90)."]
    if positivity["limited_overlap"]:
        notes.append(f"Limited overlap: {positivity['share_outside']:.0%} of propensities lie outside [.05, .95] "
                     "(Hernán and Robins 3.3). IP weighting under-covered there in validation; prefer "
                     "weights='overlap' (overlap-population effect) or method='ra' (g-formula), both validated "
                     f"({pz.AUDIT}), or restrict the population to areas with overlap. AIPW (validated in Round 41 "
                     "with good overlap) was not tested under limited overlap.")
    if calibrate:
        cal = [c for c in confounders if f"{c}_se" in f or f"{c}_moe" in f]
        if not cal:
            raise ValueError("calibrate=True needs confounders with _se or _moe columns")
        idx = [list(confounders).index(c) for c in cal]
        S2 = np.column_stack([_error_variance(f, c) for c in cal])
        if len(cal) == len(confounders):
            out = cr.aipw_calibrated(y, T, Z, S2, np.random.default_rng(seed))
        else:
            out = _aipw_calibrated_mixed(y, T, Z, idx, S2, np.random.default_rng(seed))
            notes.append("Error-free confounders were not part of the validated design (all confounders were "
                         "error-prone there); they are passed to the propensity and outcome models unchanged.")
        notes.append(f"Confounders {cal} regression-calibrated within treatment groups (Round 47, {ROBUST_AUDIT}); "
                     "the interval is a percentile bootstrap. Assumes errors independent of each other and of the "
                     "true values.")
        return dict(kind="treatment", method="aipw_calibrated", ate=out, n=len(y), n_treated=int(T.sum()),
                    validated=CALIBRATED_TREATMENT_VALIDATED, calibrated=cal, notes=notes, audit=ROBUST_AUDIT,
                    positivity=positivity)
    out = cc.treatment_effect(y, T, Z, method)
    if noisy:
        notes.append(f"Confounders with sampling error {noisy}: plain AIPW leaves residual confounding (Round 47: "
                     "coverage .77-.87 at reliability .7-.9). Use calibrate=True with _se columns (validated).")
    validated = not noisy and not (method == "ipw" and positivity["limited_overlap"])
    return dict(kind="treatment", method=method, ate=out, n=len(y), n_treated=int(T.sum()), validated=validated,
                notes=notes, audit=AUDIT, positivity=positivity)


def _aipw_calibrated_mixed(y, T, Z, idx, S2, rng, boot=200):
    """``cr.aipw_calibrated`` with some error-free columns left uncalibrated (same bootstrap)."""
    def point(i):
        Zi = Z[i].copy()
        Zi[:, idx] = cr._calibrate_within(T[i], Z[i][:, idx], S2[i])
        return cr.aipw_point(y[i], T[i], Zi)
    n = len(y); est = point(np.arange(n)); reps = []
    for _ in range(boot):
        i = rng.integers(0, n, n)
        if min(T[i].sum(), (1-T[i]).sum()) < Z.shape[1]+3:
            continue
        try:
            reps.append(point(i))
        except (ValueError, np.linalg.LinAlgError):
            continue
    if len(reps) < .9*boot:
        raise ValueError("too many failed bootstrap resamples")
    lo, hi = np.quantile(reps, [.05, .95])
    return dict(estimate=est, se=float(np.std(reps, ddof=1)), lower=float(lo), upper=float(hi), resamples=len(reps))


def iv_slope(frame: pd.DataFrame, outcome: str, x: str, instrument: str,
             controls: Sequence[str] = ()) -> Dict[str, Any]:
    """Slope of an error-prone ``x`` instrumented by an independent second measurement of the same quantity."""
    f, vals = _cols(frame, [outcome, x, instrument]+list(controls))
    C = np.column_stack(vals[3:]) if controls else None
    iv = cc.iv_2sls(vals[0], vals[1], vals[2], C); ols = cc.ols_slope(vals[0], vals[1], C)
    r = np.corrcoef(vals[1], vals[2])[0, 1]
    F = first_stage_f(vals[1], vals[2], C)
    ar = cr.anderson_rubin(vals[0], vals[1], vals[2], C)
    notes = ["Valid only if the instrument's error is independent of x's error and of the outcome (exclusion "
             "restriction): e.g. a non-overlapping ACS release or a different survey of the same quantity.",
             f"First-stage F = {F:.1f}. Anderson-Rubin interval ({ar['kind']}) is valid at any instrument strength "
             f"(Round 47, {ROBUST_AUDIT})."]
    if F < IV_UNSTABLE_F:
        notes.append(f"WEAK INSTRUMENT: F < {IV_UNSTABLE_F}. The 2SLS point estimate is unstable (Round 47: mean bias "
                     "about +-1 on a slope of .5 at F 2-5) and its Wald interval is very wide; report the "
                     "Anderson-Rubin interval, which may be unbounded.")
    return dict(kind="iv", iv=iv, ar_interval=ar, ols_naive=ols, first_stage_corr=float(r), first_stage_f=F,
                n=len(vals[0]), validated=F >= IV_WALD_F_CUTOFF, ar_validated=AR_VALIDATED, notes=notes,
                audit=ROBUST_AUDIT)


def first_stage_f(x, instrument, controls=None) -> float:
    """Classical F for the single instrument in the first stage x ~ 1 + instrument (+ controls)."""
    import statsmodels.api as sm
    Z = np.column_stack([np.ones(len(x)), instrument] + ([controls] if controls is not None else []))
    fit = sm.OLS(np.asarray(x, float), Z).fit()
    return float(fit.tvalues[1]**2)


def mediation(frame: pd.DataFrame, x: str, mediator: str, outcome: str, controls: Sequence[str] = (),
              method: str = "bootstrap", replicates: Optional[pd.DataFrame] = None, seed: int = 20270225,
              calibrate: bool = False) -> Dict[str, Any]:
    """Indirect effect of ``x`` on ``outcome`` through ``mediator`` (product of coefficients).

    ``calibrate=True`` (Round 47, validated; no controls, bootstrap only): the a-path from mediator ~ x,
    the b-path from outcome ~ x + E[M | W, x] using the mediator's ``_se``/``_moe`` column; 90% percentile
    bootstrap with 400 resamples re-estimating the calibration."""
    if method not in ("bootstrap", "sobel"):
        raise ValueError("method must be 'bootstrap' (default) or 'sobel'")
    if calibrate:
        if controls or method != "bootstrap":
            raise ValueError("calibrate=True is validated without controls and with method='bootstrap' only")
        f, vals = _cols(frame, [x, mediator, outcome])
        out = cr.mediation_calibrated(vals[0], vals[1], _error_variance(f, mediator), vals[2],
                                      np.random.default_rng(seed))
        notes = ["Assumes sequential ignorability (no unmeasured mediator-outcome confounding).",
                 f"Mediator regression-calibrated (Round 47, {ROBUST_AUDIT}); x is assumed error-free."]
        return dict(kind="mediation", method="bootstrap_calibrated", indirect=out, n=len(vals[0]),
                    validated=CALIBRATED_MEDIATION_VALIDATED, notes=notes, audit=ROBUST_AUDIT)
    f, vals = _cols(frame, [x, mediator, outcome]+list(controls))
    C = np.column_stack(vals[3:]) if controls else None
    out = cc.mediation(vals[0], vals[1], vals[2], method, np.random.default_rng(seed), controls=C)
    noisy = _has_error(f, mediator, replicates)
    notes = ["Assumes sequential ignorability (no unmeasured mediator-outcome confounding)."]
    if noisy:
        notes.append("EXPLORATORY: the mediator has sampling error; validation coverage fell to .69-.72 "
                     f"(attenuated indirect effect) ({AUDIT}). Use calibrate=True with a _se column (Round 47, validated).")
    return dict(kind="mediation", method=method, indirect=out, n=len(vals[0]), validated=not noisy, notes=notes, audit=AUDIT)

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
Causal readings require the stated assumptions; a registered design is needed for confirmatory claims.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import causal_core as cc

AUDIT = "docs/audits/causal_validation.md"


def _cols(frame, cols):
    f = frame.dropna(subset=list(cols)).reset_index(drop=True)
    return f, [pd.to_numeric(f[c], errors="coerce").to_numpy(float) for c in cols]


def _has_error(frame, col, replicates):
    return f"{col}_se" in frame or f"{col}_moe" in frame or (
        replicates is not None and col in set(replicates["variable"].astype(str)))


def estimate_effect(frame: pd.DataFrame, outcome: str, treatment: str, confounders: Sequence[str],
                    method: str = "aipw", replicates: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Average effect of a binary area-level treatment (0/1) adjusting for ``confounders``."""
    if method not in ("ipw", "aipw", "ra"):
        raise ValueError("method must be 'aipw' (doubly robust; default), 'ipw' or 'ra'")
    f, vals = _cols(frame, [outcome, treatment]+list(confounders))
    y, T, Z = vals[0], vals[1], np.column_stack(vals[2:])
    if set(np.unique(T)) - {0., 1.}:
        raise ValueError("treatment must be coded 0/1")
    if min(T.sum(), (1-T).sum()) < 10:
        raise ValueError("each treatment group needs at least 10 areas")
    out = cc.treatment_effect(y, T, Z, method)
    noisy = [c for c in confounders if _has_error(f, c, replicates)]
    notes = ["Assumes no unmeasured confounding and overlap (check the propensity distribution); areas independent."]
    if noisy:
        notes.append(f"Confounders with sampling error {noisy}: residual confounding is possible and was not "
                     "ruled out by validation; consider a sensitivity analysis.")
    return dict(kind="treatment", method=method, ate=out, n=len(y), n_treated=int(T.sum()), validated=True,
                notes=notes, audit=AUDIT)


def iv_slope(frame: pd.DataFrame, outcome: str, x: str, instrument: str,
             controls: Sequence[str] = ()) -> Dict[str, Any]:
    """Slope of an error-prone ``x`` instrumented by an independent second measurement of the same quantity."""
    f, vals = _cols(frame, [outcome, x, instrument]+list(controls))
    C = np.column_stack(vals[3:]) if controls else None
    iv = cc.iv_2sls(vals[0], vals[1], vals[2], C); ols = cc.ols_slope(vals[0], vals[1], C)
    r = np.corrcoef(vals[1], vals[2])[0, 1]
    F = first_stage_f(vals[1], vals[2], C)
    notes = ["Valid only if the instrument's error is independent of x's error and of the outcome (exclusion "
             "restriction): e.g. a non-overlapping ACS release or a different survey of the same quantity.",
             f"First-stage F = {F:.1f}. Validation used strong instruments only; the weak-instrument cut-off "
             "(corr < 0.3) is a convention, not yet validated (ROADMAP_BACKLOG.md Round 47)."]
    if abs(r) < .3:
        notes.append(f"WEAK INSTRUMENT: corr(x, instrument) = {r:.2f}; 2SLS is unreliable.")
    return dict(kind="iv", iv=iv, ols_naive=ols, first_stage_corr=float(r), first_stage_f=F, n=len(vals[0]),
                validated=abs(r) >= .3, notes=notes, audit=AUDIT)


def first_stage_f(x, instrument, controls=None) -> float:
    """Classical F for the single instrument in the first stage x ~ 1 + instrument (+ controls)."""
    import statsmodels.api as sm
    Z = np.column_stack([np.ones(len(x)), instrument] + ([controls] if controls is not None else []))
    fit = sm.OLS(np.asarray(x, float), Z).fit()
    return float(fit.tvalues[1]**2)


def mediation(frame: pd.DataFrame, x: str, mediator: str, outcome: str, controls: Sequence[str] = (),
              method: str = "bootstrap", replicates: Optional[pd.DataFrame] = None, seed: int = 20270225) -> Dict[str, Any]:
    """Indirect effect of ``x`` on ``outcome`` through ``mediator`` (product of coefficients)."""
    if method not in ("bootstrap", "sobel"):
        raise ValueError("method must be 'bootstrap' (default) or 'sobel'")
    f, vals = _cols(frame, [x, mediator, outcome]+list(controls))
    C = np.column_stack(vals[3:]) if controls else None
    out = cc.mediation(vals[0], vals[1], vals[2], method, np.random.default_rng(seed), controls=C)
    noisy = _has_error(f, mediator, replicates)
    notes = ["Assumes sequential ignorability (no unmeasured mediator-outcome confounding)."]
    if noisy:
        notes.append("EXPLORATORY: the mediator has sampling error; validation coverage fell to .69-.72 "
                     f"(attenuated indirect effect) ({AUDIT}).")
    return dict(kind="mediation", method=method, indirect=out, n=len(vals[0]), validated=not noisy, notes=notes, audit=AUDIT)

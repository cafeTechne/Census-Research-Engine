# SPDX-License-Identifier: AGPL-3.0-or-later
"""Marginal (standardized) risk ratios and differences, prevalence ratios, attributable fractions and
dose-response trends (Round 84; backlog N61; Foundations of Epidemiology chapters 4 and 10).

Validation: ``docs/audits/epi_measures_validation.md`` (criterion ``epi_measures_validation_criterion.md``): every
candidate passed - area g-computation RR, RD and PAF with HC3 delta SEs (.862-.898), PUMS g-computation RR, RD and
PAF with SDR SEs (.866-), modified-Poisson prevalence ratios with SDR SEs (.869-), and dose-response trend tests
(size .083-.129 at .10). Odds ratios overstate risk ratios for common outcomes, so binomial and logit results pair
every OR with the marginal RR when the outcome prevalence exceeds 10%.
"""
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import epi_measures_core as em

AUDIT = "docs/audits/epi_measures_validation.md"
VALIDATED = {"area_marginal": True, "area_paf": True, "area_dose": True, "pums_marginal": True, "pums_paf": True,
             "prevalence_ratio": True, "pums_dose": True}
COMMON_OUTCOME = .10
OR_NOTE = ("The outcome is common (prevalence above 10%): odds ratios overstate risk ratios, so report the marginal "
           "(standardized) risk ratio and risk difference.")


def _design(formula, frame):
    import patsy
    lhs, rhs = formula.split("~", 1)
    y, X = patsy.dmatrices(f"{lhs} ~ {rhs}", frame, return_type="dataframe", NA_action="drop")
    return y.iloc[:, 0], X


def area_marginal_measures(frame: pd.DataFrame, formula: str, trials: str, exposure: str,
                           values: Optional[Sequence[float]] = None, level: float = .90,
                           dose_levels: int = 0) -> Dict[str, Any]:
    """Area binomial model (outcome a proportion or percent, ``trials`` its denominator): marginal RR and RD for
    ``exposure`` at values[1] vs values[0] (default: its 25th and 75th percentiles), the PAF for setting every area
    to values[0], and optionally a dose-response test over ``dose_levels`` quantile groups of the exposure."""
    y, X = _design(formula, frame)
    if exposure not in X.columns:
        raise ValueError(f"exposure {exposure!r} must be a numeric term of the formula")
    rows = y.index
    yv = y.to_numpy(float)
    if np.nanmax(yv) > 1:
        yv = yv/100
    w = frame.loc[rows, trials].to_numpy(float)
    col = list(X.columns).index(exposure)
    xv = X[exposure].to_numpy(float)
    lo, hi = (np.quantile(xv, [.25, .75]) if values is None else values)
    r = em.area_marginal(yv, X.to_numpy(float), w, [col], float(lo), float(hi), level)
    prev = float(np.average(yv, weights=w))
    out = dict(exposure=exposure, low=float(lo), high=float(hi), risk_low=float(r["risks"][0]),
               risk_high=float(r["risks"][1]), rr=float(r["rr"]), rr_lower=float(r["rr_lower"]),
               rr_upper=float(r["rr_upper"]), rd=float(r["rd"]), rd_lower=float(r["rd_lower"]),
               rd_upper=float(r["rd_upper"]), paf=float(r["paf"]), paf_lower=float(min(r["paf_lower"], r["paf_upper"])),
               paf_upper=float(max(r["paf_lower"], r["paf_upper"])), prevalence=prev, level=level,
               validated=VALIDATED["area_marginal"], audit=AUDIT,
               notes=["Marginal (standardized) measures average every area's predicted risk with the exposure set to "
                      "each value (g-computation; HC3 delta SEs, population target). The attributable fraction is the "
                      "share of the outcome that would not occur if every area had the low exposure value; fractions "
                      "over several causes sum past 100%."])
    if prev > COMMON_OUTCOME:
        out["notes"].append(OR_NOTE)
    if dose_levels >= 3:
        q = np.quantile(xv, np.linspace(0, 1, dose_levels+1)[1:-1])
        lev = np.digitize(xv, q)
        D = np.eye(dose_levels)[lev][:, 1:]
        others = [c for c in X.columns if c != exposure]
        XD = np.column_stack([X[others].to_numpy(float), D])
        cols = list(range(len(others), XD.shape[1]))
        settings = [np.eye(dose_levels)[k][1:] for k in range(dose_levels)]
        out["dose_response"] = {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                                for k, v in em.area_dose(yv, XD, w, cols, settings, level).items()}
    return out


def pums_marginal_measures(y: np.ndarray, X: np.ndarray, W: np.ndarray, col: int, level: float = .90,
                           prevalence_ratio: bool = True) -> Dict[str, Any]:
    """PUMS 0/1 outcome, binary exposure column ``col`` of X: marginal RR, RD, PAF (SDR) and the modified-Poisson
    prevalence ratio (SDR; model-robust comparison)."""
    r = em.replicate_marginal(y, X, W, [col], 0.0, 1.0, level)
    out = {k: float(v) for k, v in r.items() if k != "se"}
    out["paf_lower"], out["paf_upper"] = sorted((out["paf_lower"], out["paf_upper"]))
    prev = float(np.average(y, weights=W[:, 0]))
    out.update(prevalence=prev, validated=VALIDATED["pums_marginal"], audit=AUDIT, notes=[])
    if prevalence_ratio:
        out["prevalence_ratio"] = em.prevalence_ratio(y, X, W, col, level)
    if prev > COMMON_OUTCOME:
        out["notes"].append(OR_NOTE)
    return out

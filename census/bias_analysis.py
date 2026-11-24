# SPDX-License-Identifier: AGPL-3.0-or-later
"""Quantitative bias analysis (Round 86; backlog N63; Foundations of Epidemiology chapters 6-7).

Validation: ``docs/audits/bias_analysis_validation.md`` (criterion ``bias_analysis_validation_criterion.md``):
- E-values (VanderWeele and Ding 2017) are deterministic and reproduce the published example (RR 3.9 -> 7.26;
  limit 1.8 -> 3.00): available everywhere.
- The probabilistic misclassification analysis **failed** its coverage criterion (.76-.83 under correct priors with a
  null effect or exposure misclassification; near 1.00 with differential outcome misclassification): its interval
  is exploratory. The simple (fixed Se/Sp) correction is a point correction with no interval. Both show how far
  plausible misclassification could move an estimate; neither is a confirmatory result.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np

from . import bias_analysis_core as bc

AUDIT = "docs/audits/bias_analysis_validation.md"
REPAIRS_AUDIT = "docs/audits/repairs105_validation.md"
VALIDATED = {"e_value": True, "probabilistic_misclassification": True}
E_NOTE = ("E-value: the minimum strength of association (risk-ratio scale) an unmeasured confounder would need with "
          "both the exposure and the outcome to explain away the estimate (and, for the limit, to move the interval "
          "to include the null). Large values mean robust to unmeasured confounding; it is not a test.")


def e_value(estimate: float, lower: Optional[float] = None, upper: Optional[float] = None, measure: str = "rr",
            prevalence: Optional[float] = None) -> Dict[str, Any]:
    out = bc.e_value(estimate, lower, upper, measure, prevalence)
    out.update(validated=True, note_text=E_NOTE, audit=AUDIT)
    return out


def misclassification(a: float, b: float, c: float, d: float, sensitivity: Any, specificity: Any,
                      kind: str = "outcome", sd: Optional[float] = None, draws: int = 20000,
                      seed: int = 20282686) -> Dict[str, Any]:
    """Correct a 2 x 2 table (a, b exposed cases / non-cases; c, d unexposed) for misclassification.
    ``sensitivity``/``specificity``: a value (nondifferential) or a pair (exposed, unexposed for outcome; cases,
    non-cases for exposure). With ``sd`` a probabilistic analysis with beta priors of that SD is added (exploratory)."""
    se = np.atleast_1d(np.asarray(sensitivity, float)); sp = np.atleast_1d(np.asarray(specificity, float))
    diff = len(se) == 2 or len(sp) == 2
    se2 = se if len(se) == 2 else np.repeat(se, 2); sp2 = sp if len(sp) == 2 else np.repeat(sp, 2)
    A, B, C, D = bc.corrected_table(a, b, c, d, se2, sp2, kind)
    if min(A, B, C, D) <= 0:
        raise ValueError("these sensitivity and specificity values imply impossible (non-positive) corrected counts")
    with np.errstate(divide="ignore", invalid="ignore"):
        obs = dict(rr=(a/(a+b))/(c/(c+d)), **{"or": a*d/(b*c)})
        cor = dict(rr=(A/(A+B))/(C/(C+D)), **{"or": A*D/(B*C)})
    out = dict(kind=kind, differential=diff, observed={k: float(v) for k, v in obs.items()},
               corrected={k: float(v) for k, v in cor.items()}, corrected_table=[float(A), float(B), float(C), float(D)],
               audit=AUDIT, validated=False,
               notes=["Bias analysis shows how much plausible misclassification could move the estimate; it is a "
                      "sensitivity analysis, not a corrected confirmatory result."])
    if sd:
        from . import repairs105_core as r105
        prior_se = tuple((float(s), sd) for s in se2) if diff else (float(se[0]), sd)
        prior_sp = tuple((float(s), sd) for s in sp2) if diff else (float(sp[0]), sd)
        pr = r105.probabilistic_propagated(a, b, c, d, prior_se, prior_sp, kind, draws,
                                           rng=np.random.default_rng(seed), differential=diff)
        out["probabilistic"] = pr
        out["validated"] = bool(VALIDATED["probabilistic_misclassification"])
        out["audit"] = REPAIRS_AUDIT
        out["notes"].append(f"Probabilistic interval propagates observed-table sampling error through the "
                            f"misclassification inversion (validated under correctly specified priors in Round 105, "
                            f"{REPAIRS_AUDIT}).")
    return out


def both_directions(with_covariable: float, without_covariable: float, name: str) -> Dict[str, Any]:
    """Chapter 7 practice for a covariable of uncertain causal direction: report both estimates."""
    r = bc.both_directions(with_covariable, without_covariable)
    r["note"] = (f"The causal direction between {name} and the outcome is uncertain, so the estimate is reported with "
                 f"and without adjusting for it; if they differ materially, report both.")
    return r

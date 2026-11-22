# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 90: positivity diagnostics and weighting options for area treatment effects (backlog N66).

Validation (``docs/audits/positivity_validation.md``; criterion tag ``criterion-r90``), 145 or 600 areas with 0%, 5%
or 15% of propensities outside [.05, .95]:
- passed: weights truncated at the 1st/99th percentiles (.864-.905), overlap weights for the overlap-population
  effect (.877-.906), the g-formula / regression adjustment (.881-.907), and the IPW-versus-g-formula flag (size
  .000-.061);
- failed: stabilized IP weights (.807-.863 once 5% or more of propensities are extreme; .886-.902 without extreme
  propensities). Plain IPW (``method="ipw"``) gives the same estimate and failed alike (.814-.871).
Hernán and Robins, *What If*, chapters 3.3, 12, 13 and 15; Li, Morgan and Zaslavsky (2018).
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import positivity_core as pc

AUDIT = "docs/audits/positivity_validation.md"
VALIDATED = {"stabilized": False, "truncated": True, "overlap": True, "g_formula": True, "flag": True}
LIMITED = .05  # share of propensities outside [.05, .95] above which IPW failed validation


def diagnose(T, Z) -> Dict[str, Any]:
    """Propensity diagnostics with stabilized weights (always reported by estimate_effect)."""
    T = np.asarray(T, float)
    _, e = pc.propensity(T, Z)
    w = np.where(T == 1, T.mean()/e, (1-T.mean())/(1-e))
    d = pc.diagnostics(T, Z, e, w)
    d["limited_overlap"] = d["share_outside"] >= LIMITED
    return d


def weighted(y, T, Z, weights: str) -> Dict[str, Any]:
    """A weighted estimate with diagnostics, the g-formula beside it and the agreement flag."""
    est, e, w = pc.weighted_effect(y, T, Z, weights)
    g = pc.g_formula(y, T, Z)
    d = pc.diagnostics(T, Z, e, w)
    d["limited_overlap"] = d["share_outside"] >= LIMITED
    notes = []
    if weights == "overlap":
        notes.append("Overlap weights estimate the effect in the overlap population (areas that could plausibly have "
                     "been treated or not), not the average effect over all areas; report it as such.")
    if weights == "stabilized" and d["limited_overlap"]:
        notes.append(f"{d['share_outside']:.0%} of propensities lie outside [.05, .95]: stabilized IP weights "
                     "under-covered in validation (.807-.863); use weights='overlap', weights='truncated' or "
                     "method='ra' (g-formula).")
    agree = pc.agreement(est, g)
    if agree["flagged"]:
        notes.append("IP weighting and the g-formula disagree by more than the sum of their SEs: the propensity or "
                     "outcome model is likely misspecified (Hernán and Robins 13.5).")
    validated = VALIDATED[weights]
    return dict(kind="treatment", method=f"ipw_{weights}", ate=est, g_formula=g, agreement=agree, positivity=d,
                validated=validated, notes=notes, audit=AUDIT)

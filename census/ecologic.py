# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ecologic versus individual-level associations on PUMS (Round 87; backlog N64; Foundations of Epidemiology
chapter 9: the ecologic fallacy).

Validation: ``docs/audits/ecologic_validation.md`` (criterion ``ecologic_validation_criterion.md``); computation is the
frozen core :mod:`census.ecologic_core`.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np

from . import ecologic_core as ec

AUDIT = "docs/audits/ecologic_validation.md"
VALIDATED_FROM = {"C1": None, "C2": None, "C1l": None}  # smallest validated record count, None = failed; from the audit
NOTE = ("within = the association of a person's own exposure with their outcome inside areas (individual level); "
        "between = the association of area means; contextual = between - within, the area-mean association beyond "
        "the person's own exposure; ecologic = what an area-level (ACS-only) analysis estimates; ecologic_gap = "
        "ecologic - within, the ecologic bias for this question. A contextual effect is an area-level association, "
        "not proof of an area cause: composition and omitted individual confounders remain.")


def ecologic_check(y: np.ndarray, x: np.ndarray, area: np.ndarray, W: np.ndarray, Z: Optional[np.ndarray] = None,
                   binary: bool = False, level: float = .90) -> Dict[str, Any]:
    """Within / between / contextual associations and the ecologic gap (identity scale; for 0/1 outcomes also the
    logit decomposition)."""
    lin, n_areas = ec.decompose(y, x, area, W, Z, logit=False, level=level)
    n = len(y)
    def ok(fam):
        gate = VALIDATED_FROM[fam]
        return gate is not None and n >= gate
    out = dict(identity={k: dict(estimate=v[0], se=v[1], lower=v[2], upper=v[3]) for k, v in lin.items()},
               areas=int(n_areas), records=int(n), level=level, audit=AUDIT, notes=[NOTE],
               validated={"within_between_contextual": ok("C1"), "ecologic_gap": ok("C2")})
    if binary:
        lg, _ = ec.decompose(y, x, area, W, Z, logit=True, level=level)
        out["logit"] = {k: dict(estimate=v[0], se=v[1], lower=v[2], upper=v[3]) for k, v in lg.items()}
        out["validated"]["logit"] = ok("C1l")
        out["notes"].append("For a 0/1 outcome the identity-scale results are risk differences per unit of exposure; "
                            "the logit results are log-odds ratios.")
    return out

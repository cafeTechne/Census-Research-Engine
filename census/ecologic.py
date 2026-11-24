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
REPAIRS_AUDIT = "docs/audits/repairs109_validation.md"
VALIDATED_FROM = {"C1": None, "C2": None, "C1l": 5000}
FULLER_ECOLOGIC_VALIDATED = True
FULLER_MIN_AREAS = 50
FULLER_MIN_MEDIAN_N = 80
# docs/audits/ecologic_validation.json: the logit decomposition (C1l) passed in every binary cell (>= .871); the
# linear decomposition (C1) and the ecologic slope and gap (C2) failed with 150 small areas (about 33 records per area:
# noisy area means bias the between-area slope; .62-.86) and are exploratory. The within-area slope covered
# everywhere but is judged with its family.
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
    # Round 109: Fuller (1987, alpha=4) reliability-corrected ecologic/between-area slope (E3d)
    from . import repairs109_core as r109
    a_arr = np.asarray(area)
    uniq = np.unique(a_arr)
    if len(uniq) >= 3:
        ax = np.array([float(np.mean(x[a_arr == u])) for u in uniq])
        ay = np.array([float(np.mean(y[a_arr == u])) for u in uniq])
        ns = np.array([int(np.sum(a_arr == u)) for u in uniq])
        vx = np.array([float(np.var(x[a_arr == u], ddof=1) / max(int(np.sum(a_arr == u)), 1))
                       if int(np.sum(a_arr == u)) > 1 else 0.0 for u in uniq])
        med_n = float(np.median(ns))
        fe = r109.ecologic_fuller_slope(ax, ay, vx, alpha=4.0, level=level)
        fe["median_area_n"] = med_n
        fe["validated"] = bool(FULLER_ECOLOGIC_VALIDATED and len(uniq) >= FULLER_MIN_AREAS and med_n >= FULLER_MIN_MEDIAN_N)
        fe["audit"] = REPAIRS_AUDIT
        out["ecologic_fuller"] = fe
    if binary:
        lg, _ = ec.decompose(y, x, area, W, Z, logit=True, level=level)
        out["logit"] = {k: dict(estimate=v[0], se=v[1], lower=v[2], upper=v[3]) for k, v in lg.items()}
        out["validated"]["logit"] = ok("C1l")
        out["notes"].append("For a 0/1 outcome the identity-scale results are risk differences per unit of exposure; "
                            "the logit results are log-odds ratios.")
    return out

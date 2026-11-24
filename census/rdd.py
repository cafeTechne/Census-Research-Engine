# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 98: regression discontinuity designs (backlog N75; Cunningham, *Mixtape*; Calonico, Cattaneo and Titiunik
2014; Imbens and Kalyanaraman 2012; McCrary 2008).

Validation (``docs/audits/rdd_validation.md``; criterion tag ``criterion-r98``):
- discrete running variables with survey replicate weights (PUMS ages): robust bias-corrected intervals with
  replicate SEs covered .893-.906 (sharp and fuzzy): validated. Clustering by running-variable value covered only
  .69-.71 (Lee-Card clustering is unreliable; Kolesar and Rothe 2018) and is not offered;
- continuous running variables: the robust interval covered .893-.915 with linear or quadratic regression functions
  but .78-.80 under the strongly curved Lee design with n up to 10,000 (conventional intervals .30-.49 there):
  exploratory;
- the density (manipulation) test rejected .097-.114 at .10 under no manipulation: exploratory.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import rdd_core as rc

AUDIT = "docs/audits/rdd_validation.md"
REPAIRS_AUDIT = "docs/audits/repairs105_validation.md"
REPAIRS_AUDIT_112 = "docs/audits/repairs112_validation.md"
VALIDATED = {"discrete_replicate": True, "continuous": True, "density": True}
DENSITY_MIN_N = 1000


def regression_discontinuity(frame: pd.DataFrame, outcome: str, running: str, cutoff: float,
                             treatment: Optional[str] = None, weight: Optional[str] = None,
                             replicate_prefix: Optional[str] = None, bandwidth: Optional[float] = None,
                             covariates: Sequence[str] = (), placebo_cutoffs: Sequence[float] = (),
                             level: float = .90) -> Dict[str, Any]:
    cols = [outcome, running]+([treatment] if treatment else [])+([weight] if weight else [])+list(covariates)
    d = frame.dropna(subset=cols).reset_index(drop=True)
    x = d[running].astype(float).to_numpy(); y = d[outcome].astype(float).to_numpy()
    t = d[treatment].astype(float).to_numpy() if treatment else None
    w = d[weight].astype(float).to_numpy() if weight else None
    R = None
    if replicate_prefix:
        rcols = [f"{replicate_prefix}{i}" for i in range(1, 81)]
        miss = [c for c in rcols if c not in d]
        if miss:
            raise ValueError(f"replicate weights {miss[:3]}... not in the frame")
        R = d[rcols].astype(float).to_numpy()
    discrete = len(np.unique(x)) <= 100
    if bandwidth is not None:
        h = float(bandwidth)
    elif discrete:
        h = max(rc.ik_bandwidth(x, y, cutoff), 4.0)   # 3+ support points per side for the local quadratic
    else:
        h = float(rc.ik_bandwidth(x, y, cutoff) * (len(x) ** (-1.0 / 20.0)))   # Round 105: CCT CER bandwidth
    res = rc.rdd(x, y, cutoff, h=h, d=t, weights=w, replicate_weights=R, level=level)
    if discrete:
        validated = bool(R is not None and VALIDATED["discrete_replicate"])
    else:
        validated = bool(bandwidth is None and VALIDATED["continuous"])
    notes = []
    if discrete and R is None:
        notes.append("Discrete running variable without replicate weights: HC intervals are exploratory (validation "
                     "used survey replicates).")
    if not discrete:
        if validated:
            notes.append(f"Continuous running variable uses CCT CER-optimal bandwidth h_ik * n^(-1/20) "
                         f"(validated in Round 105, {REPAIRS_AUDIT}).")
        else:
            notes.append("Custom bandwidth on a continuous running variable is exploratory (validation used automatic "
                         f"CER bandwidth; {REPAIRS_AUDIT}).")
    out = dict(design=res["design"], estimate=res["robust_estimate"], se=res["robust_se"], lower=res["robust_lower"],
               upper=res["robust_upper"], conventional=dict(estimate=res["estimate"], lower=res["lower"], upper=res["upper"]),
               bandwidth=res["bandwidth"], n_within=res["n_within"], variance=res["variance"], validated=validated)
    dt = rc.density_test(x if not discrete else x+np.random.default_rng(0).uniform(-.5, .5, len(x)), cutoff)
    dens_ok = bool(not discrete and len(x) >= DENSITY_MIN_N and VALIDATED["density"])
    out["density_test"] = dict(
        dt, validated=dens_ok,
        note=(f"Manipulation (density) test: validated for continuous running variables with n >= {DENSITY_MIN_N} "
              f"(Round 112, {REPAIRS_AUDIT_112})." if dens_ok else
              "Manipulation (density) test: exploratory (validated for continuous running variables with "
              f"n >= {DENSITY_MIN_N}; " + ("ages were jittered within each year for the test)." if discrete else f"n = {len(x)}).")),
    )
    out["covariate_jumps"] = {c: _jump(x, d[c].astype(float).to_numpy(), cutoff, h, w, R, level) for c in covariates}
    out["placebo"] = {str(c0): _jump(x, y, c0, h, w, R, level) for c0 in placebo_cutoffs}
    notes.append("The estimate is the robust bias-corrected (local quadratic) jump; the conventional local linear "
                 "estimate is in 'conventional'. A causal reading needs no other change at the cutoff (check "
                 "covariate_jumps and placebo cutoffs).")
    out.update(notes=notes, audit=AUDIT, n=len(d), cutoff=cutoff)
    return out


def _jump(x, y, c, h, w, R, level):
    try:
        r = rc.rdd(x, y, c, h=h, weights=w, replicate_weights=R, level=level)
        return dict(estimate=r["robust_estimate"], lower=r["robust_lower"], upper=r["robust_upper"])
    except (ValueError, np.linalg.LinAlgError) as exc:
        return dict(error=str(exc))

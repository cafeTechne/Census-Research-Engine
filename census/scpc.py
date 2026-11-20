# SPDX-License-Identifier: AGPL-3.0-or-later
"""SCPC spatial-correlation-robust intervals for naive area-level slopes (Round 58).

Validated (``docs/audits/spatial_outside_validation.md``, criterion e8c6c8c; Round 30 cells on MI/NY and OH/PA,
spatially correlated covariate and error fields, observed-estimate target):
- OLS with rho_bar .05 (.861-.930) and .10 (.897-.947);
- Poisson with rho_bar .10 (.863-.934); .05 failed (.830);
- binomial failed at both (.793 and .846): exploratory.
SCPC does not assume independent clusters, so it holds on adjacent states (OH/PA), where IM-8 under-covered.
The target is the slope on the ACS estimates as observed (attenuated by covariate sampling error, as IM-8 C1).
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import patsy

from . import scpc_core as core

AUDIT = "docs/audits/spatial_outside_validation.md"
VALIDATED_RHO = {"ols": (.05, .10), "poisson": (.10,), "binomial": ()}
DEFAULT_RHO = {"ols": .05, "poisson": .10, "binomial": .10}
_SETUPS: Dict[Any, Dict[str, Any]] = {}


def fit_scpc(formula: str, frame: pd.DataFrame, model: str = "ols", trials: Optional[str] = None,
             exposure: Optional[str] = None, coords: Optional[pd.DataFrame] = None, rho_bar: Optional[float] = None,
             level: float = .90) -> Dict[str, Any]:
    """Naive slopes with SCPC intervals. ``coords``: GEOID, lon, lat (else Census representative points)."""
    if model not in VALIDATED_RHO:
        raise ValueError("model must be ols, poisson or binomial")
    if model == "binomial" and not trials:
        raise ValueError("binomial needs trials (the outcome is a proportion)")
    if model == "poisson" and not exposure:
        raise ValueError("poisson needs exposure")
    rho = DEFAULT_RHO[model] if rho_bar is None else float(rho_bar)
    if not 0 < rho < 1:
        raise ValueError("rho_bar must be in (0, 1)")
    extra = [v for v in (trials, exposure) if v]
    data = frame.dropna(subset=[c for c in extra if c in frame.columns]).copy()
    y_df, X_df = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    data = data.loc[X_df.index]
    if "GEOID" not in data:
        raise ValueError("SCPC needs GEOIDs for locations")
    if coords is None:
        from .small_spatial import frame_coordinates
        coords = frame_coordinates(data)
    pts = coords.assign(GEOID=coords.GEOID.astype(str)).drop_duplicates("GEOID").set_index("GEOID")
    ids = data.GEOID.astype(str)
    if not ids.isin(pts.index).all():
        raise ValueError("missing coordinates for analysed GEOIDs")
    lon, lat = pts.loc[ids, "lon"].to_numpy(float), pts.loc[ids, "lat"].to_numpy(float)
    key = (tuple(ids), rho, level)
    if key not in _SETUPS:
        _SETUPS[key] = core.setup(core.haversine(lon, lat), rho, alpha=1-level)
    S = _SETUPS[key]
    X, y = X_df.to_numpy(float), y_df.to_numpy(float)[:, 0]
    kind = "linear" if model == "ols" else model
    t = data[trials].to_numpy(float) if trials else None
    ex = data[exposure].to_numpy(float) if exposure else None
    rows = []
    for j, term in enumerate(X_df.columns):
        if term == "Intercept":
            continue
        theta, e = core.influence(X, y, kind, j, trials=t, exposure=ex)
        rows.append(dict(term=term, **core.interval(theta, e, S)))
    validated = rho in VALIDATED_RHO[model] and abs(level-.90) < 1e-12
    notes = [f"SCPC (Mueller and Watson 2022): q = {S['q']} spatial principal components, critical value "
             f"{S['cv']:.3f}, benchmark average correlation {rho} (range {1/S['c0']:.0f} km); worst case over weaker "
             "correlation. Target: the slope on the ACS estimates as observed (not corrected for covariate sampling "
             f"error; use the corrected-slope estimators for that). {AUDIT}."]
    if not validated:
        notes.append(f"EXPLORATORY: SCPC is validated for OLS (rho_bar .05, .10) and Poisson (.10) at the 90% level; "
                     f"{model} with rho_bar {rho} is not (binomial failed).")
    return dict(model=model, spatial="scpc", rho_bar=rho, table=pd.DataFrame(rows), n=len(y), validated=validated,
                notes=notes, audit=AUDIT)

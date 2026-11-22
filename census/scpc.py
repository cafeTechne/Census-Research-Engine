# SPDX-License-Identifier: AGPL-3.0-or-later
"""SCPC spatial-correlation-robust intervals for naive area-level slopes (Round 58).

Validated (``docs/audits/spatial_outside_validation.md``, criterion e8c6c8c; Round 30 cells on MI/NY and OH/PA,
spatially correlated covariate and error fields, observed-estimate target):
- OLS with rho_bar .05 (.861-.930) and .10 (.897-.947);
- Poisson with rho_bar .10 (.863-.934); .05 failed (.830);
- binomial failed at both (.793 and .846); Round 62 (docs/audits/leftover_failures_validation.md, criterion
  8f14e39): binomial passes with the stronger benchmarks rho_bar .15 (.886-.954) and .20 (.909-.966).
Round 71 (``docs/audits/tract_spatial_validation.md``, criterion f947f64; NC 2018 and MI 2020 tracts, ranges 0-100 km):
tract OLS slopes pass with rho_bar .20 (.885-.972) and .30 (.932-.988); .20 gives the shorter intervals and is the tract
default. Round 67's rho_bar .05/.10 under-covered on tracts. Poisson and binomial tract slopes are not validated.
SCPC does not assume independent clusters, so it holds on adjacent states (OH/PA), where IM-8 under-covered.
The target is the slope on the ACS estimates as observed (attenuated by covariate sampling error, as IM-8 C1).
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import patsy

from . import scpc_core as core

AUDIT = "docs/audits/spatial_outside_validation.md"
TRACT_AUDIT = "docs/audits/tract_spatial_validation.md"   # Round 71: tract OLS passes at rho_bar .20/.30
TRACT_AUDIT_R67 = "docs/audits/r67_nc_tract_validation.md"   # Round 67: rho_bar .05/.10 failed on tracts at 100 km
VALIDATED_RHO = {"ols": (.05, .10), "poisson": (.10,), "binomial": (.15, .20)}
DEFAULT_RHO = {"ols": .05, "poisson": .10, "binomial": .15}
TRACT_VALIDATED_RHO = {"ols": (.20, .30)}
TRACT_DEFAULT_RHO = {"ols": .20}


def validated_rho(model: str, tract: bool) -> tuple:
    """Validated benchmarks for this model and geography (tract GEOIDs: Round 71; counties: Rounds 58/62)."""
    return TRACT_VALIDATED_RHO.get(model, ()) if tract else VALIDATED_RHO.get(model, ())


def default_rho(model: str, tract: bool) -> float:
    return TRACT_DEFAULT_RHO.get(model, DEFAULT_RHO[model]) if tract else DEFAULT_RHO[model]


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
    if rho_bar is not None and not 0 < float(rho_bar) < 1:
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
    tract_level = bool((ids.str.len() >= 11).all())
    rho = default_rho(model, tract_level) if rho_bar is None else float(rho_bar)
    if not 0 < rho < 1:
        raise ValueError("rho_bar must be in (0, 1)")
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
        rows.append(dict(term=term, **core.interval(theta, e, S), p_value=core.p_value(theta, e, S)))
    validated = rho in validated_rho(model, tract_level) and abs(level-.90) < 1e-12
    notes = [f"SCPC (Mueller and Watson 2022): q = {S['q']} spatial principal components, critical value "
             f"{S['cv']:.3f}, benchmark average correlation {rho} (range {1/S['c0']:.0f} km); worst case over weaker "
             "correlation. Target: the slope on the ACS estimates as observed (not corrected for covariate sampling "
             f"error; use the corrected-slope estimators for that). {AUDIT}."]
    if tract_level and validated:
        notes.append(f"Tract geometry: validated for OLS slopes with rho_bar .20/.30 (Round 71, {TRACT_AUDIT}; NC and MI "
                     "tracts, fields correlated up to 100 km, coverage .885-.988).")
    elif tract_level:
        notes.append(f"EXPLORATORY: on tract geometry SCPC is validated for OLS slopes with rho_bar .20 or .30 only (Round "
                     f"71, {TRACT_AUDIT}); {model} with rho_bar {rho} is not. Round 67 ({TRACT_AUDIT_R67}): rho_bar .05/.10 "
                     "under-covered (.75/.81 at 100 km).")
    elif not validated:
        notes.append(f"EXPLORATORY: SCPC is validated for OLS (rho_bar .05, .10), Poisson (.10) and binomial (.15, .20) "
                     f"at the 90% level; {model} with rho_bar {rho} is not.")
    return dict(model=model, spatial="scpc", rho_bar=rho, table=pd.DataFrame(rows), n=len(y), validated=validated,
                notes=notes, audit=AUDIT)

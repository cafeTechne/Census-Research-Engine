# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 210: Shared geography boundary, spatial-weights, and replicate helpers (extracted from census/workflows_geo.py)."""
from __future__ import annotations

from typing import Any, List, Optional

import pandas as pd

_LEVELS = ("state", "county", "tract", "block group", "place", "zcta")
_MAP_KINDS = ("estimate", "uncertainty", "significance")
_GEO_ERRORS = (FileNotFoundError, OSError, KeyError, ValueError, TypeError, RuntimeError)


def _release_replicates(reps: Optional[pd.DataFrame], year: int) -> Optional[pd.DataFrame]:
    """Select the requested release from a replicate frame with a Year column
    (PLAN_ROUND_11 C3): never let row order pick among releases."""
    if reps is None or "Year" not in reps.columns:
        return reps
    sel = reps[pd.to_numeric(reps["Year"], errors="coerce") == int(year)]
    if not len(sel):
        raise ValueError(f"replicates have no rows for release {int(year)}")
    return sel


def _per_state(level: str, boundary_year: int) -> bool:
    """Whether boundaries for ``level`` must come from per-state files: tract and
    block group always (smaller downloads), other per-state levels (place,
    county subdivision) only before national cb files exist (2019)."""
    from census.boundaries import FIRST_NATIONAL_SUBSTATE_CB_YEAR, LEVELS, normalize_level

    lvl = normalize_level(level)
    if not LEVELS[lvl]["per_state"]:
        return False
    return lvl in ("tract", "block group") or int(boundary_year) < FIRST_NATIONAL_SUBSTATE_CB_YEAR


def _fetch_boundaries(level: str, acs_year: int, states=None):
    """Boundaries matching an ACS release: the boundary year comes from
    ``boundary_vintage`` (e.g. ZCTA for ACS 2023 -> the 2020 file) and per-state
    files are stitched together when the level has no national file that year."""
    from census.boundaries import boundary_vintage, get_boundaries

    b_year = boundary_vintage(acs_year, level)
    if not _per_state(level, b_year):
        return get_boundaries(level, b_year)
    states = sorted(set(states or ()))
    if not states:
        raise ValueError(f"{level} boundaries for {b_year} are per state; pass state")
    parts = [get_boundaries(level, b_year, state=s) for s in states]
    if len(parts) == 1:
        return parts[0]
    bounds = parts[0].__class__(pd.concat(parts, ignore_index=True), geometry="geometry", crs=parts[0].crs)
    # concat drops attrs; keep the vintage and source for captions and provenance
    bounds.attrs.update({k: v for k, v in parts[0].attrs.items() if k not in ("state", "source_url", "sha256")})
    bounds.attrs["states"] = states
    return bounds


def _with_boundaries(df: pd.DataFrame, level: str, year: int):
    """Attach Census cartographic boundaries matching the ACS release."""
    from census.boundaries import join_boundaries
    from census import workflows_geo as _wg

    if level not in _LEVELS:
        raise ValueError(f"level must be one of {_LEVELS}")
    states = {g[:2] for g in df["GEOID"].astype(str)}
    bounds = _wg._fetch_boundaries(level, year, states)
    return join_boundaries(df, level, acs_year=year, boundaries=bounds, how="inner", on_unmatched="warn")


def _weights_for(gdf, kind: str):
    """Spatial weights; knn / distance weights are built in an equal-area CRS so
    distances are in meters, not degrees."""
    from census import spatial

    if kind in ("knn", "distance") and gdf.crs is not None:
        from census.boundaries import equal_area_crs

        gdf = gdf.to_crs(equal_area_crs(gdf))
    return gdf, spatial.spatial_weights(gdf, kind=kind)


def _paths(fig: Any) -> List[str]:
    paths = fig.paths.values() if isinstance(fig.paths, dict) else fig.paths
    return [str(p) for p in paths]

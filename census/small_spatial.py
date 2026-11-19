# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 48 engine flags and helpers (docs/audits/small_spatial_validation.md, criterion 3fb07d3).

Passed: effective-sample-size (Clifford-Richardson-Hemon, Moran's I in 13 distance classes) intervals for
Spearman (.875-.917), Kendall (.862-.905) and Pearson with replicates (.864-.967) and for Feldt's alpha
(.912-.926) under spatial dependence; Paule-Mandel + Hartung-Knapp with the variance factor truncated at 1
for 5-10 estimates (.874-.918); Bland-Altman limits with moment-based SEs (.884-.936); the AR(1)
bootstrap-t for interrupted series at 30 points (.883-.896). Failed: REML AR(1) at 15-30 points
(.79-.88), bootstrap-t at 15-20 points (.846-.894; .846 and .857 in the phi = .6 cells), IM-8 versions (Spearman, Pearson,
alpha).
"""
from typing import Optional

import numpy as np
import pandas as pd

from . import small_spatial_core as sc

AUDIT = "docs/audits/small_spatial_validation.md"
ITS_BOOTSTRAP_MIN_N = 30
ITS_REML_VALIDATED = False
NEFF_CORRELATION_VALIDATED = {"spearman": True, "kendall": True, "pearson": True, "partial": False}
NEFF_ALPHA_VALIDATED = True
HKSJ_TRUNCATED_MAX_K = 10
LIMITS_ROBUST_VALIDATED = True


def frame_coordinates(frame: pd.DataFrame, acs_year: Optional[int] = None) -> pd.DataFrame:
    """Representative points (GEOID, lon, lat) for the county or tract GEOIDs of ``frame``."""
    from .spatial_hac import unit_coordinates
    geoids = frame["GEOID"].astype(str)
    lengths = set(geoids.str.len())
    level = "county" if lengths == {5} else "tract" if lengths == {11} else None
    if level is None:
        raise ValueError("spatial correction needs county (5-digit) or tract (11-digit) GEOIDs")
    year = acs_year or (int(frame["Year"].max()) if "Year" in frame else 2022)
    return unit_coordinates(geoids, level, year)[0]


def distance_classes(frame: pd.DataFrame, coords: pd.DataFrame) -> np.ndarray:
    """Round 48 distance-class matrix for the rows of ``frame`` (GEOID column)."""
    from .spatial_hac import coordinate_distances
    D = coordinate_distances(frame, coords)
    if not np.isfinite(D).all():
        raise ValueError("coordinates missing for some GEOIDs")
    return sc.class_index(D)

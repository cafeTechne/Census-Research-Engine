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
# Round 55 (criterion dd6d6b7; docs/audits/short_series_reference_validation.md): the bootstrap-t with the
# bootstrap series at a bias-corrected AR coefficient covered both changes .867-.889 at 20 and 25 points
# (.857 at 15 points with phi .6); the EWC HAR t test failed everywhere (.61-.72). The plain bootstrap-t (a
# comparison arm there) covered .872+ at 25 points; its validated minimum stays 30.
SHORT_SERIES_AUDIT = "docs/audits/short_series_reference_validation.md"
ITS_BOOTSTRAP_BC_MIN_N = 20
ITS_EWC_VALIDATED = False
# Round 63 (criterion ac2f34c; docs/audits/small_many_validation.md): the conservative bootstrap-t (critical values
# at least the t(n - p - 1) quantile) covered both changes at 17 and 19 points (.865-.896) and, as it is never
# narrower than the Round 55 bias-corrected bootstrap-t, at 20+ points; at 15 points every method failed (.849-.855).
# The bootstrap-bias-corrected variant passed only from 19 points.
SMALL_SERIES_AUDIT = "docs/audits/small_many_validation.md"
ITS_BOOTSTRAP_CONS_MIN_N = 17
ITS_BOOTSTRAP_BB_MIN_N = 19
# Round 59 (criterion 669a506; docs/audits/spatial_correlation_validation.md): partial correlations with the
# effective n of the residual series passed (.869-.971, MI/NY and OH/PA); the Round 48 correlation and alpha
# intervals replicated on OH/PA (correlations .880-.965, alpha .901-.933).
NEFF_CORRELATION_VALIDATED = {"spearman": True, "kendall": True, "pearson": True, "partial": True}
OHPA_REPLICATED = {"spearman": True, "kendall": True, "pearson": True, "partial": True, "alpha": True}
SPATIAL_CORRELATION_AUDIT = "docs/audits/spatial_correlation_validation.md"
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
    if acs_year or "Year" in frame:
        return unit_coordinates(geoids, level, acs_year or int(frame["Year"].max()))[0]
    if level == "county":
        return unit_coordinates(geoids, level, 2022)[0]
    # Round 75: no release given. Tract GEOIDs changed in 2020, so try 2020 tracts, then 2010 tracts (2019).
    errors = []
    for year in (2022, 2019):
        try:
            coords = unit_coordinates(geoids, level, year)[0]
            coords.attrs["tract_vintage_note"] = (f"No Year column: tract points from the {year} boundary vintage "
                                                  f"({'2020' if year >= 2020 else '2010'} tracts), where every GEOID was found.")
            return coords
        except ValueError as exc:
            errors.append(f"{year}: {exc}")
    raise ValueError("tract GEOIDs were not all found in the 2020-tract (2022) or 2010-tract (2019) boundaries "
                     f"({'; '.join(errors)}). Add a Year column with the ACS release so its vintage is used.")


def distance_classes(frame: pd.DataFrame, coords: pd.DataFrame) -> np.ndarray:
    """Round 48 distance-class matrix for the rows of ``frame`` (GEOID column)."""
    from .spatial_hac import coordinate_distances
    D = coordinate_distances(frame, coords)
    if not np.isfinite(D).all():
        raise ValueError("coordinates missing for some GEOIDs")
    return sc.class_index(D)

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Kulldorff Poisson spatial scan for county counts (Round 81; backlog N58).

Validation: ``docs/audits/scan_validation.md`` (criterion ``scan_validation_criterion.md``); computation is the frozen
core :mod:`census.scan_core`. Cluster detection is exploratory unless the maximum window and alpha were declared
before looking at the data (``prespecified=True``); the p-value is validated for the 50% maximum window only.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import scan_core as sc

AUDIT = "docs/audits/scan_validation.md"
VALIDATED_MAX_SHARE = .5
K1_VALIDATED = True  # docs/audits/scan_validation.json: size .099-.116 at alpha .10 in all six null cells
NOISY_DENOMINATOR_NOTE = ("Denominators with sampling error inflate false clusters: with 5% ACS-like error the "
                          "rejection rate at .10 was .15-.17 (20 expected per county) and .47-.53 (100) in validation. "
                          "Use exact counts (vital records, decennial counts) or treat the result as exploratory.")
SEED = 20282181


def spatial_scan(frame: pd.DataFrame, cases: str, population: Optional[str] = None, expected: Optional[str] = None,
                 year: Optional[int] = None, max_share: float = .5, replicates: int = 999, secondary: int = 3,
                 exclude: Optional[Sequence[str]] = None, exclude_rule: Optional[str] = None,
                 prespecified: bool = False, seed: int = SEED) -> Dict[str, Any]:
    """Primary and secondary high-rate clusters of county counts.

    ``cases``: observed counts (non-negative integers, fully observed). ``expected``: expected counts (e.g. from
    indirect standardisation), or ``population`` (expected proportional to population). Missing counts (WONDER
    suppression) are refused unless those counties are listed in ``exclude`` with an ``exclude_rule`` stating why;
    no count is imputed. ``max_share``: largest window as a share of the expected total (validated: .5).
    """
    if (population is None) == (expected is None):
        raise ValueError("give exactly one of population or expected")
    f = frame.copy(); f["GEOID"] = f["GEOID"].astype(str)
    if not (f["GEOID"].str.len() == 5).all():
        raise ValueError("the scan works on county GEOIDs (five digits)")
    notes = []
    if exclude:
        if not exclude_rule:
            raise ValueError("excluded counties need a stated exclude_rule")
        drop = f["GEOID"].isin([str(g) for g in exclude])
        notes.append(f"{int(drop.sum())} counties excluded ({exclude_rule}); results describe the remaining counties.")
        f = f[~drop]
    base = expected or population
    if f[cases].isna().any():
        raise ValueError("some counts are missing (suppressed): exclude those counties with a stated exclude_rule; "
                         "counts are never imputed")
    c = f[cases].to_numpy(float)
    if (c < 0).any() or not np.allclose(c, np.round(c)):
        raise ValueError("cases must be non-negative integer counts")
    mu = f[base].to_numpy(float)
    if (mu <= 0).any() or not np.isfinite(mu).all():
        raise ValueError(f"{base} must be positive")
    noisy = False
    if f"{base}_se" in f.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            cv = float(np.nanmedian(f[f"{base}_se"].to_numpy(float)/mu))
        noisy = cv > .01
        if noisy:
            notes.append(f"Median denominator CV {cv:.3f}. "+NOISY_DENOMINATOR_NOTE)
    coords = _coords(f, year)
    f = f.merge(coords, on="GEOID", how="left")
    if f[["lon", "lat"]].isna().any().any():
        raise ValueError("representative points missing for some counties")
    res = sc.scan(c, mu, f.lon.to_numpy(), f.lat.to_numpy(), max_share=max_share, R=replicates,
                  rng=np.random.default_rng(seed), secondary=secondary)
    geo = f["GEOID"].tolist()

    def rows(cl):
        return dict(counties=[geo[i] for i in cl["members"]], center=geo[cl["center"]], cases=cl["cases"],
                    expected=cl["expected"], relative_risk=cl["rr"], llr=cl["llr"], p_value=cl["p_mc"],
                    p_gumbel=cl["p_gumbel"])
    validated = bool(K1_VALIDATED) and abs(max_share-VALIDATED_MAX_SHARE) < 1e-12 and replicates >= 999 and not noisy
    if not validated:
        notes.append("The p-value is outside the validated setting (50% maximum window, 999 replicates, exact denominators"
                     + ("" if K1_VALIDATED else "; K1 did not pass validation") + ").")
    if not prespecified:
        notes.append("Exploratory: the window and alpha were not declared in advance; report the cluster as "
                     "descriptive.")
    notes.append("Expected counts were scaled to the observed total (conditional on the total).")
    return dict(primary=rows(res["primary"]) if res["primary"] else None,
                secondary=[rows(x) for x in res["secondary"]], windows=res["windows"], counties=len(geo),
                max_share=max_share, replicates=replicates, validated_p=validated, confirmatory=validated and prespecified,
                notes=notes, audit=AUDIT)


def _coords(f, year):
    from .small_spatial import frame_coordinates
    g = pd.DataFrame({"GEOID": f["GEOID"].unique()})
    if year is not None:
        g["Year"] = int(year)
    return frame_coordinates(g)[["GEOID", "lon", "lat"]]

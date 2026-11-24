# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 93: geographically weighted regression, geodemographic classification, regionalization and an entropy
diversity index with ACS uncertainty (backlog N69; Walker, *Analyzing US Census Data*, chapter 8).

Validation: ``docs/audits/spatial_models_validation.md`` (criterion tag ``criterion-r93``), Wayne County tracts:
- GWR **failed**: local 90% intervals covered .866-.894 with a constant slope but .707-.714 with slopes varying over
  space (kernel smoothing bias), and the permutation non-stationarity test rejected .116-.166 at .10: exploratory;
- the entropy diversity index **failed** narrowly (.847 with 50 effective respondents per tract; .883 with 200); the
  bias correction changed nothing: exploratory;
- classification and regionalization had no pass rule. Stability is informative: areas with stability below .8 were
  misclassified 39-50% of the time against 3-16% for stable areas; SKATER recovered planted regions (ARI .65-.72),
  k-means planted aspatial types less well (ARI .39-.50).
"""
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from . import spatial_models_core as sm

AUDIT = "docs/audits/spatial_models_validation.md"
VALIDATED = {"gwr": False, "diversity": False, "diversity_bc": False}   # spatial_models_validation.md
MAX_GWR_AREAS = 3000
WALKER_NOTE = ("GWR explores whether a relationship varies over space; local coefficients suffer from local "
               "collinearity and edge effects, so report them beside a global model (Walker 2023, section 8.4.3).")


def _coords_km(gdf) -> np.ndarray:
    pts = gdf.to_crs(5070).representative_point()
    return np.column_stack([pts.x.to_numpy(), pts.y.to_numpy()])/1000


def _se(frame: pd.DataFrame, col: str) -> np.ndarray:
    if f"{col}_se" in frame:
        return pd.to_numeric(frame[f"{col}_se"], errors="coerce").to_numpy(float)
    if f"{col}_moe" in frame:
        return pd.to_numeric(frame[f"{col}_moe"], errors="coerce").to_numpy(float)/1.645
    raise ValueError(f"{col!r} needs a {col}_se or {col}_moe column (sampling error drives the stability measure)")


def gwr_model(gdf, outcome: str, predictors: Sequence[str], permutations: int = 99, seed: int = 20282931
              ) -> Dict[str, Any]:
    """GWR of ``outcome`` on ``predictors`` over the areas of ``gdf`` (a GeoDataFrame with the columns)."""
    cols = [outcome, *predictors]
    d = gdf.dropna(subset=cols).reset_index(drop=True)
    if len(d) > MAX_GWR_AREAS:
        raise ValueError(f"{len(d)} areas; GWR is limited to {MAX_GWR_AREAS} (use a county or metro subset)")
    if len(d) < 50:
        raise ValueError("GWR needs at least 50 areas")
    xy = _coords_km(d)
    D = np.hypot(xy[:, :1]-xy[:, 0], xy[:, 1:]-xy[:, 1])
    y = d[outcome].astype(float).to_numpy(); X = d[list(predictors)].astype(float).to_numpy()
    r = sm.gwr(y, X, D, perms=permutations, rng=np.random.default_rng(seed))
    names = ["Intercept", *predictors]
    local = pd.DataFrame({"GEOID": d.GEOID.astype(str)})
    for j, nm in enumerate(names):
        local[nm] = r["coef"][:, j]; local[f"{nm}_se"] = r["se"][:, j]
        local[f"{nm}_lower"] = r["lower"][:, j]; local[f"{nm}_upper"] = r["upper"][:, j]
    validated = bool(VALIDATED["gwr"])
    notes = [WALKER_NOTE, "Local intervals are 90% heteroskedasticity-robust (they carry each area's sampling error); "
             "they do not account for the bandwidth choice."]
    if not validated:
        notes.append(f"Exploratory: GWR local intervals failed validation ({AUDIT}).")
    summary = {nm: dict(min=float(local[nm].min()), median=float(local[nm].median()), max=float(local[nm].max()))
               for nm in names}
    return dict(bandwidth_km=r["bandwidth_km"], effective_parameters=r["effective_params"], n=len(d),
                nonstationarity=dict(predictor=names[1], statistic=r["nonstationarity_stat"],
                                     p_value=r["nonstationarity_p"], permutations=permutations),
                coefficients=summary, local=local, validated=validated, notes=notes, audit=AUDIT)


def classify(frame: pd.DataFrame, features: Sequence[str], k: int, method: str = "kmeans",
             edges: Optional[Sequence[Sequence[int]]] = None, replicates: int = 20, min_size: int = 5,
             seed: int = 20282932) -> Dict[str, Any]:
    """Geodemographic classification (``kmeans``) or contiguous regions (``skater``, needs ``edges``) with per-area
    stability under sampling error (each feature needs ``<feature>_se`` or ``_moe``)."""
    if method not in ("kmeans", "skater"):
        raise ValueError("method must be 'kmeans' or 'skater'")
    if not 2 <= int(k) <= 12:
        raise ValueError("k must be between 2 and 12 (set it before looking at the result)")
    if len(features) < 2:
        raise ValueError("give at least two features")
    F = frame[list(features)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    S = np.column_stack([_se(frame, c) for c in features])
    if not (np.isfinite(F).all() and np.isfinite(S).all()):
        raise ValueError("features and their SEs must be complete (drop areas with missing values first)")
    rng = np.random.default_rng(seed)
    if method == "skater":
        if not edges:
            raise ValueError("skater needs the neighbour edges")
        fit = lambda G: sm.skater(G, edges, k, min_size)  # noqa: E731
    else:
        fit = lambda G: sm.kmeans(G, k, rng)  # noqa: E731
    main = fit(F)
    reps = [fit(F+S*rng.standard_normal(F.shape)) for _ in range(int(replicates))]
    stab = sm.stability(main, reps, k)
    prof = pd.DataFrame(F, columns=list(features)).assign(group=main).groupby("group").mean()
    out = pd.DataFrame({"GEOID": frame.GEOID.astype(str).to_numpy(), "group": main+1, "stability": stab})
    return dict(method=method, k=int(k), assignments=out, profiles=prof.reset_index().assign(group=lambda x: x.group+1),
                mean_stability=float(stab.mean()), share_unstable=float((stab < .8).mean()), validated=False,
                notes=["Descriptive: groups are labels for exploration, not a tested result. Stability is the share of "
                       f"{replicates} sampling-error replicates (features + N(0, SE^2)) giving the same group; in "
                       "validation, areas with stability below .8 were misclassified far more often.",
                       "k was fixed in advance; report how it was chosen."], audit=AUDIT)


DIVERSITY_REPAIRS_AUDIT = "docs/audits/repairs108_validation.md"
DIVERSITY_SDR_BC_MIN_N = 150
DIVERSITY_SDR_BC_VALIDATED = True


def diversity_index(shares: pd.DataFrame, replicate_shares: Sequence[pd.DataFrame], bias_correct: bool = True,
                    method: str = "default", sample_sizes: Optional[Sequence[float]] = None) -> pd.DataFrame:
    """Entropy diversity per area from group shares (rows areas, columns groups; each row sums to 1) and replicate
    shares (same shape, SDR replicates). Returns estimate, SE and 90% limits; maximum is ln(number of groups).
    Pass ``method='sdr_bc'`` (with ``sample_sizes``) for Round 108's validated exact SDR replicate bias correction
    (gated at ``n >= 150`` respondents per area; ``docs/audits/repairs108_validation.md``)."""
    P = shares.to_numpy(float)
    R = np.stack([r.loc[shares.index, shares.columns].to_numpy(float) for r in replicate_shares])
    if method == "sdr_bc":
        from . import repairs108_core as r108
        out = r108.diversity_sdr_bc(P, R)
        df = pd.DataFrame({"entropy": out["estimate"], "se": out["se"], "lower": out["lower"], "upper": out["upper"],
                           "max": np.log(P.shape[1])}, index=shares.index)
        if sample_sizes is not None:
            ns = np.asarray(sample_sizes, float)
            df["validated"] = bool(DIVERSITY_SDR_BC_VALIDATED) & (ns >= DIVERSITY_SDR_BC_MIN_N)
        else:
            df["validated"] = False
        return df
    out = sm.diversity(P, R, bias_correct)
    return pd.DataFrame({"entropy": out["estimate"], "se": out["se"], "lower": out["lower"], "upper": out["upper"],
                         "max": np.log(P.shape[1])}, index=shares.index)

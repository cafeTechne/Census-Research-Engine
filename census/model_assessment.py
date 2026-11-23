# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 97: out-of-sample model assessment with spatial block cross-validation, and MAUP sensitivity (backlog N74;
Moraga 2023, chapters 11 and 16).

Validation (``docs/audits/model_assessment_validation.md``; criterion tag ``criterion-r97``), Wayne County tracts with
predictions for the adjacent Oakland and Macomb tracts: with spatially correlated residuals (20-50 km), 5-block
spatial CV under-estimated the new-region RMSE by 19-23% and over-stated coverage (.78-.83 vs .66-.73); random CV
under-estimated by 33-43% (coverage .90). Without spatial correlation both were exact. Block CV is therefore
exploratory: less optimistic than random folds, but not a calibrated estimate of error in a new region.
MAUP (reported): zone-level slopes over random zonings of about 10 tracts ranged from -0.21 to 1.45 times the
tract-level slope (5th-95th percentile) when residuals were spatially correlated.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import model_assessment_core as mc

AUDIT = "docs/audits/model_assessment_validation.md"
VALIDATED = {"spatial_cv": False}   # model_assessment_validation.md: block CV under-estimated new-region RMSE by 19-23%


def _ols_fit_predict(y_tr, X_tr, xy_tr, X_te, xy_te):
    A = np.column_stack([np.ones(len(y_tr)), X_tr]); B = np.column_stack([np.ones(len(X_te)), X_te])
    beta, *_ = np.linalg.lstsq(A, y_tr, rcond=None)
    r = y_tr-A @ beta
    sd = float(np.sqrt(np.sum(r**2)/max(1, len(r)-A.shape[1])))
    return B @ beta, np.full(len(X_te), sd)


MODELS = {"ols": _ols_fit_predict, "ols_knn": mc.ols_knn_fit_predict}


def _xy_km(gdf):
    pts = gdf.to_crs(5070).representative_point()
    return np.column_stack([pts.x.to_numpy(), pts.y.to_numpy()])/1000


def spatial_cv(gdf, outcome: str, predictors: Sequence[str], model: str = "ols", folds: int = 5,
               seed: int = 20282971) -> Dict[str, Any]:
    """Spatial block (k-means on coordinates) and random cross-validation scores: MAE, RMSE, 90% coverage, CRPS."""
    if model not in MODELS:
        raise ValueError(f"model must be one of {sorted(MODELS)}")
    d = gdf.dropna(subset=[outcome, *predictors]).reset_index(drop=True)
    if len(d) < 10*folds:
        raise ValueError(f"need at least {10*folds} areas for {folds} folds")
    y = d[outcome].astype(float).to_numpy(); X = d[list(predictors)].astype(float).to_numpy(); xy = _xy_km(d)
    rng = np.random.default_rng(seed)
    blocks = mc.block_folds(xy, folds, rng)
    sp = mc.cross_validate(y, X, xy, blocks, MODELS[model])
    rnd = mc.cross_validate(y, X, xy, mc.random_folds(len(y), max(folds, 10), rng), MODELS[model])
    validated = bool(VALIDATED["spatial_cv"]) and folds == 5
    notes = ["Spatial blocks estimate error for areas without nearby training data (a new region); random folds "
             "do not, and are optimistic for models that borrow strength from neighbours (Moraga 2023 ch. 16)."]
    if not validated:
        notes.append("Exploratory: in validation, spatial-block CV still under-estimated error in a new region by about "
                     f"20% when residuals were spatially correlated (random CV by 33-43%) ({AUDIT}). Read it as a "
                     "lower bound on out-of-region error.")
    return dict(model=model, n=len(y), folds=folds, spatial_block=sp, random=rnd, block_labels=blocks.tolist(),
                validated=validated, notes=notes, audit=AUDIT)


def maup_sensitivity(gdf, y: str, x: str, edges, weight: Optional[str] = None, size: int = 10, zonings: int = 100,
                     seed: int = 20282972) -> Dict[str, Any]:
    """The weighted slope of zone means of ``y`` on ``x`` over random contiguous zonings of about ``size`` areas,
    against the area-level slope (Openshaw 1984; Moraga 2023 ch. 11). Descriptive."""
    d = gdf.reset_index(drop=True)
    yy = d[y].astype(float).to_numpy(); xx = d[x].astype(float).to_numpy()
    w = d[weight].astype(float).to_numpy() if weight else np.ones(len(d))
    if not (np.isfinite(yy).all() and np.isfinite(xx).all() and np.isfinite(w).all()):
        raise ValueError("y, x and weight must be complete (drop areas with missing values first)")
    rng = np.random.default_rng(seed)
    base = mc.maup_slope(yy, xx, w, np.arange(len(d)))
    slopes = np.array([mc.maup_slope(yy, xx, w, mc.random_zoning(len(d), edges, size, rng)) for _ in range(int(zonings))])
    return dict(area_slope=base, zone_slopes=dict(mean=float(slopes.mean()), sd=float(slopes.std(ddof=1)),
                p05=float(np.quantile(slopes, .05)), p95=float(np.quantile(slopes, .95))),
                ratio_mean=float(slopes.mean()/base), zonings=int(zonings), size=size, validated=False,
                notes=["Descriptive: how much an area-level slope depends on how areas are grouped (scale and zoning "
                       "effects). A wide range means the result is a property of the units, not only of the places."],
                audit=AUDIT)

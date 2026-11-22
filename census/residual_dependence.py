# SPDX-License-Identifier: AGPL-3.0-or-later
"""Residual spatial-dependence check for area regressions (Round 71, backlog N49).

Moran's I of OLS residuals on a k = 6 nearest-neighbour graph of representative points, with a 999-draw
permutation p-value. Frames above 5,000 rows use a fixed 5,000-row subsample. A diagnostic only: it never changes
an interval. ``mode``: "auto" uses cached boundary files only (no download), "on" may download, "off" skips.
"""
from typing import Any, Dict, Optional
from unittest import mock

import numpy as np
import pandas as pd

K, PERMUTATIONS, MAX_ROWS, ALPHA = 6, 999, 5000, .01


def _knn(lon, lat, k=K):
    from scipy.spatial import cKDTree
    lo, la = np.radians(lon), np.radians(lat)
    xyz = np.column_stack((np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)))
    _, idx = cKDTree(xyz).query(xyz, k=k+1)
    return idx[:, 1:]


def morans_i(resid, nbrs):
    z = resid-resid.mean()
    return float((z*z[nbrs].mean(axis=1)).sum()/(z*z).sum())


def check(frame: pd.DataFrame, formula: str, coords: Optional[pd.DataFrame] = None, mode: str = "auto",
          seed: int = 20281201) -> Optional[Dict[str, Any]]:
    """Return {"moran_i", "p", "n", "level"} or None (not computable / off)."""
    if mode == "off" or "GEOID" not in frame:
        return None
    try:
        import patsy
        y, X = patsy.dmatrices(formula, frame, return_type="dataframe", NA_action="drop")
        d = frame.loc[X.index]
        if len(d) < 30:
            return None
        if coords is None:
            from .small_spatial import frame_coordinates
            if mode == "auto":
                with mock.patch("requests.sessions.Session.request", side_effect=RuntimeError("offline check")):
                    coords = frame_coordinates(d)
            else:
                coords = frame_coordinates(d)
        pts = coords.assign(GEOID=coords.GEOID.astype(str)).drop_duplicates("GEOID").set_index("GEOID")
        ids = d.GEOID.astype(str)
        if not ids.isin(pts.index).all():
            return None
        Xv, yv = X.to_numpy(float), y.to_numpy(float)[:, 0]
        resid = yv-Xv@np.linalg.lstsq(Xv, yv, rcond=None)[0]
        lon, lat = pts.loc[ids, "lon"].to_numpy(float), pts.loc[ids, "lat"].to_numpy(float)
        rng = np.random.default_rng(seed)
        if len(resid) > MAX_ROWS:
            pick = rng.choice(len(resid), MAX_ROWS, replace=False)
            resid, lon, lat = resid[pick], lon[pick], lat[pick]
        nbrs = _knn(lon, lat)
        obs = morans_i(resid, nbrs)
        perm = np.array([morans_i(rng.permutation(resid), nbrs) for _ in range(PERMUTATIONS)])
        p = float((1+np.sum(perm >= obs))/(PERMUTATIONS+1))
        level = "tract" if ids.str.len().eq(11).all() else "county" if ids.str.len().eq(5).all() else "area"
        return dict(moran_i=obs, p=p, n=int(len(resid)), level=level, k=K)
    except Exception:  # noqa: BLE001 - a diagnostic must never break a fit
        return None


def note(result: Optional[Dict[str, Any]], recommended: str) -> Optional[str]:
    if not result or result["p"] >= ALPHA:
        return None
    return (f"Residuals are spatially dependent (Moran's I {result['moran_i']:.3f}, permutation p {result['p']:.3f}, "
            f"{result['level']} k={result['k']} neighbours): the interval assumes independent areas and is too narrow. "
            f"{recommended}")


RECOMMENDED = {
    "county": 'Use fit_model(spatial="scpc") (validated for county OLS, Poisson and binomial slopes).',
    "tract": ('Use fit_model(spatial="scpc") (Round 71: validated for tract OLS slopes, rho_bar .20 '
              'by default; tract Poisson/binomial slopes and the spatial error model are not validated on tracts).'),
    "area": "Use a validated spatial interval for this geography (see the regression recipe).",
}


def recommended(result: Optional[Dict[str, Any]]) -> str:
    return RECOMMENDED.get((result or {}).get("level", "area"), RECOMMENDED["area"])

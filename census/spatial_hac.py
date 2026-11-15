# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bartlett spatial HAC for per-unit estimating equations (Conley 1999)."""

import numpy as np

EARTH_RADIUS_KM = 6371.0088
# Fixed Round 22 validation gate; updated only from the pre-specified simulation.
SPATIAL_HAC_VALIDATED = False


def haversine_matrix(lon, lat) -> np.ndarray:
    """n x n great-circle distances in km (inputs in degrees)."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    if (lon.ndim != 1 or lat.shape != lon.shape or not np.isfinite(lon).all()
            or not np.isfinite(lat).all() or (np.abs(lat) > 90).any() or (np.abs(lon) > 180).any()):
        raise ValueError("coordinates must be finite paired longitude/latitude vectors in degrees")
    lo, la = np.radians(lon), np.radians(lat)
    a = np.sin((la[:, None] - la) / 2) ** 2 + np.cos(la[:, None]) * np.cos(la) * np.sin((lo[:, None] - lo) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def conley_meat(scores: np.ndarray, dist_km: np.ndarray, cutoff_km: float) -> np.ndarray:
    """Bartlett-weighted cross-products of n x k per-observation scores."""
    try:
        invalid = (isinstance(cutoff_km, (bool, np.bool_)) or np.ndim(cutoff_km) != 0
                   or not np.isfinite(cutoff_km) or cutoff_km <= 0)
    except (TypeError, ValueError):
        invalid = True
    if invalid:
        raise ValueError("cutoff_km must be finite and positive")
    scores, dist = np.asarray(scores, float), np.asarray(dist_km, float)
    if (scores.ndim != 2 or dist.shape != (len(scores), len(scores))
            or not np.isfinite(scores).all() or not np.isfinite(dist).all() or (dist < 0).any()
            or not np.allclose(dist, dist.T, atol=1e-10) or not np.allclose(np.diag(dist), 0)):
        raise ValueError("scores/distances must be finite and conformable; distances symmetric with zero diagonal")
    return scores.T @ (np.maximum(0, 1 - dist / cutoff_km) @ scores)


def conley_covariance(scores, bread_inv, dist_km, cutoff_km) -> tuple[np.ndarray, dict]:
    """Sandwich with the sole small-sample adjustment n/(n-k)."""
    scores, bread = np.asarray(scores, float), np.asarray(bread_inv, float)
    if scores.ndim != 2:
        raise ValueError("scores must be n x k")
    n, k = scores.shape
    if n <= k or bread.shape != (k, k) or not np.isfinite(bread).all():
        raise ValueError("Conley covariance needs n > k and a finite k x k inverse bread")
    meat = conley_meat(scores, dist_km, cutoff_km)
    cov = bread @ meat @ bread.T * n / (n - k)
    cov = (cov + cov.T) / 2
    if not np.isfinite(cov).all() or (np.diag(cov) <= 0).any():
        raise ValueError(f"Conley covariance is not positive at cutoff {cutoff_km}")
    eig = float(np.linalg.eigvalsh(cov).min())
    return cov, {"kernel": "bartlett", "cutoff_km": float(cutoff_km), "n": n,
                 "mean_neighbours": float(np.mean((np.asarray(dist_km) < cutoff_km).sum(axis=1) - 1)),
                 "min_eigenvalue": eig, "psd": bool(eig >= 0)}


def coordinate_distances(data, coords):
    """Align coordinates to the actual complete-case/formula rows, never positional input order."""
    if coords is None:
        raise ValueError("spatial_se requires coords (GEOID, lon, lat)")
    if not {"GEOID", "lon", "lat"}.issubset(coords.columns) or coords["GEOID"].duplicated().any():
        raise ValueError("coords requires unique GEOID, lon, lat")
    aligned = coords.set_index("GEOID").reindex(data["GEOID"].astype(str))
    return haversine_matrix(aligned["lon"], aligned["lat"])


def unit_coordinates(geoids, level, acs_year):
    """Representative points and boundary-file provenance for county/tract units."""
    import pandas as pd
    from .boundaries import boundary_vintage, get_boundaries
    if level not in ("county", "tract"):
        raise ValueError("unit_coordinates supports county and tract")
    geoids = list(dict.fromkeys(map(str, geoids)))
    year = boundary_vintage(acs_year, level)
    frames, files = [], []
    for state in sorted({g[:2] for g in geoids}):
        boundary = get_boundaries(level, year, state)
        attrs = boundary.attrs
        points = boundary.to_crs(epsg=4269).representative_point()
        frames.append(pd.DataFrame({"GEOID": boundary["GEOID"].astype(str), "lon": points.x, "lat": points.y}))
        record = {k: attrs.get(k) for k in ("cache_path", "source_url", "sha256")}
        if record not in files:
            files.append(record)
    all_coords = pd.concat(frames, ignore_index=True).drop_duplicates("GEOID").set_index("GEOID")
    missing = sorted(set(geoids) - set(all_coords.index))
    if missing:
        raise ValueError(f"missing boundary GEOIDs: {missing[:10]}")
    result = all_coords.reindex(geoids).reset_index()
    return result, {"level": level, "boundary_year": year, "files": files}

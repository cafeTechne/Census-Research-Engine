# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 206: Finite-sample simulation calibration for multi-component & island-aware BYM2 (N132)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .disease_mapping import disease_map
from .disease_mapping_core import graph_components, scaled_icar_eigen


def build_multicomponent_graph(grid_side: int = 4, n_islands: int = 2) -> Tuple[int, List[Tuple[int, int]]]:
    """Build two disconnected ``grid_side x grid_side`` rook lattices plus ``n_islands`` isolated nodes."""
    m = grid_side * grid_side
    edges: List[Tuple[int, int]] = []
    for block in (0, m):
        for r in range(grid_side):
            for c in range(grid_side):
                u = block + r * grid_side + c
                if c + 1 < grid_side:
                    edges.append((u, u + 1))
                if r + 1 < grid_side:
                    edges.append((u, u + grid_side))
    n_total = 2 * m + int(n_islands)
    return n_total, edges


def run_multicomponent_bym2_calibration(
    *,
    n_draws: int = 30,
    median_e: float = 40.0,
    sigma: float = 0.35,
    phi: float = 0.70,
    threshold: float = 1.2,
    seed: int = 206,
) -> Dict[str, Any]:
    """Simulate Poisson counts from a 4-component (2 lattices + 2 islands) BYM2 DGP and evaluate B3 coverage."""
    rng = np.random.default_rng(seed)
    n, edges = build_multicomponent_graph(grid_side=4, n_islands=2)
    comps = graph_components(n, edges)
    island_mask = np.zeros(n, dtype=bool)
    for c in comps:
        if len(c) == 1:
            island_mask[c[0]] = True

    V, lam = scaled_icar_eigen(n, edges, allow_disconnected=True)
    # Exact multi-component BYM2 covariance eigenvalues: sigma^2 * ((1 - phi) + phi * lam)
    eig_sd = sigma * np.sqrt(np.maximum((1.0 - phi) + phi * lam, 1e-12))

    cov_conn: List[float] = []
    cov_isl: List[float] = []
    rmse_bym2: List[float] = []
    rmse_smr: List[float] = []
    exc_hits: List[float] = []

    for _ in range(int(n_draws)):
        E = rng.uniform(0.6 * median_e, 1.4 * median_e, size=n)
        b = V @ (eig_sd * rng.normal(size=n))
        true_rr = np.exp(b)
        y = rng.poisson(E * true_rr)
        df = pd.DataFrame({"GEOID": [f"M{i:03d}" for i in range(n)], "y": y, "E": E})
        res = disease_map(df, "y", "E", edges, threshold=threshold, method="B3", allow_disconnected=True)
        tab = res["table"]
        lo = tab["ci_lower"].to_numpy(float)
        hi = tab["ci_upper"].to_numpy(float)
        rr_hat = tab["relative_risk"].to_numpy(float)
        p_exc = tab["p_exceed"].to_numpy(float)
        inside = (true_rr >= lo) & (true_rr <= hi)

        cov_conn.append(float(inside[~island_mask].mean()))
        cov_isl.append(float(inside[island_mask].mean()))
        rmse_bym2.append(float(np.sqrt(np.mean((rr_hat - true_rr) ** 2))))
        rmse_smr.append(float(np.sqrt(np.mean((y / E - true_rr) ** 2))))
        hi_flag = p_exc >= 0.8
        if hi_flag.any():
            exc_hits.append(float((true_rr[hi_flag] > threshold).mean()))

    mean_cov_conn = round(float(np.mean(cov_conn)), 4)
    mean_cov_isl = round(float(np.mean(cov_isl)), 4)
    mean_rmse_bym2 = round(float(np.mean(rmse_bym2)), 4)
    mean_rmse_smr = round(float(np.mean(rmse_smr)), 4)
    return {
        "ok": True,
        "n_areas": n,
        "n_components": len(comps),
        "n_islands": int(island_mask.sum()),
        "n_draws": int(n_draws),
        "median_e": float(median_e),
        "sigma": float(sigma),
        "phi": float(phi),
        "coverage_connected_90": mean_cov_conn,
        "coverage_islands_90": mean_cov_isl,
        "rmse_bym2": mean_rmse_bym2,
        "rmse_raw_smr": mean_rmse_smr,
        "bym2_beats_raw_smr": bool(mean_rmse_bym2 < mean_rmse_smr),
        "exceedance_precision_p80": round(float(np.mean(exc_hits)), 4) if exc_hits else None,
        "note": "Diagnostic calibration of multi-component BYM2 (B3); multi-component fits stay exploratory until full pre-registered 500-draw grid validation.",
    }


if __name__ == "__main__":
    print(json.dumps(run_multicomponent_bym2_calibration(n_draws=30), indent=2))

#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 141: Pre-registered 4-state county Area Deprivation Index (PCA) & BEA RPP real-income study."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.composite_index import build_index
from census.replicate import fetch_vre
from census.rpp import adjust_for_place

PROTOCOL = {
    "round": 141,
    "title": "4-State County Deprivation Index (PCA) & BEA Regional Price Parity Real Per-Capita Income (2020-2024)",
    "states": ["26", "36", "39", "42"],
    "year": 2024,
    "rpp_year": 2023,
    "indicators": ["poverty_pct", "non_ba_pct", "renter_pct", "real_pci"],
    "reverse": ["real_pci"],
    "typology_k": 3,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_counties() -> pd.DataFrame:
    rows = []
    ba_vars = [f"B15002_{i:03d}" for i in (15, 16, 17, 18, 32, 33, 34, 35)]
    for st in PROTOCOL["states"]:
        pov = fetch_vre("B17001", 2024, "county", state_code=st)
        edu = fetch_vre("B15002", 2024, "county", state_code=st)
        ten = fetch_vre("B25003", 2024, "county", state_code=st)
        inc = fetch_vre("B19025", 2024, "county", state_code=st)
        pop = fetch_vre("B01003", 2024, "county", state_code=st)

        p_num = pov[pov["variable"] == "B17001_002"].set_index("GEOID")["estimate"]
        p_den = pov[pov["variable"] == "B17001_001"].set_index("GEOID")["estimate"]
        e_ba = edu[edu["variable"].isin(ba_vars)].groupby("GEOID")["estimate"].sum()
        e_den = edu[edu["variable"] == "B15002_001"].set_index("GEOID")["estimate"]
        r_num = ten[ten["variable"] == "B25003_003"].set_index("GEOID")["estimate"]
        r_den = ten[ten["variable"] == "B25003_001"].set_index("GEOID")["estimate"]
        agg_inc = inc[inc["variable"] == "B19025_001"].set_index("GEOID")["estimate"]
        tot_pop = pop[pop["variable"] == "B01003_001"].set_index("GEOID")["estimate"]

        common = sorted(set(p_num.index) & set(p_den.index) & set(e_ba.index) & set(e_den.index)
                        & set(r_num.index) & set(r_den.index) & set(agg_inc.index) & set(tot_pop.index))
        for g in common:
            nom_pci = float(agg_inc.loc[g]) / float(tot_pop.loc[g])
            real_pci = float(adjust_for_place(nom_pci, st, PROTOCOL["rpp_year"]))
            rows.append({
                "GEOID": g,
                "state": st,
                "pop": float(tot_pop.loc[g]),
                "poverty_pct": 100.0 * float(p_num.loc[g]) / float(p_den.loc[g]),
                "non_ba_pct": 100.0 * (1.0 - float(e_ba.loc[g]) / float(e_den.loc[g])),
                "renter_pct": 100.0 * float(r_num.loc[g]) / float(r_den.loc[g]),
                "nominal_pci": nom_pci,
                "real_pci": real_pci,
            })
    return pd.DataFrame(rows)


def main() -> None:
    df = load_counties()
    idx = build_index(
        df,
        PROTOCOL["indicators"],
        method="pca",
        reverse=PROTOCOL["reverse"],
        typology_k=PROTOCOL["typology_k"],
        level=0.90,
    )
    scores = idx["table"]
    merged = df.merge(scores[["area", "score"]], left_on="GEOID", right_on="area", how="inner")

    by_state: Dict[str, Any] = {}
    for st, sub in merged.groupby("state"):
        by_state[st] = {
            "n_counties": int(len(sub)),
            "median_nominal_pci": float(sub["nominal_pci"].median()),
            "median_real_pci": float(sub["real_pci"].median()),
            "mean_deprivation_score": float(sub["score"].mean()),
        }

    nom_spread = max(v["median_nominal_pci"] for v in by_state.values()) - min(v["median_nominal_pci"] for v in by_state.values())
    real_spread = max(v["median_real_pci"] for v in by_state.values()) - min(v["median_real_pci"] for v in by_state.values())

    out_dir = Path("studies_output/r141_deprivation_rpp")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "n_counties_total": int(len(merged)),
        "variance_explained_pc1": float(idx["explained_variance"]),
        "loadings": {k: float(v) for k, v in idx.get("loadings", {}).items()},
        "typology_groups": {str(k): int(v) for k, v in idx.get("typology", {}).get("groups", {}).items()},
        "state_nominal_pci_spread": float(nom_spread),
        "state_real_pci_spread": float(real_spread),
        "states": by_state,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

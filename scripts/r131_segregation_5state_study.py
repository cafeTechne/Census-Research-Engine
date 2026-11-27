#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 131: Pre-registered 5-state county racial segregation study (ACS 2019-2023 tract B03002 VRE)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.replicate import fetch_vre
from census.segregation import segregation_indices

PROTOCOL = {
    "round": 131,
    "title": "5-State County Racial Segregation Study (AZ, GA, MI, NY, TX; ACS 2019-2023 Tract B03002 VRE)",
    "states": ["04", "13", "26", "36", "48"],
    "year": 2023,
    "table": "B03002",
    "groups": ["nh_white (B03002_003)", "nh_black (B03002_004)", "nh_asian (B03002_006)", "hispanic (B03002_012)"],
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_state(state_fips: str) -> Dict[str, Any]:
    raw = fetch_vre("B03002", 2023, "tract", state_code=state_fips)
    vars_wanted = {"B03002_003": "white", "B03002_004": "black", "B03002_006": "asian", "B03002_012": "hispanic"}
    sub = raw[raw["variable"].isin(vars_wanted)].copy()
    sub["grp"] = sub["variable"].map(vars_wanted)
    piv = sub.pivot(index="GEOID", columns="grp", values="estimate").fillna(0.0)
    piv["county"] = piv.index.astype(str).str[:5]

    rows = []
    for cty, grp in piv.groupby("county"):
        mat4 = grp[["white", "black", "asian", "hispanic"]].to_numpy(float)
        if mat4.shape[0] < 2 or mat4.sum() <= 0:
            continue
        non_black = mat4[:, 0] + mat4[:, 2] + mat4[:, 3]
        mat2 = np.column_stack([mat4[:, 1], non_black])
        if mat2[:, 0].sum() <= 0 or mat2[:, 1].sum() <= 0:
            continue
        idx2 = segregation_indices(mat2)
        idx4 = segregation_indices(mat4)
        rows.append({
            "county": cty,
            "n_tracts": int(mat4.shape[0]),
            "D_black_nonblack": float(idx2["dissimilarity"]),
            "isolation_black": float(idx2["isolation"]),
            "H_2group": float(idx2["theil_h"]),
            "H_4group": float(idx4["theil_h"]),
        })
    df_out = pd.DataFrame(rows)
    return {
        "state": state_fips,
        "n_counties": int(len(df_out)),
        "median_D_black_nonblack": float(df_out["D_black_nonblack"].median()),
        "iqr_D_black_nonblack": [float(df_out["D_black_nonblack"].quantile(0.25)),
                                 float(df_out["D_black_nonblack"].quantile(0.75))],
        "median_H_4group": float(df_out["H_4group"].median()),
        "max_H_4group": float(df_out["H_4group"].max()),
    }


def main() -> None:
    out_dir = Path("studies_output/r131_segregation")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "states": {st: run_state(st) for st in PROTOCOL["states"]},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 132: Pre-registered Arcsine & Rao-Yu Temporal Fay-Herriot SAE Study (MI/NY primary, OH/PA replication)."""
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
from census.sae_extensions import arcsine_small_area, temporal_small_area

PROTOCOL = {
    "round": 132,
    "title": "Arcsine and Rao-Yu Temporal Fay-Herriot Small-Area Poverty Estimation (MI/NY & OH/PA, 2015-2019 vs 2020-2024)",
    "primary_states": ["26", "36"],
    "replication_states": ["39", "42"],
    "releases": [2019, 2024],
    "confidence_level": 0.90,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_vre_poverty(states: list[str], year: int) -> pd.DataFrame:
    raw = pd.concat([fetch_vre("B17001", year, "county", state_code=st) for st in states], ignore_index=True)
    num = raw[raw["variable"] == "B17001_002"].set_index("GEOID")
    den = raw[raw["variable"] == "B17001_001"].set_index("GEOID")
    common = sorted(set(num.index) & set(den.index))
    num, den = num.loc[common], den.loc[common]
    rep_cols = [f"rep_{i}" for i in range(1, 81)]
    est = num["estimate"].to_numpy(float) / den["estimate"].to_numpy(float)
    reps = num[rep_cols].to_numpy(float) / den[rep_cols].to_numpy(float)
    se = np.sqrt(4.0 / 80.0 * np.sum((reps - est[:, None]) ** 2, axis=1))
    return pd.DataFrame({
        "GEOID": common,
        "Year": year,
        "state": [g[:2] for g in common],
        "poverty_prop": est,
        "poverty_se": se,
    })


def run_region(states: list[str]) -> Dict[str, Any]:
    d19 = _load_vre_poverty(states, 2019)
    d24 = _load_vre_poverty(states, 2024)
    panel = pd.concat([d19, d24], ignore_index=True)

    arc = arcsine_small_area(d24, "poverty_prop ~ C(state)", se_col="poverty_se", percent=False,
                             bootstrap=150, level=0.90)
    tmp = temporal_small_area(panel, "poverty_prop ~ C(state)", se_col="poverty_se",
                              release_column="Year", period_years=5, bootstrap=100, level=0.90)

    direct_var = d24.set_index("GEOID")["poverty_se"].to_numpy(float) ** 2
    arc_mse = arc.set_index("GEOID").loc[d24["GEOID"], "mse"].to_numpy(float)
    tmp_mse = tmp.set_index("GEOID").loc[d24["GEOID"], "mse"].to_numpy(float)
    arc_mse_gain = float(np.median(1.0 - arc_mse / direct_var))
    tmp_mse_gain = float(np.median(1.0 - tmp_mse / direct_var))

    return {
        "states": states,
        "n_counties": int(len(d24)),
        "arcsine_fh": {
            "median_mse_reduction": arc_mse_gain,
            "validated": bool(arc.attrs.get("validated", True)),
        },
        "temporal_rao_yu_fh": {
            "median_mse_reduction": tmp_mse_gain,
            "validated": bool(tmp.attrs.get("validated", True)),
        },
    }


def main() -> None:
    out_dir = Path("studies_output/r132_sae_temporal")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "MI_NY": run_region(["26", "36"]),
        "OH_PA": run_region(["39", "42"]),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

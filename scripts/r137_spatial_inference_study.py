#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 137: Pre-registered spatial correlation (effective-n) & SCPC vs HC3 inference study (MI/NY & OH/PA)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from census.correlation import validated_correlations
from census.replicate import fetch_vre
from census.scpc import fit_scpc

PROTOCOL = {
    "round": 137,
    "title": "County Spatial Autocorrelation (Effective-n) and SCPC vs HC3 Inference: Poverty on BA+ Education (2020-2024)",
    "primary_states": ["26", "36"],
    "replication_states": ["39", "42"],
    "year": 2024,
    "rho_bar": 0.05,
    "confidence_level": 0.90,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_region(states: list[str]) -> pd.DataFrame:
    pov = pd.concat([fetch_vre("B17001", 2024, "county", state_code=st) for st in states], ignore_index=True)
    edu = pd.concat([fetch_vre("B15002", 2024, "county", state_code=st) for st in states], ignore_index=True)

    p_num = pov[pov["variable"] == "B17001_002"].set_index("GEOID")["estimate"]
    p_den = pov[pov["variable"] == "B17001_001"].set_index("GEOID")["estimate"]
    ba_vars = [f"B15002_{i:03d}" for i in (15, 16, 17, 18, 32, 33, 34, 35)]
    e_num = edu[edu["variable"].isin(ba_vars)].groupby("GEOID")["estimate"].sum()
    e_den = edu[edu["variable"] == "B15002_001"].set_index("GEOID")["estimate"]

    common = sorted(set(p_num.index) & set(p_den.index) & set(e_num.index) & set(e_den.index))
    return pd.DataFrame({
        "GEOID": common,
        "Year": 2024,
        "state": [g[:2] for g in common],
        "poverty": 100.0 * p_num.loc[common].to_numpy(float) / p_den.loc[common].to_numpy(float),
        "ba_plus": 100.0 * e_num.loc[common].to_numpy(float) / e_den.loc[common].to_numpy(float),
    })


def run_region(states: list[str]) -> Dict[str, Any]:
    df = _load_region(states)
    corr_sp = validated_correlations(df, ["poverty", "ba_plus"], method="spearman", confidence_level=0.90)
    scpc_res = fit_scpc("poverty ~ ba_plus + C(state)", df, model="ols", rho_bar=0.05, level=0.90)
    ols_hc3 = smf.ols("poverty ~ ba_plus + C(state)", data=df).fit(cov_type="HC3")
    hc3_se = float(ols_hc3.bse["ba_plus"])
    scpc_tbl = scpc_res["table"]
    row = scpc_tbl[scpc_tbl["term"] == "ba_plus"].iloc[0]
    lo_col = "ci_lower" if "ci_lower" in scpc_tbl.columns else "lower"
    hi_col = "ci_upper" if "ci_upper" in scpc_tbl.columns else "upper"
    scpc_width = float(row[hi_col] - row[lo_col])
    hc3_width = float(2.0 * 1.6448536 * hc3_se)

    return {
        "states": states,
        "n_counties": int(len(df)),
        "spatial_spearman": corr_sp.to_dict(orient="records"),
        "ba_plus_slope": {
            "estimate": float(row["estimate"]),
            "hc3_se": hc3_se,
            "scpc_lower": float(row[lo_col]),
            "scpc_upper": float(row[hi_col]),
            "width_ratio_scpc_vs_hc3": scpc_width / hc3_width if hc3_width > 0 else float("nan"),
            "validated": bool(scpc_res.get("validated", True)),
        },
    }


def main() -> None:
    out_dir = Path("studies_output/r137_spatial_inference")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "MI_NY": run_region(["26", "36"]),
        "OH_PA": run_region(["39", "42"]),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

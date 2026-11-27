#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 139: Pre-registered KWW county poverty ranking & Holm state-reference comparison (MI, NY, OH, PA)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.ranking import compare_to_reference, rank_intervals
from census.replicate import fetch_vre

PROTOCOL = {
    "round": 139,
    "title": "County Poverty Ranking (KWW Individual & Joint Intervals) and Holm State-Reference Comparisons (2020-2024)",
    "states": ["26", "36", "39", "42"],
    "year": 2024,
    "confidence_level": 0.90,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_state(state_fips: str) -> Dict[str, Any]:
    raw = fetch_vre("B17001", 2024, "county", state_code=state_fips)
    num = raw[raw["variable"] == "B17001_002"].set_index("GEOID")
    den = raw[raw["variable"] == "B17001_001"].set_index("GEOID")
    common = sorted(set(num.index) & set(den.index))
    num, den = num.loc[common], den.loc[common]
    rep_cols = [f"rep_{i}" for i in range(1, 81)]
    est = 100.0 * num["estimate"].to_numpy(float) / den["estimate"].to_numpy(float)
    reps = 100.0 * num[rep_cols].to_numpy(float) / den[rep_cols].to_numpy(float)
    se = np.sqrt(4.0 / 80.0 * np.sum((reps - est[:, None]) ** 2, axis=1))
    df = pd.DataFrame({
        "GEOID": common,
        "poverty": est,
        "poverty_se": se,
        "pop": den["estimate"].to_numpy(float),
    })

    rk_ind = rank_intervals(df, "poverty", se_col="poverty_se", joint=False, level=0.90)
    rk_jnt = rank_intervals(df, "poverty", se_col="poverty_se", joint=True, level=0.90)
    ref = compare_to_reference(df, "poverty", se_col="poverty_se", reference="weighted_mean",
                               weights="pop", method="holm", level=0.90)

    ti = rk_ind["table"]
    tj = rk_jnt["table"]
    tr = ref["table"]
    n = len(ti)
    top10_cut = max(1, int(np.ceil(0.10 * n)))
    surely_top10 = int((ti["rank_upper"] <= top10_cut).sum())
    sig_col = next((c for c in tr.columns if "reject" in c or "differs" in c or "significant" in c), None)
    n_diff_ref = int(tr[sig_col].sum()) if sig_col else int((tr["p_adjusted"] < 0.10).sum())

    return {
        "state": state_fips,
        "n_counties": n,
        "median_individual_rank_width": float((ti["rank_upper"] - ti["rank_lower"]).median()),
        "median_joint_rank_width": float((tj["rank_upper"] - tj["rank_lower"]).median()),
        "surely_top_decile_counties": surely_top10,
        "counties_differing_from_state_holm": n_diff_ref,
        "reference_rate": float(ref["reference_value"]),
    }


def main() -> None:
    out_dir = Path("studies_output/r139_county_ranking")
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

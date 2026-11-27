#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 122: Pre-registered multi-release (2015-2019 vs 2020-2024) county disparity, DiD & meta-analysis study."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy import stats

from census.context_sources import fetch_ers
from census.did import difference_in_differences
from census.evidence import combine_estimates
from census.multitest import adjust_pvalues
from census.replicate import fetch_vre

PROTOCOL = {
    "round": 122,
    "title": "Multi-Release County Poverty Disparity, Rural-Urban DiD, and 4-State Pooling (ACS 2015-2019 vs 2020-2024)",
    "primary_states": ["26", "36"],
    "replication_states": ["39", "42"],
    "releases": [2019, 2024],
    "confidence_level": 0.90,
    "alpha": 0.10,
    "correction": "holm",
    "hypotheses": [
        {"id": "H1", "statement": "Nonmetro counties have higher population-weighted poverty than metro counties in 2020-2024 (rate difference > 0).", "direction": "greater"},
        {"id": "H2", "statement": "The nonmetro-minus-metro county poverty gap changed between 2015-2019 and 2020-2024.", "direction": "two-sided"},
        {"id": "H3", "statement": "Nonmetro vs metro county poverty followed a differential 2015-2019 to 2020-2024 trajectory (two-group DiD).", "direction": "two-sided"},
    ],
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_vre_poverty(states: list[str], year: int) -> pd.DataFrame:
    frames = [fetch_vre("B17001", year, "county", state_code=st) for st in states]
    raw = pd.concat(frames, ignore_index=True)
    num = raw[raw["variable"] == "B17001_002"].set_index("GEOID")
    den = raw[raw["variable"] == "B17001_001"].set_index("GEOID")
    common = sorted(set(num.index) & set(den.index))
    num, den = num.loc[common], den.loc[common]
    rep_cols = [f"rep_{i}" for i in range(1, 81)]
    est = 100.0 * num["estimate"].to_numpy(float) / den["estimate"].to_numpy(float)
    reps = 100.0 * num[rep_cols].to_numpy(float) / den[rep_cols].to_numpy(float)
    se = np.sqrt(4.0 / 80.0 * np.sum((reps - est[:, None]) ** 2, axis=1))
    return pd.DataFrame({
        "GEOID": common,
        "Year": year,
        "state": [g[:2] for g in common],
        "poverty": est,
        "poverty_se": se,
        "pop_universe": den["estimate"].to_numpy(float),
    })


def _group_gap(df_yr: pd.DataFrame) -> Dict[str, float]:
    out = {}
    for k, label in ((1, "nonmetro"), (0, "metro")):
        sub = df_yr[df_yr["nonmetro"] == k]
        w = sub["pop_universe"].to_numpy(float)
        x = sub["poverty"].to_numpy(float)
        s = sub["poverty_se"].to_numpy(float)
        wsum = w.sum()
        out[label] = float(np.sum(w * x) / wsum)
        out[f"{label}_se"] = float(np.sqrt(np.sum((w * s) ** 2)) / wsum)
    rd = out["nonmetro"] - out["metro"]
    rd_se = float(np.hypot(out["nonmetro_se"], out["metro_se"]))
    z90 = float(stats.norm.ppf(0.95))
    return {
        **out,
        "rd": rd,
        "rd_se": rd_se,
        "rd_lower": rd - z90 * rd_se,
        "rd_upper": rd + z90 * rd_se,
    }


def run_region(states: list[str], ers_small: pd.DataFrame) -> Dict[str, Any]:
    d19 = _load_vre_poverty(states, 2019)
    d24 = _load_vre_poverty(states, 2024)
    panel = pd.concat([d19, d24], ignore_index=True).merge(ers_small, on="GEOID", how="inner")

    g19 = _group_gap(panel[panel["Year"] == 2019])
    g24 = _group_gap(panel[panel["Year"] == 2024])
    gap_chg = g24["rd"] - g19["rd"]
    gap_chg_se = float(np.hypot(g24["rd_se"], g19["rd_se"]))
    z90 = float(stats.norm.ppf(0.95))

    did_res = difference_in_differences(panel, "poverty", "nonmetro", 2024, period="Year",
                                        se="poverty_se", design="two_group", period_years=5)
    did_dict = did_res.to_dict()
    did_row = next(c for c in did_dict["coefficients"] if c.get("role") == "effect")

    state_dids = {}
    for st in states:
        sub = panel[panel["state"] == st].copy()
        r_st = difference_in_differences(sub, "poverty", "nonmetro", 2024, period="Year",
                                         se="poverty_se", design="two_group", period_years=5).to_dict()
        row_st = next(c for c in r_st["coefficients"] if c.get("role") == "effect")
        state_dids[st] = {
            "estimate": float(row_st["estimate"]),
            "se": float(row_st["se_total"]),
            "ci_lower": float(row_st["ci_lower"]),
            "ci_upper": float(row_st["ci_upper"]),
        }

    p_h1 = float(stats.norm.sf(g24["rd"] / g24["rd_se"]))
    p_h2 = float(2.0 * stats.norm.sf(abs(gap_chg) / gap_chg_se))
    p_h3 = float(did_row["p_value"])
    p_adj = [float(x) for x in adjust_pvalues([p_h1, p_h2, p_h3], method="holm")]

    return {
        "states": states,
        "n_counties": int(panel["GEOID"].nunique()),
        "gap_2019": g19,
        "H1_nonmetro_vs_metro_2024": {
            "rd": g24["rd"], "se": g24["rd_se"], "lower": g24["rd_lower"], "upper": g24["rd_upper"],
            "nonmetro_rate": g24["nonmetro"], "metro_rate": g24["metro"],
            "p_raw": p_h1, "p_holm": p_adj[0],
        },
        "H2_disparity_change_19_24": {
            "change": gap_chg, "se": gap_chg_se,
            "lower": gap_chg - z90 * gap_chg_se, "upper": gap_chg + z90 * gap_chg_se,
            "p_raw": p_h2, "p_holm": p_adj[1],
        },
        "H3_did_nonmetro_poverty": {
            "estimate": float(did_row["estimate"]), "se": float(did_row["se_total"]),
            "ci_lower": float(did_row["ci_lower"]), "ci_upper": float(did_row["ci_upper"]),
            "p_raw": p_h3, "p_holm": p_adj[2],
        },
        "state_dids": state_dids,
    }


def main() -> None:
    out_dir = Path("studies_output/r122_disparity_did")
    out_dir.mkdir(parents=True, exist_ok=True)
    ers, _ = fetch_ers()
    ers = ers.copy()
    ers["GEOID"] = ers.index.astype(str).str.zfill(5)
    metro_col = next(c for c in ers.columns if "metro" in c.lower() or "rucc" in c.lower())
    if "rucc" in metro_col.lower():
        ers["nonmetro"] = (pd.to_numeric(ers[metro_col], errors="coerce") >= 4).astype(int)
    else:
        ers["nonmetro"] = (pd.to_numeric(ers[metro_col], errors="coerce") == 0).astype(int)
    ers_small = ers[["GEOID", "nonmetro"]].drop_duplicates("GEOID")

    mi_ny = run_region(["26", "36"], ers_small)
    oh_pa = run_region(["39", "42"], ers_small)

    all_states = {**mi_ny["state_dids"], **oh_pa["state_dids"]}
    ests = [all_states[s]["estimate"] for s in sorted(all_states)]
    ses = [all_states[s]["se"] for s in sorted(all_states)]
    pooled = combine_estimates(ests, ses, method="hksj", level=0.90)

    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "MI_NY": mi_ny,
        "OH_PA": oh_pa,
        "H4_pooled_4state_did": {
            "states": sorted(all_states),
            "pooled": pooled["pooled"],
            "validated": pooled["validated"],
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

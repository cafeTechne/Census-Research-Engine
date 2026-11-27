#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 134: Pre-registered WHO Health Inequality Monitoring & Priority Quadrants Study (MI, NY, OH, PA)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.context_sources import fetch_ers
from census.inequality_monitoring import monitoring_measures, priority_quadrants
from census.replicate import fetch_vre

PROTOCOL = {
    "round": 134,
    "title": "WHO Poverty Inequality Monitoring (PAR vs Best Subgroup) and Priority Quadrants (MI, NY, OH, PA; ACS 2020-2024)",
    "states": ["26", "36", "39", "42"],
    "year": 2024,
    "confidence_level": 0.90,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> None:
    ers, _ = fetch_ers()
    ers = ers.copy()
    ers["GEOID"] = ers.index.astype(str).str.zfill(5)
    metro_col = next(c for c in ers.columns if "metro" in c.lower() or "rucc" in c.lower())
    if "rucc" in metro_col.lower():
        ers["nonmetro"] = (pd.to_numeric(ers[metro_col], errors="coerce") >= 4).astype(int)
    else:
        ers["nonmetro"] = (pd.to_numeric(ers[metro_col], errors="coerce") == 0).astype(int)
    ers_map = dict(zip(ers["GEOID"], ers["nonmetro"]))

    rep_cols = [f"rep_{i}" for i in range(1, 81)]
    area_rows = []
    rep_rows = []
    for st in PROTOCOL["states"]:
        raw = fetch_vre("B17001", 2024, "county", state_code=st)
        num = raw[raw["variable"] == "B17001_002"].set_index("GEOID")
        den = raw[raw["variable"] == "B17001_001"].set_index("GEOID")
        common = sorted(set(num.index) & set(den.index))
        num, den = num.loc[common], den.loc[common]
        nm_mask = np.array([ers_map.get(g, 0) for g in common]) == 1

        row = {"GEOID": st}
        for label, mask in (("metro", ~nm_mask), ("nonmetro", nm_mask)):
            p_num = float(num["estimate"].to_numpy(float)[mask].sum())
            p_den = float(den["estimate"].to_numpy(float)[mask].sum())
            row[f"rate_{label}"] = 100.0 * p_num / p_den
            row[f"pop_{label}"] = p_den
        area_rows.append(row)

        for label, mask in (("metro", ~nm_mask), ("nonmetro", nm_mask)):
            rate_row = {"GEOID": st, "variable": f"rate_{label}"}
            pop_row = {"GEOID": st, "variable": f"pop_{label}"}
            for rc in rep_cols:
                p_num = float(num[rc].to_numpy(float)[mask].sum())
                p_den = float(den[rc].to_numpy(float)[mask].sum())
                rate_row[rc] = 100.0 * p_num / p_den
                pop_row[rc] = p_den
            rep_rows.append(rate_row)
            rep_rows.append(pop_row)

    frame = pd.DataFrame(area_rows)
    reps = pd.DataFrame(rep_rows)
    who = monitoring_measures(
        frame, groups=["rate_metro", "rate_nonmetro"], populations=["pop_metro", "pop_nonmetro"],
        replicates=reps, reference="best", level=0.90,
    )

    par_df = who[who["measure"] == "par"].copy()
    q_rows = []
    for _, r in frame.iterrows():
        st = r["GEOID"]
        tot_pop = r["pop_metro"] + r["pop_nonmetro"]
        lvl = (r["rate_metro"] * r["pop_metro"] + r["rate_nonmetro"] * r["pop_nonmetro"]) / tot_pop
        sub_r = reps[reps["GEOID"] == st].set_index("variable")[rep_cols]
        rm, rn = sub_r.loc["rate_metro"].to_numpy(float), sub_r.loc["rate_nonmetro"].to_numpy(float)
        pm, pn = sub_r.loc["pop_metro"].to_numpy(float), sub_r.loc["pop_nonmetro"].to_numpy(float)
        lvl_r = (rm * pm + rn * pn) / (pm + pn)
        lvl_se = float(np.sqrt(4.0 / 80.0 * np.sum((lvl_r - lvl) ** 2)))
        pr = par_df[par_df["GEOID"] == st].iloc[0]
        lo_col = "ci_lower" if "ci_lower" in par_df.columns else "lower"
        hi_col = "ci_upper" if "ci_upper" in par_df.columns else "upper"
        q_rows.append({
            "GEOID": st,
            "level": lvl, "level_lower": lvl - 1.645 * lvl_se, "level_upper": lvl + 1.645 * lvl_se,
            "par": float(pr["estimate"]), "par_lower": float(pr[lo_col]), "par_upper": float(pr[hi_col]),
        })
    quads = priority_quadrants(pd.DataFrame(q_rows), level="level", inequality="par")

    lo_col = "ci_lower" if "ci_lower" in par_df.columns else "lower"
    hi_col = "ci_upper" if "ci_upper" in par_df.columns else "upper"
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "who_par_vs_best": par_df[["GEOID", "estimate", lo_col, hi_col, "validated"]].to_dict(orient="records"),
        "priority_quadrants": quads.to_dict(orient="records"),
    }
    out_dir = Path("studies_output/r134_who_inequality")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

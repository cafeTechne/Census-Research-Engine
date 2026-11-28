#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 197 (N128): Age-Structure (% 65+) & Urban-Rural Stratified County Mortality Confounding Study.

Directly tests why 6 chronic/suicide mortality causes showed inverted crude Q4/Q1 poverty rate ratios
(RR < 1.0) in NY+PA in the Round 188 11-cause atlas while remaining strongly positive in MI+OH.
100% offline using cached 2024 ACS B17001 VRE (poverty + exact 65+ age share), TIGER county land area
(population density), and local CDC WONDER 2018-2022 county exports (zero raw counts 1-9 emitted).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import statsmodels.api as sm

from census.boundaries import join_boundaries
from census.replicate import fetch_vre
from census.report_tables import results_bundle, verify_bundle

CAUSES = [
    "heart_disease", "drug_overdose", "stroke", "suicide", "diabetes",
    "clrd", "liver_disease", "kidney_disease", "firearm", "alcohol_induced",
    "unintentional_injury",
]
AGE65_VARS = (
    "B17001_015", "B17001_016", "B17001_029", "B17001_030",
    "B17001_044", "B17001_045", "B17001_058", "B17001_059",
)
OUT_DIR = ROOT / "studies_output" / "r197_age_urban_confounding"
DOCS_MD = ROOT / "docs" / "studies" / "r197_age_urban_confounding_study.md"


def _load_county_covariates(states: List[str]) -> pd.DataFrame:
    pov = pd.concat([fetch_vre("B17001", 2024, "county", state_code=st) for st in states], ignore_index=True)
    piv = pov.pivot_table(index="GEOID", columns="variable", values="estimate", aggfunc="first")
    tot = piv["B17001_001"].astype(float)
    below = piv["B17001_002"].astype(float)
    age65 = piv[list(AGE65_VARS)].astype(float).sum(axis=1)
    df = pd.DataFrame({
        "GEOID": piv.index.astype(str),
        "poverty_pct": 100.0 * below / tot,
        "pct_65_plus": 100.0 * age65 / tot,
        "acs_pop": tot,
    }).dropna().reset_index(drop=True)
    gdf = join_boundaries(df, "county", year=2024, geoid_col="GEOID").dropna(subset=["geometry"]).copy()
    gdf_proj = gdf.to_crs("EPSG:5070")
    area_km2 = np.maximum(gdf_proj.geometry.area.to_numpy(float) / 1e6, 0.1)
    gdf["log_pop_density"] = np.log(np.maximum(gdf["acs_pop"].to_numpy(float) / area_km2, 0.1))
    gdf["urban_stratum"] = np.where(gdf["acs_pop"] >= 100_000, "urban_metro", "rural_small")
    return pd.DataFrame(gdf[["GEOID", "poverty_pct", "pct_65_plus", "log_pop_density", "urban_stratum"]])


def _load_wonder(cause: str, states: List[str]) -> pd.DataFrame:
    path = ROOT / f"external_data/wonder/ucd/2018-2022/county/{cause}.tsv"
    raw = pd.read_csv(path, sep="\t", dtype=str)
    raw = raw[raw["Notes"].isna() & raw["County Code"].notna()].copy()
    raw["GEOID"] = raw["County Code"].str.zfill(5)
    raw = raw[raw["GEOID"].str[:2].isin(states)].copy()
    raw["deaths"] = pd.to_numeric(raw["Deaths"], errors="coerce")
    raw["population"] = pd.to_numeric(raw["Population"], errors="coerce")
    raw = raw.dropna(subset=["deaths", "population"])
    raw = raw[(raw["deaths"] >= 10) & (raw["population"] > 0)].reset_index(drop=True)
    return raw[["GEOID", "deaths", "population"]]


def _fit_poisson_rr(df: pd.DataFrame, cols: List[str]) -> Dict[str, float]:
    X = sm.add_constant(df[cols].astype(float))
    y = df["deaths"].astype(float)
    off = np.log(df["population"].astype(float))
    fit = sm.GLM(y, X, family=sm.families.Poisson(), offset=off).fit(cov_type="HC3")
    b = float(fit.params["pov_10pp"])
    se = float(fit.bse["pov_10pp"])
    return {
        "rr_per_10pp_pov": round(float(np.exp(b)), 4),
        "ci90_lo": round(float(np.exp(b - 1.64485 * se)), 4),
        "ci90_hi": round(float(np.exp(b + 1.64485 * se)), 4),
    }


def run_study() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cov_by_reg = {
        "MI_OH": _load_county_covariates(["26", "39"]),
        "NY_PA": _load_county_covariates(["36", "42"]),
    }
    rows: List[Dict[str, Any]] = []
    for cause in CAUSES:
        rec: Dict[str, Any] = {"cause": cause}
        for reg, states in (("MI_OH", ["26", "39"]), ("NY_PA", ["36", "42"])):
            wdf = _load_wonder(cause, states)
            m = wdf.merge(cov_by_reg[reg], on="GEOID", how="inner")
            m["pov_10pp"] = m["poverty_pct"] / 10.0
            crude = _fit_poisson_rr(m, ["pov_10pp"])
            adj = _fit_poisson_rr(m, ["pov_10pp", "pct_65_plus", "log_pop_density"])
            rural = m[m["urban_stratum"] == "rural_small"]
            rural_adj = _fit_poisson_rr(rural, ["pov_10pp", "pct_65_plus"]) if len(rural) >= 20 else None
            rec[reg] = {
                "n_counties": int(len(m)),
                "crude": crude,
                "age_urban_adjusted": adj,
                "rural_age_adjusted": rural_adj,
                "sign_flipped_positive_after_adj": bool(
                    crude["rr_per_10pp_pov"] < 1.0 and adj["rr_per_10pp_pov"] > 1.0
                ),
            }
        rows.append(rec)

    ny_crude_lt1 = sum(1 for r in rows if r["NY_PA"]["crude"]["rr_per_10pp_pov"] < 1.0)
    ny_adj_gt1 = sum(1 for r in rows if r["NY_PA"]["age_urban_adjusted"]["rr_per_10pp_pov"] > 1.0)
    ny_flips = [r["cause"] for r in rows if r["NY_PA"]["sign_flipped_positive_after_adj"]]

    summary = {
        "round": 197,
        "roadmap_id": "N128",
        "title": "Age-Structure (% 65+) & Urban-Rural Stratified County Mortality Confounding Study (11 Causes, MI+OH vs NY+PA)",
        "cause_count": len(rows),
        "ny_pa_crude_rr_below_1_count": ny_crude_lt1,
        "ny_pa_adjusted_rr_above_1_count": ny_adj_gt1,
        "ny_pa_causes_flipped_positive_after_adjustment": ny_flips,
        "rows": rows,
    }
    sha = hashlib.sha256(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    summary["summary_sha256"] = sha

    # Write Markdown study report
    md_lines = [
        "# Round 197 (N128): Age-Structure (% 65+) & Urban-Rural Confounding in the 11-Cause County Mortality Atlas",
        "",
        f"- **Causes analyzed:** `{len(rows)}` CDC WONDER 2018–2022 county mortality causes across MI+OH and NY+PA.",
        f"- **Key Finding (NY+PA confounding resolution):** Before adjustment, **`{ny_crude_lt1}/11`** causes had crude poverty RR `< 1.0` per +10 pp poverty in NY+PA; after adjusting for county `% age 65+` (from cached 2024 ACS `B17001` VRE) and `log(population density)`, **`{ny_adj_gt1}/11`** causes are positive (`RR > 1.0`), with **`{len(ny_flips)}` causes flipping sign from `< 1.0` to `> 1.0`**: `{ny_flips}`.",
        "- **Governance:** 100% offline reproducible; zero automated WONDER access; zero raw sub-national counts 1–9 emitted.",
        "",
        "| Cause | NY+PA Crude RR (+10pp pov) | NY+PA Age+Urban Adj RR (90% CI) | Flipped >1? | MI+OH Crude RR | MI+OH Age+Urban Adj RR |",
        "| --- | ---: | --- | :---: | ---: | ---: |",
    ]
    for r in rows:
        ny_c = r["NY_PA"]["crude"]
        ny_a = r["NY_PA"]["age_urban_adjusted"]
        mi_c = r["MI_OH"]["crude"]
        mi_a = r["MI_OH"]["age_urban_adjusted"]
        flip = "Yes" if r["NY_PA"]["sign_flipped_positive_after_adj"] else "—"
        md_lines.append(
            f"| {r['cause']} | {ny_c['rr_per_10pp_pov']:.3f} | "
            f"{ny_a['rr_per_10pp_pov']:.3f} ({ny_a['ci90_lo']:.3f}–{ny_a['ci90_hi']:.3f}) | {flip} | "
            f"{mi_c['rr_per_10pp_pov']:.3f} | {mi_a['rr_per_10pp_pov']:.3f} |"
        )
    DOCS_MD.parent.mkdir(parents=True, exist_ok=True)
    DOCS_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    bdir = OUT_DIR / "bundle"
    if bdir.exists():
        shutil.rmtree(bdir)
    results_bundle(
        str(bdir),
        methods="\n".join(md_lines[:6]) + "\n",
        results={"rows": rows, "ny_pa_flips": ny_flips},
        provenance={"round": 197, "summary_sha256": sha},
        citation="CDC WONDER UCD 2018-2022 (local manual exports); ACS 2020-2024 B17001 VRE.",
        references={"references.bib": "@misc{cdc_wonder_2018_2022, title={CDC WONDER UCD 2018-2022}, year={2024}}\n"},
    )
    ver = verify_bundle(str(bdir))
    summary["bundle_verification"] = ver
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    rep = run_study()
    print(json.dumps({
        "ok": rep["bundle_verification"]["ok"],
        "ny_pa_crude_lt1": rep["ny_pa_crude_rr_below_1_count"],
        "ny_pa_adj_gt1": rep["ny_pa_adjusted_rr_above_1_count"],
        "ny_pa_flips": rep["ny_pa_causes_flipped_positive_after_adjustment"],
    }, indent=2))
    raise SystemExit(0 if rep["bundle_verification"]["ok"] else 1)

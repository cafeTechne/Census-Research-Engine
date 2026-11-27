#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 183: Pre-registered WONDER 2018-2022 county alcohol-induced & unintentional injury BYM2 (B3) + E-value QBA."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.bias_analysis import e_value
from census.boundaries import join_boundaries
from census.disease_mapping import disease_map
from census.replicate import fetch_vre
from census.report_tables import results_bundle, verify_bundle
from census.spatial import spatial_weights

PROTOCOL = {
    "round": 183,
    "title": "WONDER 2018-2022 County Alcohol-Induced & Unintentional Injury Mortality: BYM2 (B3) Mapping & E-Value QBA",
    "primary_states": ["26", "39"],
    "replication_states": ["36", "42"],
    "causes": ["alcohol_induced", "unintentional_injury"],
    "exceedance_threshold": 1.20,
    "bym2_method": "B3",
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _run_region_cause(states: List[str], cause: str) -> Dict[str, Any]:
    raw = pd.read_csv(f"external_data/wonder/ucd/2018-2022/county/{cause}.tsv", sep="\t", dtype=str)
    raw = raw[raw["Notes"].isna() & raw["County Code"].notna()].copy()
    raw["GEOID"] = raw["County Code"].str.zfill(5)
    raw = raw[raw["GEOID"].str[:2].isin(states)].copy()
    raw["deaths"] = pd.to_numeric(raw["Deaths"], errors="coerce")
    raw["population"] = pd.to_numeric(raw["Population"], errors="coerce")
    wdf = raw.dropna(subset=["deaths", "population"])
    wdf = wdf[(wdf["deaths"] >= 10) & (wdf["population"] > 0)][["GEOID", "deaths", "population"]].reset_index(drop=True)

    pov = pd.concat([fetch_vre("B17001", 2024, "county", state_code=st) for st in states], ignore_index=True)
    num = pov[pov["variable"] == "B17001_002"].set_index("GEOID")["estimate"]
    den = pov[pov["variable"] == "B17001_001"].set_index("GEOID")["estimate"]
    common = sorted(set(num.index) & set(den.index))
    pdf = pd.DataFrame({"GEOID": common, "poverty_pct": 100.0 * num.loc[common].to_numpy(float) / den.loc[common].to_numpy(float)})

    df = wdf.merge(pdf, on="GEOID", how="inner")
    pooled_rate = float(df["deaths"].sum() / df["population"].sum())
    df["expected"] = df["population"] * pooled_rate
    df["smr_raw"] = df["deaths"] / df["expected"]

    gdf = join_boundaries(df, level="county", year=2022)
    gdf = gdf.dropna(subset=["deaths", "expected", "poverty_pct"]).sort_values("GEOID").reset_index(drop=True)
    df = pd.DataFrame(gdf.drop(columns=["geometry"]))
    W = spatial_weights(gdf.to_crs(5070), kind="knn", k=5)
    sym = W.sparse + W.sparse.T
    rows_i, cols_j = sym.nonzero()
    edges = sorted({(int(i), int(j)) for i, j in zip(rows_i, cols_j) if i < j})

    res = disease_map(df, "deaths", "expected", edges, covariates=["poverty_pct"],
                      threshold=PROTOCOL["exceedance_threshold"], method=PROTOCOL["bym2_method"])
    tbl = res["table"]
    rr_col = next((c for c in tbl.columns if c in ("rr", "relative_risk", "estimate")), tbl.columns[1])
    exc_col = next((c for c in tbl.columns if "exceed" in c or "prob" in c), None)

    q75, q25 = df["poverty_pct"].quantile(0.75), df["poverty_pct"].quantile(0.25)
    hi, lo = df[df["poverty_pct"] >= q75], df[df["poverty_pct"] <= q25]
    rr = float((hi["deaths"].sum() / hi["population"].sum()) / (lo["deaths"].sum() / lo["population"].sum()))
    se = float(np.sqrt(1.0 / hi["deaths"].sum() + 1.0 / lo["deaths"].sum()))
    rr_lo, rr_hi = float(np.exp(np.log(rr) - 1.6448536 * se)), float(np.exp(np.log(rr) + 1.6448536 * se))
    ev = e_value(rr, lower=rr_lo, upper=rr_hi, measure="rr")

    return {
        "states": states,
        "cause": cause,
        "n_counties": int(len(df)),
        "bym2_sigma": float(res["sigma"]),
        "bym2_phi": float(res["phi"]),
        "bym2_validated": bool(res["validated"]),
        "raw_smr_iqr": float(df["smr_raw"].quantile(0.75) - df["smr_raw"].quantile(0.25)),
        "smoothed_rr_iqr": float(tbl[rr_col].quantile(0.75) - tbl[rr_col].quantile(0.25)),
        "high_exceedance_counties_p80": int((tbl[exc_col] >= 0.80).sum()) if exc_col else 0,
        "q4_vs_q1_poverty_rr": rr,
        "q4_vs_q1_rr_ci90": [rr_lo, rr_hi],
        "e_value_point": float(ev["e_value"]),
        "e_value_limit": float(ev["e_value_limit"]),
    }


def main() -> None:
    out_dir = Path("studies_output/r183_wonder_alcohol_injury")
    bundle_dir = out_dir / "bundle"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        f"{reg}_{cause}": _run_region_cause(states, cause)
        for reg, states in (("MI_OH", PROTOCOL["primary_states"]), ("NY_PA", PROTOCOL["replication_states"]))
        for cause in PROTOCOL["causes"]
    }
    methods_md = (
        "# Round 183: County Alcohol-Induced & Unintentional Injury Mortality (2018-2022) BYM2 & E-Value QBA\n\n"
        f"- **Protocol SHA-256:** `{protocol_hash()}`\n"
        "- **Methods:** BYM2 (B3) spatial smoothing with symmetric 5-NN graph in EPSG:5070 and E-value QBA.\n"
    )
    refs_bib = (
        "@article{riebler2016,\n  title={An intuitive Bayesian spatial model for disease mapping that accounts for scaling},\n"
        "  author={Riebler, Andrea and S{\\o}rbye, Sigrunn H and Simpson, Daniel and Rue, H{\\aa}vard},\n"
        "  journal={Statistical Methods in Medical Research}, year={2016}\n}\n"
        "@article{vanderweele2017,\n  title={Sensitivity Analysis in Observational Research: Introducing the E-Value},\n"
        "  author={VanderWeele, Tyler J and Ding, Peng}, journal={Annals of Internal Medicine}, year={2017}\n}\n"
    )
    results_bundle(
        str(bundle_dir),
        methods=methods_md,
        results=results,
        provenance={"protocol_sha256": protocol_hash()},
        citation="CDC WONDER UCD 2018-2022 (local manual export); ACS 5-Year 2020-2024 B17001 VRE.",
        references={"references.bib": refs_bib},
    )
    verification = verify_bundle(str(bundle_dir))
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "results": results,
        "bundle_verification": verification,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

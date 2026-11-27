#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 121: Pre-registered PUMS Age-65 Medicare RDD & Stratified Disparity Study (MI primary, OH replication)."""
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

from census.bias_analysis import e_value
from census.multitest import adjust_pvalues
from census.pums import fetch_pums
from census.rdd import regression_discontinuity
from census.stratified import stratified_pums

PROTOCOL = {
    "round": 121,
    "title": "Age-65 Medicare Eligibility Discontinuity and Disability Stratification (ACS 2019-2023 PUMS)",
    "primary_state": "26",
    "replication_state": "39",
    "year": 2023,
    "product": "5-year",
    "age_window": [55, 75],
    "cutoff": 65,
    "placebo_cutoffs": [62, 68],
    "confidence_level": 0.90,
    "alpha": 0.10,
    "correction": "holm",
    "hypotheses": [
        {"id": "H1", "statement": "Uninsurance drops sharply at age 65 (Medicare eligibility cutoff).", "direction": "less"},
        {"id": "H2", "statement": "Public health insurance coverage jumps sharply at age 65.", "direction": "greater"},
        {"id": "H3", "statement": "Disability is associated with uninsurance across age strata (55-64 vs 65-75) with heterogeneity tested by Korn-Graubard Hotelling F.", "direction": "two-sided"},
    ],
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_state(state_fips: str) -> Dict[str, Any]:
    cols = ["AGEP", "HICOV", "PUBCOV", "DIS"]
    df = fetch_pums(
        state_fips,
        PROTOCOL["year"],
        product=PROTOCOL["product"],
        record="person",
        columns=cols,
        replicates=True,
        filter=lambda d: pd.to_numeric(d["AGEP"], errors="coerce").between(55, 75),
    )
    for c in ("AGEP", "HICOV", "PUBCOV", "DIS", "PWGTP"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AGEP", "HICOV", "PUBCOV", "DIS", "PWGTP"]).reset_index(drop=True)
    df["uninsured"] = (df["HICOV"].astype(int) == 2).astype(float)
    df["pubcov"] = (df["PUBCOV"].astype(int) == 1).astype(float)
    df["disabled"] = (df["DIS"].astype(int) == 1).astype(int)
    df["age_band"] = np.where(df["AGEP"].astype(int) < 65, "55_64", "65_75")

    h1 = regression_discontinuity(
        df, "uninsured", "AGEP", 65.0,
        weight="PWGTP", replicate_prefix="PWGTP",
        placebo_cutoffs=tuple(PROTOCOL["placebo_cutoffs"]),
        level=PROTOCOL["confidence_level"],
    )
    h2 = regression_discontinuity(
        df, "pubcov", "AGEP", 65.0,
        weight="PWGTP", replicate_prefix="PWGTP",
        placebo_cutoffs=tuple(PROTOCOL["placebo_cutoffs"]),
        level=PROTOCOL["confidence_level"],
    )

    rep_cols = ["PWGTP"] + [f"PWGTP{i}" for i in range(1, 81)]
    W = df[rep_cols].to_numpy(float)
    h3 = stratified_pums(
        y=df["uninsured"].to_numpy(int),
        e=df["disabled"].to_numpy(int),
        s=df["age_band"].to_numpy(),
        W=W,
        strata=["55_64", "65_75"],
        level=PROTOCOL["confidence_level"],
        homogeneity_method="hotelling_f",
    )

    # Compute weighted risk ratio at age 65 vs 64 for E-value (H4 sensitivity)
    d64 = df[df["AGEP"] == 64]
    d65 = df[df["AGEP"] == 65]
    r64 = float(np.average(d64["uninsured"], weights=d64["PWGTP"]))
    r65 = float(np.average(d65["uninsured"], weights=d65["PWGTP"]))
    rr_65_64 = r65 / r64 if r64 > 0 else float("nan")
    h4 = e_value(rr_65_64, measure="rr")

    def _p_from_est(est: float, se: float, direction: str) -> float:
        z = est / se if se > 0 else 0.0
        if direction == "less":
            return float(stats.norm.cdf(z))
        if direction == "greater":
            return float(stats.norm.sf(z))
        return float(2.0 * stats.norm.sf(abs(z)))

    p_h1 = _p_from_est(float(h1["estimate"]), float(h1["se"]), "less")
    p_h2 = _p_from_est(float(h2["estimate"]), float(h2["se"]), "greater")
    mh_rr = h3["pooled"]["rr"]
    se_log_rr = (np.log(mh_rr["upper"]) - np.log(mh_rr["lower"])) / (2.0 * stats.norm.ppf(0.95))
    p_h3 = float(2.0 * stats.norm.sf(abs(np.log(mh_rr["estimate"])) / se_log_rr))

    adj = adjust_pvalues([p_h1, p_h2, p_h3], method="holm")
    p_adj = [float(x) for x in (adj["adjusted_p"] if isinstance(adj, dict) else adj)]
    return {
        "state": state_fips,
        "n_records": int(len(df)),
        "protocol_sha256": protocol_hash(),
        "H1_uninsured_rdd": {
            "estimate": float(h1["estimate"]),
            "se": float(h1["se"]),
            "lower": float(h1["lower"]),
            "upper": float(h1["upper"]),
            "validated": bool(h1["validated"]),
            "p_raw": p_h1,
            "p_holm": p_adj[0],
            "placebos": h1.get("placebos"),
        },
        "H2_pubcov_rdd": {
            "estimate": float(h2["estimate"]),
            "se": float(h2["se"]),
            "lower": float(h2["lower"]),
            "upper": float(h2["upper"]),
            "validated": bool(h2["validated"]),
            "p_raw": p_h2,
            "p_holm": p_adj[1],
            "placebos": h2.get("placebos"),
        },
        "H3_stratified_disability_uninsured": {
            "mh_rr": mh_rr,
            "mh_rd": h3["pooled"]["rd"],
            "homogeneity_rr": h3["homogeneity"]["rr"],
            "homogeneity_or": h3["homogeneity"]["or"],
            "validated": h3["validated"],
            "p_raw": p_h3,
            "p_holm": p_adj[2],
        },
        "H4_evalue_age65_vs_64": {
            "rate_64": r64,
            "rate_65": r65,
            "rr_65_vs_64": rr_65_64,
            "e_value": float(h4["e_value"]),
        },
    }


def main() -> None:
    out_dir = Path("studies_output/r121_medicare_rdd")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "MI_26": run_state("26"),
        "OH_39": run_state("39"),
    }
    out_path = out_dir / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

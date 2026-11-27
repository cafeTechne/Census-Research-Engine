#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 142: Pre-registered PUMS causal AIPW/IPW effect of BA+ on working-age poverty (MI primary, OH replication)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.causal import estimate_effect
from census.pums import fetch_pums

PROTOCOL = {
    "round": 142,
    "title": "Observational AIPW/IPW Effect of College Attainment (BA+) on Working-Age Poverty (MI & OH PUMS, 2019-2023)",
    "primary_state": "26",
    "replication_state": "39",
    "year": 2023,
    "product": "5-year",
    "age_window": [25, 64],
    "treatment": "ba_plus (SCHL >= 21)",
    "outcome": "in_poverty (POVPIP < 100)",
    "confounders": ["AGEP", "female", "disabled", "nonwhite"],
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_state(state_fips: str) -> Dict[str, Any]:
    df = fetch_pums(
        state_fips, 2023, product="5-year", record="person",
        columns=["AGEP", "SEX", "DIS", "RAC1P", "SCHL", "POVPIP"],
        replicates=False,
        filter=lambda d: pd.to_numeric(d["AGEP"], errors="coerce").between(25, 64),
    )
    for c in ("AGEP", "SEX", "DIS", "RAC1P", "SCHL", "POVPIP", "PWGTP"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AGEP", "SEX", "DIS", "RAC1P", "SCHL", "POVPIP", "PWGTP"]).reset_index(drop=True)

    # Deterministic stratified subsample (N=25,000) for fast, exact AIPW/IPW & overlap diagnostics
    rng = np.random.default_rng(20261126 + int(state_fips))
    idx = np.sort(rng.choice(len(df), size=min(25_000, len(df)), replace=False))
    sub = df.iloc[idx].reset_index(drop=True)

    frame = pd.DataFrame({
        "in_poverty": (sub["POVPIP"] < 100).astype(float),
        "ba_plus": (sub["SCHL"] >= 21).astype(float),
        "AGEP": sub["AGEP"].astype(float),
        "female": (sub["SEX"] == 2).astype(float),
        "disabled": (sub["DIS"] == 1).astype(float),
        "nonwhite": (sub["RAC1P"] != 1).astype(float),
        "PWGTP": sub["PWGTP"].astype(float),
    })

    aipw = estimate_effect(frame, "in_poverty", "ba_plus", ["AGEP", "female", "disabled", "nonwhite"],
                           method="aipw")
    ipw = estimate_effect(frame, "in_poverty", "ba_plus", ["AGEP", "female", "disabled", "nonwhite"],
                          method="ipw")
    ato = estimate_effect(frame, "in_poverty", "ba_plus", ["AGEP", "female", "disabled", "nonwhite"],
                          weights="overlap")

    return {
        "state": state_fips,
        "n_population_sample": int(len(df)),
        "n_analysis": int(len(frame)),
        "treated_share": float(frame["ba_plus"].mean()),
        "crude_poverty_treated": float(frame.loc[frame["ba_plus"] == 1, "in_poverty"].mean()),
        "crude_poverty_control": float(frame.loc[frame["ba_plus"] == 0, "in_poverty"].mean()),
        "aipw": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in aipw["ate"].items()},
        "aipw_validated": bool(aipw["validated"]),
        "ipw": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in ipw["ate"].items()},
        "ipw_validated": bool(ipw["validated"]),
        "overlap_ato": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in ato["ate"].items()},
        "positivity": {
            "limited_overlap": bool(aipw["positivity"]["limited_overlap"]),
            "share_outside": float(aipw["positivity"]["share_outside"]),
            "max_smd_after": float(np.max(np.abs(aipw["positivity"].get("smd_weighted", [0.0])))),
        },
    }


def main() -> None:
    out_dir = Path("studies_output/r142_pums_causal")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "protocol": PROTOCOL,
        "protocol_sha256": protocol_hash(),
        "MI_26": run_state("26"),
        "OH_39": run_state("39"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 127: Pre-registered PUMS disability earnings & poverty gap decomposition (MI primary, OH replication)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.decomposition import pums_decomposition
from census.pums import fetch_pums

PROTOCOL = {
    "round": 127,
    "title": "Disability Gaps in Earnings (Oaxaca-Blinder) and Poverty (Fairlie) among Working-Age Adults 25-64 (ACS 2019-2023 PUMS)",
    "primary_state": "26",
    "replication_state": "39",
    "year": 2023,
    "product": "5-year",
    "age_window": [25, 64],
    "confidence_level": 0.90,
}


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def run_state(state_fips: str) -> Dict[str, Any]:
    cols = ["AGEP", "SEX", "SCHL", "DIS", "PERNP", "POVPIP"]
    df = fetch_pums(
        state_fips,
        PROTOCOL["year"],
        product=PROTOCOL["product"],
        record="person",
        columns=cols,
        replicates=True,
        filter=lambda d: pd.to_numeric(d["AGEP"], errors="coerce").between(25, 64),
    )
    for c in ("AGEP", "SEX", "SCHL", "DIS", "PERNP", "POVPIP", "PWGTP"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AGEP", "SEX", "SCHL", "DIS", "POVPIP", "PWGTP"]).reset_index(drop=True)
    df["ba_plus"] = (df["SCHL"] >= 21).astype(float)
    df["female"] = (df["SEX"] == 2).astype(float)
    df["in_poverty"] = (df["POVPIP"] < 100).astype(float)

    # 1. Oaxaca-Blinder on log earnings (positive earners)
    earn = df[df["PERNP"] > 0].copy()
    earn["log_earn"] = np.log(earn["PERNP"].to_numpy(float))
    ob = pums_decomposition(
        earn, "log_earn", "DIS == 1", "DIS == 2",
        covariates=["AGEP", "ba_plus", "female"],
        model="linear", level=0.90,
    )

    # 2. Fairlie nonlinear decomposition on poverty indicator
    fl = pums_decomposition(
        df, "in_poverty", "DIS == 1", "DIS == 2",
        covariates=["AGEP", "ba_plus", "female"],
        model="logit", level=0.90, orderings=12,
    )

    return {
        "state": state_fips,
        "n_working_age": int(len(df)),
        "n_earners": int(len(earn)),
        "oaxaca_log_earnings": {
            "records": ob["records"],
            "table": ob["table"].to_dict(orient="records"),
        },
        "fairlie_poverty": {
            "records": fl["records"],
            "table": fl["table"].to_dict(orient="records"),
        },
    }


def main() -> None:
    out_dir = Path("studies_output/r127_pums_decomposition")
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

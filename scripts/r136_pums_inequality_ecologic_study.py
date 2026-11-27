#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 136: Pre-registered PUMS income inequality & PUMA ecologic fallacy study (MI primary, OH replication)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from census.ecologic import ecologic_check
from census.pums import fetch_pums
from census.pums_inequality import pums_inequality

PROTOCOL = {
    "round": 136,
    "title": "PUMS Earnings Inequality (Gini, P90/P10, Atkinson) & PUMA Ecologic Fallacy Decomposition (MI & OH, 2019-2023)",
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
    df = fetch_pums(
        state_fips, 2023, product="5-year", record="person",
        columns=["AGEP", "DIS", "PERNP", "POVPIP", "PUMA"],
        replicates=True,
        filter=lambda d: pd.to_numeric(d["AGEP"], errors="coerce").between(25, 64),
    )
    for c in ("AGEP", "DIS", "PERNP", "POVPIP", "PWGTP"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AGEP", "DIS", "POVPIP", "PUMA", "PWGTP"]).reset_index(drop=True)

    # 1. Validated earnings inequality among positive earners (overall + by disability)
    earn = df[df["PERNP"] > 0].copy()
    ineq = pums_inequality(earn, "PERNP", weight="person")
    ineq_by_dis = pums_inequality(earn, "PERNP", weight="person", by="DIS == 1")

    # 2. PUMA within / between / contextual logit decomposition of poverty on disability
    rep_cols = ["PWGTP"] + [f"PWGTP{i}" for i in range(1, 81)]
    W = df[rep_cols].to_numpy(float)
    y = (df["POVPIP"] < 100).to_numpy(int)
    x = (df["DIS"] == 1).to_numpy(float)
    area = df["PUMA"].astype(str).to_numpy()
    eco = ecologic_check(y, x, area, W, binary=True, level=0.90)

    return {
        "state": state_fips,
        "n_working_age": int(len(df)),
        "n_earners": int(len(earn)),
        "n_pumas": int(df["PUMA"].nunique()),
        "inequality_overall": ineq["table"].to_dict(orient="records"),
        "inequality_gini_diff_disability": ineq_by_dis.get("gini_difference"),
        "ecologic_logit": eco.get("logit"),
        "ecologic_fuller": eco.get("ecologic_fuller"),
    }


def main() -> None:
    out_dir = Path("studies_output/r136_pums_ineq_ecologic")
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

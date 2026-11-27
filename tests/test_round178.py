# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 178 tests: WONDER 2018-2022 county kidney disease & firearm BYM2 (B3) + E-value QBA invariants."""
import json
from pathlib import Path

from scripts.r178_wonder_kidney_firearm_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r178_kidney_firearm_study_and_verified_bundle():
    path = ROOT / "studies_output/r178_wonder_kidney_firearm/summary.json"
    assert path.exists(), "Run scripts/r178_wonder_kidney_firearm_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    assert data["bundle_verification"]["ok"] is True
    assert data["bundle_verification"]["errors"] == []
    for key in ("MI_OH_kidney_disease", "MI_OH_firearm", "NY_PA_kidney_disease", "NY_PA_firearm"):
        rec = data["results"][key]
        assert rec["n_counties"] >= 90
        assert rec["bym2_validated"] is True
        assert rec["smoothed_rr_iqr"] <= rec["raw_smr_iqr"]
        assert rec["e_value_point"] > 1.0

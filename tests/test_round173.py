# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 173 tests: WONDER 2018-2022 county CLRD & liver disease BYM2 (B3) + E-value QBA invariants."""
import json
from pathlib import Path

from scripts.r173_wonder_clrd_liver_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r173_clrd_liver_study_and_verified_bundle():
    path = ROOT / "studies_output/r173_wonder_clrd_liver/summary.json"
    assert path.exists(), "Run scripts/r173_wonder_clrd_liver_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    assert data["bundle_verification"]["ok"] is True
    assert data["bundle_verification"]["errors"] == []
    for key in ("MI_OH_clrd", "MI_OH_liver_disease", "NY_PA_clrd", "NY_PA_liver_disease"):
        rec = data["results"][key]
        assert rec["n_counties"] >= 100
        assert rec["bym2_validated"] is True
        assert rec["smoothed_rr_iqr"] <= rec["raw_smr_iqr"]
        assert rec["e_value_point"] > 1.0

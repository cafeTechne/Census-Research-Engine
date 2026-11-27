# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 183 tests: WONDER 2018-2022 county alcohol-induced & unintentional injury BYM2 (B3) + E-value QBA."""
import json
from pathlib import Path

from scripts.r183_wonder_alcohol_injury_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r183_alcohol_injury_study_and_verified_bundle():
    path = ROOT / "studies_output/r183_wonder_alcohol_injury/summary.json"
    assert path.exists(), "Run scripts/r183_wonder_alcohol_injury_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    assert data["bundle_verification"]["ok"] is True
    assert data["bundle_verification"]["errors"] == []
    for key in ("MI_OH_alcohol_induced", "MI_OH_unintentional_injury", "NY_PA_alcohol_induced", "NY_PA_unintentional_injury"):
        rec = data["results"][key]
        assert rec["n_counties"] >= 90
        assert rec["bym2_validated"] is True
        assert rec["smoothed_rr_iqr"] <= rec["raw_smr_iqr"] + 0.02
        assert rec["q4_vs_q1_poverty_rr"] > 1.0
        assert rec["e_value_point"] > 1.0

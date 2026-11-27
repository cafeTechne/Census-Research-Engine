# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 156 tests: end-to-end live Layer B -> Layer A stroke mortality study & bundle verification."""
import json
from pathlib import Path

from scripts.r156_layer_b_to_layer_a_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r156_end_to_end_study_and_verified_bundle():
    path = ROOT / "studies_output/r156_layer_a_stroke/summary.json"
    assert path.exists(), "Run scripts/r156_layer_b_to_layer_a_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    assert data["bundle_verification"]["ok"] is True
    assert data["bundle_verification"]["errors"] == []
    assert data["upstream_layer_b_provenance"]["layer_b_seed_sha256"]
    for key in ("MI_OH", "NY_PA"):
        rec = data["results"][key]
        assert rec["bym2_validated"] is True
        assert rec["smoothed_rr_iqr"] <= rec["raw_smr_iqr"]
        assert rec["e_value_point"] > 1.0

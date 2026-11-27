# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 139 tests: KWW county poverty ranking & Holm state-reference comparison invariants."""
import json
from pathlib import Path

from scripts.r139_county_ranking_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r139_summary_invariants():
    path = ROOT / "studies_output/r139_county_ranking/summary.json"
    assert path.exists(), "Run scripts/r139_county_ranking_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    expected_counts = {"26": 83, "36": 62, "39": 88, "42": 67}
    for st, n_exp in expected_counts.items():
        rec = data["states"][st]
        assert rec["n_counties"] == n_exp
        assert rec["median_joint_rank_width"] >= rec["median_individual_rank_width"] > 0
        assert 5.0 < rec["reference_rate"] < 25.0
        assert 0 <= rec["surely_top_decile_counties"] <= n_exp
        assert 0 < rec["counties_differing_from_state_holm"] < n_exp

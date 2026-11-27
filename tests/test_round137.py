# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 137 tests: spatial Spearman effective-n & SCPC vs HC3 inference invariants."""
import json
from pathlib import Path

from scripts.r137_spatial_inference_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r137_summary_invariants():
    path = ROOT / "studies_output/r137_spatial_inference/summary.json"
    assert path.exists(), "Run scripts/r137_spatial_inference_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    for region, n_exp in (("MI_NY", 145), ("OH_PA", 155)):
        rec = data[region]
        assert rec["n_counties"] == n_exp
        assert len(rec["spatial_spearman"]) == 1
        sp = rec["spatial_spearman"][0]
        assert sp["estimate"] < 0.0
        slope = rec["ba_plus_slope"]
        assert slope["estimate"] < 0.0
        assert slope["scpc_lower"] < slope["estimate"] < slope["scpc_upper"]
        assert slope["width_ratio_scpc_vs_hc3"] > 0.5
        assert slope["validated"] is True

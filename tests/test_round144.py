# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 144 tests: WONDER 2018-2022 county mortality BYM2 (B3) & E-value QBA invariants."""
import json
from pathlib import Path

from scripts.r144_wonder_bym2_qba_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r144_summary_invariants():
    path = ROOT / "studies_output/r144_wonder_bym2_qba/summary.json"
    assert path.exists(), "Run scripts/r144_wonder_bym2_qba_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    for key in ("MI_OH_heart_disease", "MI_OH_drug_overdose", "NY_PA_heart_disease", "NY_PA_drug_overdose"):
        rec = data["results"][key]
        assert rec["n_counties"] >= 100
        assert rec["n_edges"] >= 150
        assert rec["bym2_validated"] is True
        assert rec["bym2_sigma"] > 0.0
        assert 0.0 <= rec["bym2_phi"] <= 1.0
        assert rec["smoothed_rr_iqr"] <= rec["raw_smr_iqr"]
        assert rec["q4_vs_q1_poverty_rr"] > (1.2 if "drug_overdose" in key else 0.8)
        assert rec["e_value_point"] > 1.0
        assert rec["e_value_ci"] >= 1.0

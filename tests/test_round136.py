# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 136 tests: PUMS earnings inequality & PUMA ecologic fallacy decomposition invariants."""
import json
from pathlib import Path

from scripts.r136_pums_inequality_ecologic_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r136_summary_invariants():
    path = ROOT / "studies_output/r136_pums_ineq_ecologic/summary.json"
    assert path.exists(), "Run scripts/r136_pums_inequality_ecologic_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    for key in ("MI_26", "OH_39"):
        rec = data[key]
        assert rec["n_working_age"] > 200_000
        assert rec["n_earners"] > 150_000
        assert rec["n_pumas"] >= 50
        measures = {r["measure"]: r for r in rec["inequality_overall"]}
        assert 0.30 < measures["gini"]["estimate"] < 0.65
        assert rec["inequality_gini_diff_disability"]["validated"] is True
        assert rec["ecologic_logit"] is not None
        assert "within" in rec["ecologic_logit"] and "between" in rec["ecologic_logit"]
        assert rec["ecologic_logit"]["within"]["estimate"] > 0.0

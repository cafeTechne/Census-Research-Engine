# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 142 tests: PUMS causal AIPW/IPW effect of BA+ on working-age poverty & positivity invariants."""
import json
from pathlib import Path

from scripts.r142_pums_causal_study import protocol_hash

ROOT = Path(__file__).resolve().parents[1]


def test_r142_summary_invariants():
    path = ROOT / "studies_output/r142_pums_causal/summary.json"
    assert path.exists(), "Run scripts/r142_pums_causal_study.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["protocol_sha256"] == protocol_hash()
    for key in ("MI_26", "OH_39"):
        rec = data[key]
        assert rec["n_analysis"] == 25_000
        assert rec["aipw_validated"] is True
        assert rec["aipw"]["estimate"] < -0.05
        assert rec["aipw"]["lower"] < rec["aipw"]["estimate"] < rec["aipw"]["upper"] < 0.0
        assert abs(rec["aipw"]["estimate"] - rec["ipw"]["estimate"]) < 0.02
        assert rec["positivity"]["limited_overlap"] is False

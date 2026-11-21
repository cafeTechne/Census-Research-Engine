# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 69: replication D (Monnat 2018 Model 4 analogue) and spatial-error coverage on national counties."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REP = json.loads((ROOT/"docs/audits/r69_monnat_replication.json").read_text())
SIM = json.loads((ROOT/"docs/audits/r69_county_sem_validation.json").read_text())


def test_outcomes_recorded():
    assert REP["criterion_commit"] == SIM["criterion_commit"] == "20a4c13"
    e = REP["primary"]["slopes"]["econ_index"]
    assert REP["outcome"] == "replicated" and e["lower"] <= 9.62 <= e["upper"] and .67 <= e["ratio"] <= 1.5
    assert REP["counties_all"] == 3105 and REP["primary"]["n"] == 2459
    assert SIM["passed"] and all(c["coverage"] >= .86 for c in SIM["cells"])
    assert "replicated" in (ROOT/"docs/studies/r69_replication_monnat.md").read_text()

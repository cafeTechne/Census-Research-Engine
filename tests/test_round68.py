# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 68: replication E, headline shares of life-expectancy variation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT/"docs/audits/r68_le_variance_replication.json").read_text())


def test_outcome_recorded():
    assert R["criterion_commit"] == "110c22e" and R["outcome"] == "replicated"
    assert (R["tracts"], R["counties"]) == (65662, 3020) and R["primary"]["converged"]
    s = R["primary"]["shares"]
    assert all(abs(s[k]-R["published"][k]) <= 5 for k in s) and s["tract"] > s["state"] > s["county"]
    assert "replicated" in (ROOT/"docs/studies/r68_replication_le_variance.md").read_text()

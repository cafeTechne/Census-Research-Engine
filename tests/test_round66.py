# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 66: numeric replications A (CHR county dissimilarity) and B (Census state Gini); segregation on GA/TX/AZ."""
import json
from pathlib import Path

from census import segregation as sg

ROOT = Path(__file__).resolve().parents[1]
NUM = json.loads((ROOT/"docs/audits/r66_numeric_replication.json").read_text())
SIM = json.loads((ROOT/"docs/audits/r66_segregation_geometry_validation.json").read_text())


def test_replication_outcomes_recorded():
    assert NUM["criterion_commit"] == "d30d7ed" and SIM["criterion_commit"] == "d30d7ed"
    a, b = NUM["A"], NUM["B"]
    assert a["replicated"] and a["counties_compared"] == 2055 and a["max_abs_difference"] < 1e-6
    assert b["replicated"] and b["contained"] == 10 and b["median_abs_difference"] <= .005
    for doc in ("r66_replication_chr_segregation.md", "r66_replication_state_gini.md"):
        assert "replicated" in (ROOT/"docs/studies"/doc).read_text()


def test_ranges_follow_the_geometry_audit():
    p = SIM["passed"]
    assert not p["D_bc"]["passed"] and p["D_bc"]["failed_bins"] == [["black2_TX", "[.75, 1)"]]
    assert p["I_bc"]["passed"] and p["H_bc"]["passed"]
    assert sg.REALISTIC_RANGES[("dissimilarity", "bias_corrected", 2)] == (.15, .75)
    assert sg.REALISTIC_RANGES[("isolation", "bias_corrected", 2)][1] == float("inf")
    assert sg.REALISTIC_RANGES[("theil_h", "bias_corrected", 2)] == (0., 1.0)


def test_rule_text_mirrored():
    for path in ("docs/agent_protocol.md", "mcp_server.py", "docs/recipes/segregation.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert ("Round 66" in text or "50/52/66" in text) and ".75" in text

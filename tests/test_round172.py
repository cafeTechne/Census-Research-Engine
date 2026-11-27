# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 172 tests: census/concordance.py modularization into concordance_overrides.py & re-export parity."""
from pathlib import Path

from census import concordance, concordance_overrides

ROOT = Path(__file__).resolve().parents[1]


def test_r172_concordance_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/concordance.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1050, f"Expected concordance.py < 1050 lines, got {n_lines}"
    for name in (
        "build_rule_evidence",
        "rule_guardrail_errors",
        "validate_rule_row",
        "rule_cross_conflicts",
        "validate_rule_file",
        "validate_all_crosswalks",
    ):
        assert getattr(concordance, name) is getattr(concordance_overrides, name)

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 151 tests: census/validation.py modularization into validation_extended.py & symbol parity."""
from pathlib import Path

from census import validation, validation_extended

ROOT = Path(__file__).resolve().parents[1]


def test_r151_validation_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/validation.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1950, f"Expected validation.py < 1950 lines, got {n_lines}"
    for name in (
        "_cp_items",
        "check_f6_cp_inflation",
        "check_f7_cp_significance",
        "check_f8_county_sums",
        "check_f10_summary_file",
        "check_f11_decennial_invariants",
    ):
        assert getattr(validation, name) is getattr(validation_extended, name)

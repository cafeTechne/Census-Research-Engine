# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 181 tests: census/pums.py modularization into pums_stats.py & re-export parity."""
from pathlib import Path

from census import pums, pums_stats

ROOT = Path(__file__).resolve().parents[1]


def test_r181_pums_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/pums.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 950, f"Expected pums.py < 950 lines, got {n_lines}"
    for name in ("pums_regression", "puma_vintage", "puma_geoid", "add_puma_geoid", "puma_boundaries"):
        assert getattr(pums, name) is getattr(pums_stats, name)

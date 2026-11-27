# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 167 tests: census/replicate.py modularization into replicate_stats.py & re-export parity."""
from pathlib import Path

from census import replicate, replicate_stats

ROOT = Path(__file__).resolve().parents[1]


def test_r167_replicate_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/replicate.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1300, f"Expected replicate.py < 1300 lines, got {n_lines}"
    for name in ("replicate_sum", "replicate_difference", "replicate_ratio", "replicate_proportion", "replicate_apply", "replicate_frame_to_wide"):
        assert getattr(replicate, name) is getattr(replicate_stats, name)

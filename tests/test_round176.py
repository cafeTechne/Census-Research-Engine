# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 176 tests: census/geo_crosswalk.py modularization into geo_crosswalk_io.py & re-export parity."""
from pathlib import Path

from census import geo_crosswalk, geo_crosswalk_io

ROOT = Path(__file__).resolve().parents[1]


def test_r176_geo_crosswalk_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/geo_crosswalk.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1030, f"Expected geo_crosswalk.py < 1030 lines, got {n_lines}"
    for name in ("harmonize_panel", "_harmonize_split", "_apportion_wide_panel_rows", "_restore_dtypes"):
        assert getattr(geo_crosswalk, name) is getattr(geo_crosswalk_io, name)

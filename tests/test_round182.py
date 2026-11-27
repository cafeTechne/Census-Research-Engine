# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 182 tests: census/health_sources.py modularization into health_sources_io.py & re-export parity."""
from pathlib import Path

from census import health_sources, health_sources_io

ROOT = Path(__file__).resolve().parents[1]


def test_r182_health_sources_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/health_sources.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 880, f"Expected health_sources.py < 880 lines, got {n_lines}"
    for name in ("fetch_chr", "parse_chr", "load_external", "join_external", "_provenance"):
        assert getattr(health_sources, name) is getattr(health_sources_io, name)

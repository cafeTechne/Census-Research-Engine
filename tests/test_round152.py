# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 152 tests: census/pipeline.py modularization into pipeline_replay.py & symbol parity."""
from pathlib import Path

from census import pipeline, pipeline_replay

ROOT = Path(__file__).resolve().parents[1]


def test_r152_pipeline_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/pipeline.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1680, f"Expected pipeline.py < 1680 lines, got {n_lines}"
    for name in ("diff_frames", "_verify_outputs", "replay_extraction"):
        assert getattr(pipeline, name) is getattr(pipeline_replay, name)

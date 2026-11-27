# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 122 regression tests: multi-release DiD + HKSJ 4-state pooling protocol integrity."""
import importlib.util
from pathlib import Path

from census.evidence import combine_estimates

ROOT = Path(__file__).resolve().parents[1]


def test_r122_protocol_hash_is_deterministic():
    spec = importlib.util.spec_from_file_location("r122", ROOT / "scripts/r122_disparity_did_study.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    h1 = mod.protocol_hash()
    h2 = mod.protocol_hash()
    assert len(h1) == 64 and h1 == h2


def test_r122_four_state_hksj_pooling_is_validated():
    ests = [-0.167, -0.779, -0.392, -0.432]
    ses = [0.339, 0.355, 0.359, 0.298]
    out = combine_estimates(ests, ses, method="hksj", level=0.90)
    assert out["validated"] is True
    assert out["pooled"]["lower"] < out["pooled"]["estimate"] < out["pooled"]["upper"] < 0.0

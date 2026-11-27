# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 149 tests: workflows_inference.py modularization into workflows_reporting.py & re-export parity."""
from pathlib import Path

from census import workflows_inference, workflows_reporting

ROOT = Path(__file__).resolve().parents[1]


def test_r149_workflows_inference_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/workflows_inference.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1600, f"Expected workflows_inference.py < 1600 lines, got {n_lines}"
    for name in (
        "make_figure",
        "make_table",
        "make_results_bundle",
        "save_json",
        "list_health_sources",
        "run_variant",
        "create_manifest",
        "run_manifest",
        "verify_bundle",
        "list_manifest_methods",
    ):
        assert getattr(workflows_inference, name) is getattr(workflows_reporting, name)

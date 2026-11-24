# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 116 tests: README and recipe count/discoverability parity."""
from pathlib import Path

from census.manifest.methods import METHODS

ROOT = Path(__file__).resolve().parents[1]


def test_readme_and_preregistered_recipe_counts_match_engine():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "81 MCP tools" in readme
    assert f"{len(METHODS)} pre-registered manifest methods" in readme
    assert "40 offline-tested agent routing contracts" in readme

    recipe = (ROOT / "docs/recipes/preregistered.md").read_text(encoding="utf-8")
    for m in ("estimate_effect", "spatial_scan", "stratified", "designation", "agreement",
              "rdd", "disease_map", "joinpoint", "demography",
              "difference_in_differences", "interrupted_series", "combine_estimates", "bias_analysis"):
        assert m in recipe

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 153 tests: 3 new recipes (32 total) and offline Layer B pipeline."""
from pathlib import Path

from census import recipes

ROOT = Path(__file__).resolve().parents[1]


def test_r153_new_recipes_registered_and_readable():
    assert len(recipes.RECIPES) >= 32
    for name in ("pums_inequality_ecologic", "sae_temporal_pooling", "layer_b_offline_corpus"):
        assert name in recipes.RECIPES
        res = recipes.get_recipe(name)
        assert res["success"] is True
        assert (ROOT / "docs/recipes" / f"{name}.md").exists()

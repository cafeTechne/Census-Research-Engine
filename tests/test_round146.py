# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 146 tests: new Layer B -> Layer A integration & verification recipes."""
from pathlib import Path

from census import recipes

ROOT = Path(__file__).resolve().parents[1]


def test_r146_new_recipes_registered_and_readable():
    for name in ("literature_to_preregistration", "publication_verification", "spatial_mortality_qba"):
        assert name in recipes.RECIPES
        res = recipes.get_recipe(name)
        assert res["success"] is True
        assert len(res["steps"]) > 200
        assert (ROOT / "docs/recipes" / f"{name}.md").exists()


def test_r146_all_recipes_have_markdown_files():
    for name in recipes.RECIPES:
        assert (ROOT / "docs/recipes" / f"{name}.md").exists(), f"Missing recipe markdown for {name}"

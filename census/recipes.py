# SPDX-License-Identifier: AGPL-3.0-or-later
"""Workflow recipes (PLAN_ROUND_8 J3): short numbered steps an agent can follow
instead of planning from scratch. Recipes are Markdown files in docs/recipes/."""

import os
from typing import Any, Dict, Literal, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPE_DIR = os.path.join(ROOT, "docs", "recipes")

RECIPES: Dict[str, str] = {
    "composite_index": "Composite (deprivation) index with score intervals, quintile stability and alpha (Round 36)",
    "rank_areas": "Rank areas with rank intervals, and compare each area with the state value (Round 34)",
    "rank_methods": "Rank and partial correlations and rank comparisons of groups with ACS error (Round 33)",
    "pums_tests": "Survey-correct tests and intervals on PUMS microdata: tables, odds ratios, means, medians (Round 32)",
    "group_comparison": "Compare an area outcome across groups of areas: t-test, ANOVA, ANCOVA, interactions (Round 31)",
    "segregation": "County residential segregation from tract counts with strict ACS replicate uncertainty",
    "health_inequality": "Area health inequality indices and indirectly standardized ratios with ACS uncertainty",
    "compare_counties": "Compare a rate between two counties in one release",
    "tract_trend": "Trend in a tract or county rate using non-overlapping releases",
    "regression_sampling_error": "Regression whose SEs include ACS sampling error",
    "small_area": "Small-area ACS estimates (Fay-Herriot) and descriptive event-count smoothing (EB)",
    "preregistered": "Pre-registered (manifest) confirmatory analysis",
    "decennial_counts": "Use 2020 Census counts (P.L. 94-171, DHC) without inventing margins of error",
    "external_health_outcome": "Health outcome from CDC PLACES, USALEEP, County Health Rankings or WONDER, "
                               "without circularity; binomial counts with denominator trials and robust (HC3) SEs",
}

RecipeName = Literal[
    "compare_counties", "tract_trend", "regression_sampling_error", "small_area", "preregistered",
    "decennial_counts", "external_health_outcome", "health_inequality", "segregation", "group_comparison", "pums_tests", "rank_methods", "rank_areas", "composite_index",
]


def get_recipe(name: Optional[RecipeName] = None) -> Dict[str, Any]:
    """Return numbered steps for a standard analysis; omit name to list recipes.

    Args:
        name: compare_counties, tract_trend, regression_sampling_error,
            small_area, preregistered, decennial_counts, external_health_outcome, health_inequality, segregation,
            group_comparison, pums_tests, rank_methods,
            rank_areas, or composite_index.

    Example: get_recipe(name="compare_counties")
    """
    if not name:
        return {
            "success": True,
            "summary": f"{len(RECIPES)} recipes available.",
            "next_step": "get_recipe(name=...) with one of the names in recipes",
            "recipes": [{"name": k, "description": v} for k, v in RECIPES.items()],
        }
    key = str(name).strip().lower()
    if key not in RECIPES:
        return {
            "success": False,
            "error_code": "INVALID_INPUT",
            "error": f"Unknown recipe '{name}'.",
            "summary": f"Unknown recipe '{name}'.",
            "fix": f"Use one of: {', '.join(RECIPES)}.",
            "next_step": "get_recipe() to list recipes",
        }
    with open(os.path.join(RECIPE_DIR, f"{key}.md"), encoding="utf-8") as f:
        text = f.read()
    return {
        "success": True,
        "summary": RECIPES[key] + ".",
        "next_step": "follow step 1 of the recipe",
        "name": key,
        "steps": text,
    }

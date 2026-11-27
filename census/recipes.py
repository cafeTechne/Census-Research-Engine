# SPDX-License-Identifier: AGPL-3.0-or-later
"""Workflow recipes (PLAN_ROUND_8 J3): short numbered steps an agent can follow
instead of planning from scratch. Recipes are Markdown files in docs/recipes/."""

import os
from typing import Any, Dict, Literal, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPE_DIR = os.path.join(ROOT, "docs", "recipes")

RECIPES: Dict[str, str] = {
    "policy_change": "Policy or event effects: difference-in-differences on non-overlapping releases, interrupted "
                     "annual series (Round 75)",
    "custom_geographies": "Neighborhoods and combined areas: mapping tracts to polygons, summed counts with MOEs, "
                          "medians from brackets, 2010/2020 tracts (Round 75)",
    "dollars": "Inflation (R-CPI-U-RS) and place price levels (BEA RPPs) for dollar estimates (Round 75)",
    "spatial_patterns": "Global and local spatial clustering (Moran's I, LISA) and maps with reliability (Round 75)",
    "cross_release": "Variable concordance across releases and reviewed crosswalk decisions (Round 75)",
    "reporting": "Publication tables, maps, codebooks and exploratory results bundles (Round 75); epidemiologic reporting conventions: measure types, ecologic and cross-sectional limits, allocation shares, Table 1 (Round 82)",
    "replications": "Rerun the five published replications (Rounds 66-69) and check the engine still reproduces "
                    "them (Round 74)",
    "context_covariates": "County covariates from other sources (County Business Patterns, ERS county types and "
                          "rural-urban codes, CHR additional measures), joined to an ACS frame (Round 72)",
    "causal": "Treatment effects, instrumental variables and mediation with ACS data, and their assumptions (Round 41)",
    "combine_estimates": "Pool replications (meta-analysis), test equivalence, plan power (Round 38)",
    "agreement": "Agreement between two sources of the same quantity: bias, kappa, limits, concordance (Round 37)",
    "composite_index": "Composite (deprivation) index with score intervals, quintile stability and alpha (Round 36)",
    "rank_areas": "Rank areas with rank intervals, and compare each area with the state value (Round 34)",
    "rank_methods": "Rank and partial correlations and rank comparisons of groups with ACS error (Round 33)",
    "pums_tests": "Survey-correct tests and intervals on PUMS microdata: tables, odds ratios, means, medians (Round 32)",
    "group_comparison": "Compare an area outcome across groups of areas: t-test, ANOVA, ANCOVA, interactions (Round 31)",
    "confounding": "Confounders and effect modifiers: stratified analysis, Mantel-Haenszel, homogeneity, additive interaction (Round 83)",
    "segregation": "County residential segregation from tract counts with strict ACS replicate uncertainty",
    "health_inequality": "Area health inequality indices, indirectly standardized ratios, and disparities between population groups (Kitagawa too) with ACS uncertainty",
    "compare_counties": "Compare a rate between two counties in one release",
    "tract_trend": "Trend in a tract or county rate using non-overlapping releases",
    "regression_sampling_error": "Regression whose SEs include ACS sampling error",
    "small_area": "Small-area ACS estimates (Fay-Herriot) and descriptive event-count smoothing (EB)",
    "preregistered": "Pre-registered (manifest) confirmatory analysis",
    "decennial_counts": "Use 2020 Census counts (P.L. 94-171, DHC) without inventing margins of error",
    "external_health_outcome": "Health outcome from CDC PLACES, USALEEP, County Health Rankings or WONDER, "
                               "without circularity; binomial counts with denominator trials and robust (HC3) SEs",
    "literature_to_preregistration": "Bridge isolated Layer B literature dossiers and gap matrices to a human-reviewed Layer A pre-registered manifest (Round 146)",
    "publication_verification": "Verify publication bundle SHA-256 digests, references.bib citations, and balanced LaTeX tables via MCP or CLI (Round 146)",
    "spatial_mortality_qba": "County mortality BYM2 (B3) spatial disease mapping and E-value quantitative bias analysis with WONDER suppression rules (Round 146)",
    "pums_inequality_ecologic": "PUMS earnings inequality (Gini, Atkinson, subgroup gap) and PUMA ecologic fallacy decomposition (Round 153)",
    "sae_temporal_pooling": "Multi-release county arcsine and Rao-Yu temporal Fay-Herriot small-area estimation with MSE reduction checks (Round 153)",
    "layer_b_offline_corpus": "Seed, query, and run the offline Layer B SSD FTS5 literature and handoff pipeline (Round 153)",
    "domain_hybrid_rag": "Query the 36-domain Layer B SSD corpus + local passages via citation-grounded Hybrid RAG and manage the background miner (Round 164)",
}

RecipeName = Literal[
    "compare_counties", "tract_trend", "regression_sampling_error", "small_area", "preregistered",
    "decennial_counts", "external_health_outcome", "health_inequality", "segregation", "group_comparison", "pums_tests", "rank_methods", "rank_areas", "composite_index", "agreement", "combine_estimates", "causal", "context_covariates", "replications", "policy_change", "custom_geographies", "dollars", "spatial_patterns", "cross_release", "reporting", "confounding",
    "literature_to_preregistration", "publication_verification", "spatial_mortality_qba",
    "pums_inequality_ecologic", "sae_temporal_pooling", "layer_b_offline_corpus", "domain_hybrid_rag",
]


def get_recipe(name: Optional[RecipeName] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """Return numbered steps for a standard analysis; omit name to list recipes (optional keyword query).

    Args:
        name: Recipe name (omit to list all recipes or filter with query).
        query: Optional case-insensitive keyword filter when listing recipes.

    Example: get_recipe(name="compare_counties")
    """
    if not name:
        items = [{"name": k, "description": v} for k, v in RECIPES.items()]
        if query:
            q = str(query).strip().lower()
            items = [it for it in items if q in it["name"].lower() or q in it["description"].lower()]
        return {
            "success": True,
            "summary": f"{len(items)} recipe(s) available" + (f" matching '{query}'." if query else "."),
            "next_step": "get_recipe(name=...) with one of the names in recipes",
            "recipes": items,
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

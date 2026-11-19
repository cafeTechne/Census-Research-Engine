# SPDX-License-Identifier: AGPL-3.0-or-later
"""MCP tool profiles (PLAN_ROUND_8 workstream J1/J2).

A profile is a named subset of the server's tools. Small local models do much
better with about ten short, flat tools than with the full set, so:

- ``core``: one tool per step of the standard workflow, with short
  descriptions (overrides below) and results that always carry ``summary`` and
  ``next_step`` (plus ``fix`` on failures).
- ``core_spatial``: ``core`` plus ``spatial_autocorrelation``, styled like
  ``core``; used by the local-model evaluation's spatial task (Round 10 F1).
- ``review``: concordance and rule review tools only, for reviewer agents.
- ``full``: every tool, descriptions unchanged (the default).

Select with ``python mcp_server.py --profile core`` or ``CENSUS_MCP_PROFILE=core``.
The library functions are not changed; overrides live here only.
"""

import functools
import inspect
import math
import os
from typing import Any, Callable, Dict, List, Optional, Sequence

from census import errors

DEFAULT_PROFILE = "full"
ENV_VAR = "CENSUS_MCP_PROFILE"

PROFILES: Dict[str, Optional[List[str]]] = {
    "verification": ["verify_proposition"],
    "core": [
        "get_recipe",
        "search_tables",
        "describe_variable",
        "plan_extraction",
        "download_table",  # Round 9 G2: slim download; full profile keeps batch_download
        "derive_estimate",
        "calculate_significance",
        "trend_test",
        "minimum_detectable_difference",
        "build_analysis_frame",
        "fit_model",
        "compare_groups",
        "test_association",
        "make_figure",
        "make_map",
        "run_manifest",  # registered by workstream D; skipped while absent
    ],
    "review": [
        "get_research_protocol",
        "get_recipe",
        "describe_variable",
        "list_variables",
        "check_variable_concordance",
        "draft_crosswalk_override",
        "record_crosswalk_review",
        "validate_crosswalks",
        "draft_rule_override",
        "record_rule_review",
    ],
    "full": None,
}
# core plus the global/local Moran's I tool (Round 10 F1 evaluation).
PROFILES["core_spatial"] = list(PROFILES["core"]) + ["spatial_autocorrelation"]
# Profiles built like core: short descriptions and guided results.
CORE_STYLE_PROFILES = ("core", "core_spatial")

# Core-profile parameters that are nested objects by necessity (J2 exceptions).
NESTED_PARAM_EXCEPTIONS: Dict[str, List[str]] = {
    # Optional list of {"name","op","num","den"} specs; the frame is usable without it.
    "build_analysis_frame": ["derive"],
}

DESCRIPTION_BUDGET = 700  # characters, enforced by tests/test_mcp_profiles.py

# Short descriptions for the core profile: one sentence, one line per key
# parameter, one example call. The full profile keeps the library docstrings.
DESCRIPTION_OVERRIDES: Dict[str, str] = {
    "get_recipe": (
        "Return numbered steps for a standard analysis. Call this first when unsure what to do.\n"
        "name: compare_counties | tract_trend | regression_sampling_error | small_area | preregistered | "
        "decennial_counts | external_health_outcome | health_inequality | segregation; "
        "omit to list recipes.\n"
        "Example: get_recipe(name=\"compare_counties\")"
    ),
    "search_tables": (
        "Find ACS 5-year tables by code or keyword.\n"
        "query: keyword or code, e.g. 'poverty' or 'B17001'. limit: max results.\n"
        "Example: search_tables(query=\"median household income\")"
    ),
    "describe_variable": (
        "Show label, concept, table and universe of one variable code in one release.\n"
        "code: e.g. 'B19013_001E'. year: release year (default latest).\n"
        "Example: describe_variable(code=\"B17001_002E\", year=2023)"
    ),
    "plan_extraction": (
        "Dry run of a download: API calls, concordance issues, would_block. Downloads nothing.\n"
        "state_code: 2-digit FIPS. table_code: e.g. 'B17001'. start_year, end_year: releases.\n"
        "geo_level: us|state|county|tract|place|zcta|msa. variables: codes used. county_codes: 3-digit FIPS.\n"
        "Example: plan_extraction(state_code=\"48\", table_code=\"B17001\", start_year=2018, "
        "end_year=2023, geo_level=\"county\", variables=[\"B17001_001\", \"B17001_002\"])"
    ),
    "download_table": (
        "Download one table to a panel CSV with codebook and SE/CV columns; plans first, stops if blocked.\n"
        "table_code: e.g. 'B17001'. geography: us|state|county|tract|place|zcta|msa, optional "
        "':codes' e.g. 'county:453,201'.\n"
        "state_code: 2-digit FIPS. years: releases (default latest). variables: codes used.\n"
        "dataset: 'dec/dhc' or 'dec/pl' for 2020 Census counts (no MOE).\n"
        "Example: download_table(table_code=\"B17001\", geography=\"county:453\", state_code=\"48\", "
        "years=[2023], variables=[\"B17001_001\", \"B17001_002\"])"
    ),
    "batch_download": (
        "Download a table across years and geographies to files; same arguments as plan_extraction.\n"
        "output_format: panel|both|parquet|excel. compute_reliability: add SE/CV columns.\n"
        "Returns output file paths, not the rows. Stops with CONCORDANCE_REVIEW_REQUIRED "
        "if codes changed meaning.\n"
        "Example: batch_download(state_code=\"48\", table_code=\"B17001\", start_year=2023, "
        "end_year=2023, geo_level=\"county\", county_codes=[\"453\"], output_format=\"panel\")"
    ),
    "derive_estimate": (
        "Compute a rate, ratio, sum, difference or percent change with its 90% MOE (Census formulas).\n"
        "operation: proportion (numerator is part of denominator) | ratio | sum | difference | "
        "percent_change | product.\n"
        "estimates, moes: [numerator, denominator] and their MOEs. as_percent: 0-100 scale.\n"
        "Example: derive_estimate(operation=\"proportion\", estimates=[12000, 80000], "
        "moes=[900, 1500], as_percent=true)"
    ),
    "calculate_significance": (
        "Z-test: do two ACS estimates differ significantly?\n"
        "est1, moe1, est2, moe2: estimates and 90% MOEs. confidence_level: 0.90 default.\n"
        "year1, year2: give both for the same place in two releases (overlap adjustment).\n"
        "Example: calculate_significance(est1=14.2, moe1=1.1, est2=11.9, moe2=1.0)"
    ),
    "trend_test": (
        "Test a linear trend across 3+ NON-overlapping 5-year releases (e.g. 2013, 2018, 2023).\n"
        "years, estimates, moes: equal-length lists. Overlapping releases are refused.\n"
        "Example: trend_test(years=[2013, 2018, 2023], estimates=[14.1, 13.0, 11.8], moes=[0.4, 0.4, 0.3])"
    ),
    "minimum_detectable_difference": (
        "Smallest difference two estimates with these MOEs can detect (planning).\n"
        "moe1, moe2: 90% MOEs (moe2 defaults to moe1). power: default 0.80.\n"
        "Example: minimum_detectable_difference(moe1=2.1, moe2=2.4) -> about 4.8"
    ),
    "build_analysis_frame": (
        "Make a model-ready file from a batch_download output: estimate, _se and _cv per variable.\n"
        "input_path: downloaded CSV/Parquet. variables: columns to keep. use_replicates, "
        "table_code, year: attach Census replicates for exact sampling error.\n"
        "Example: build_analysis_frame(input_path=\"downloads/B17001_panel.csv\", "
        "variables=[\"B17001_002E\"])"
    ),
    "fit_model": (
        "Fit a regression whose standard errors include ACS sampling error.\n"
        "input_path: analysis frame. formula: 'y ~ x1 + x2'. method: replicate | eiv | "
        "regression_calibration | simex | fay_herriot. eiv corrects noisy ACS predictors (needs replicates_path). model: ols|wls|binomial|poisson|negbin.\n"
        "replicates_path: from build_analysis_frame. se_col: outcome SE (fay_herriot).\n"
        "Example: fit_model(input_path=\"downloads/analysis_frame.parquet\", "
        "formula=\"poverty_rate ~ median_rent\")"
    ),
    "test_association": (
        "Survey-correct tests on PUMS microdata with replicate weights.\n"
        "state, year. kind: independence (row, col) | two_by_two (exposure, outcome) | means (var, by) | "
        "medians (var, by) | proportion (var).\n"
        "Conditions use PUMS codes, e.g. outcome=\"POVPIP < 100\". where: universe. Results say validated or exploratory.\n"
        "Example: test_association(state=\"26\", year=2022, kind=\"two_by_two\", exposure=\"DIS == 1\", outcome=\"POVPIP < 100\")"
    ),
    "compare_groups": (
        "Compare an area outcome across groups: t-test, ANOVA, ANCOVA or interaction, with ACS error.\n"
        "input_path: analysis frame. outcome: column. group: category column or 'state'. "
        "design: two_group | oneway | ancova | twoway. covariates (ancova). group2 (twoway).\n"
        "model: ols|binomial|poisson. replicates_path: from build_analysis_frame. posthoc: holm | simultaneous | none.\n"
        "spatial: true for 8 fixed spatial clusters. method: model | rank. Results say validated or exploratory.\n"
        "Example: compare_groups(input_path=\"frame.parquet\", outcome=\"poverty_rate\", group=\"metro_class\")"
    ),
    "make_map": (
        "Write a journal-ready map (PDF, SVG, PNG) of one variable with Census boundaries.\n"
        "input_path: CSV/Parquet with GEOID. column: variable. level: tract | county | state | place.\n"
        "year: ACS release. se_col or moe_col: marks unreliable areas. kind: estimate | uncertainty | significance.\n"
        "Example: make_map(input_path=\"frame.parquet\", column=\"poverty_rate\", level=\"county\", "
        "year=2023, se_col=\"poverty_rate_se\")"
    ),
    "spatial_autocorrelation": (
        "Test whether one variable is spatially clustered: Moran's I with its p-value.\n"
        "input_path: CSV/Parquet with GEOID. column: variable. level: tract | county | state | place.\n"
        "year: ACS release. weights: queen | rook | knn. local: true adds LISA clusters.\n"
        "Example: spatial_autocorrelation(input_path=\"frame.csv\", column=\"poverty_rate\", "
        "level=\"tract\", year=2023)"
    ),
    "make_figure": (
        "Write a journal-ready figure (PDF, SVG, PNG) with values CSV and caption.\n"
        "kind: estimates | forest | trend. input_path: CSV/Parquet. label_col, estimate_col, "
        "moe_col, period_col: column names.\n"
        "Example: make_figure(kind=\"estimates\", input_path=\"rates.csv\", label_col=\"NAME\", "
        "estimate_col=\"rate\", moe_col=\"rate_moe\")"
    ),
}

# next_step for core tools whose results do not set one themselves.
NEXT_STEPS: Dict[str, str] = {
    "search_tables": "describe_variable on the codes you need, then plan_extraction",
    "describe_variable": "plan_extraction with these codes in variables=[...]",
    "plan_extraction": "if would_block is false, download_table for the same table, geography and years",
    "batch_download": "derive_estimate for rates, or build_analysis_frame for models",
    "derive_estimate": "calculate_significance to compare this estimate with another",
    "calculate_significance": "report the difference, its p_value and the verdict",
}

CORE_INSTRUCTIONS = """\
US Census ACS 5-year data tools. Every result has `summary` and `next_step`.
1. For any "how do I..." or multi-step task, call get_recipe FIRST and follow it
   (no arguments lists recipes).
2. Report every estimate with its 90% margin of error (MOE).
3. Rates: derive_estimate(operation='proportion') when the numerator is part of
   the denominator. Compare two estimates with calculate_significance.
4. Trends need non-overlapping releases (e.g. 2013, 2018, 2023): trend_test.
5. Download with download_table (it plans first); stop if would_block is true.
6. On failure read error_code and fix; do not guess numbers.
7. Health outcomes: use the ACS's own measure (disability: B18101); use CDC PLACES
   only for measures the ACS lacks, such as diabetes (get_recipe first).
8. Area inequality and standardized ratios: get_recipe('health_inequality'), then
   existing manifest tools. Inequality statistics sii/log_rii/concentration_index
   have no term; declare higher_is_more_deprived and positive weights. Ridits run
   least to most deprived; positive indices mean higher outcomes among more deprived
   areas, reversing the usual income-ranked concentration sign. Default conservative
   target combines HC3 and ACS replicates; median rank CV <=15% is validated, above
   which warn about attenuation. External outcome/denominator weights stay fixed;
   R2 tests rank_by. HC3 assumes independent areas. SMR requires observed integer
   counts, distinct population_bands, positive reference_rates in events per person-year
   and a hashed reference_source citation; log_smr hypotheses use geoid or all.
   Only conservative combined Poisson/replicate log intervals drive SMR tests;
   fixed-E Garwood intervals omit expected/reference uncertainty. O=0 has only exact limits;
   absent replicates set expected uncertainty to zero, noted. period_years (positive
   integer, default 1) scales E; reference_counts adds sum((E_b/E)^2/D_b) to log
   variance, with positive integer reference deaths per band. Both hashed. Rates
   are fixed without counts; reference person-years are always fixed. Pool band
   contributions before squaring (shared rates). Internal-reference covariance
   omitted makes intervals conservative, noted, not refused.
   SMR refuses negative band replicates under its pre-specified validation domain.
   Log statistics test zero and report exponentiated ratio columns. R1 applies
   to external outcomes/counts; reused MI/NY LBW associations remain exploratory.
9. Round 30 C1 passed the fixed ACS-error validation for unweighted OLS, binomial
   and Poisson: use fit_replicate with spatial_clusters={"k":8,"method":"im"},
   target="population". Keep supplied ACS replicates; independent sampling error
   enters between-cluster spread, without adding replicate variance. The IM estimate
   is the unweighted mean of eight cluster coefficients; se_cluster_mean and t(7)
   drive intervals and p-values. The estimand is the coefficient on ACS estimates
   as observed, not a measurement-error-corrected true slope. Sampling error can
   attenuate it; noisy controls can bias it in either direction. A zero naive slope
   equates to a zero true slope only with a single error-prone covariate and errors
   independent of the outcome's error; do not extend that claim to noisy controls.
   Poisson exposure/expected-death offsets remain fixed.

   C2 IM-EIV failed (unstable corrected moment matrices) and stays refused, even
   in exploratory manifests; never substitute C1 for registered EIV without a new
   specification. WLS remains unsupported. Only k=8 passed. CR1/WCR refusals remain.
   IM still requires population target; scale:robust and spatial_se are mutually
   exclusive with spatial_clusters. Labels are fixed before complete-case filtering
   (50 seeded EPSG:5070 restarts); every retained group needs >=5 units and full rank.
   Whole terms constant within every cluster are absorbed by cluster intercepts,
   reported not estimable and cannot be tested. Partial constancy is refused.
   R21b EIV re-checks are unavailable; R22 and R29 MI/NY C1 re-checks are post hoc,
   author self-review, not independent. OH/PA is outside this validation geometry.
   See docs/audits/im_acs_validation.md and docs/studies/r30_posthoc_im_acs.md.

10. Round 31 group comparisons: compare_groups (recipe group_comparison) runs t-tests,
     one-way ANOVA, ANCOVA and two-way interactions through fit_replicate. Joint tests
     use joint_test (manifest statistic; variable or term, two_sided only). Validated
     (docs/audits/omnibus_validation.md, n=145): wild score bootstrap for OLS factor tests
     and binomial/Poisson spline tests; IM-8 Hotelling for OLS/Poisson factor tests;
     Holm pairwise for OLS/binomial/Poisson; simultaneous pairwise for OLS only. F
     references failed. Binomial/Poisson factor tests, OLS splines, fewer than 145 areas
     and population-target tests with replicates are exploratory. Groups need >=5 areas;
     spatial tests need every group in every cluster. Round 27 joint_wald (chi-squared)
     stays exploratory; confirmatory binomial/Poisson splines need joint_test hypotheses.

11. Round 32 PUMS tests: test_association (recipe pums_tests) on PUMS microdata with
     the 80 replicate weights. Validated (docs/audits/pums_tests_validation.md, household
     clustering, weight CV up to 1.0, 800-3000 households): first-order Rao-Scott
     independence tests for tables up to 3x4; k-group mean tests (design Wald F; z for two
     groups); differences of proportions, odds ratios, relative risks, differences of means
     and medians; Korn-Graubard intervals for one proportion. The design-blind Pearson test
     is far too liberal; Wald proportion intervals under-cover for rare outcomes in small
     domains; larger tables are exploratory. No continuity corrections: empty 2x2 cells are refused.

12. Round 33 rank methods (recipe rank_methods): correlation_matrix returns
     validated_intervals per pair. Spearman and Kendall Fisher-type intervals passed
     without replicates; Pearson and partial (one control) intervals pass only with
     replicates (ACS replicate variance added), else exploratory. Estimand: the observed-
     estimate correlation (attenuated). compare_groups(method="rank"): Brunner-Munzel
     superiority (two groups) and Kruskal-Wallis (3+), validated for independent areas.
     All correlation intervals under-covered (0.60-0.89) with spatially correlated areas.
     OLS fit_model/compare_groups add model diagnostics (VIF, Cook's distance, Breusch-Pagan,
     RESET): information only, never a gate.

13. Round 34 ranking (full profile tool rank_areas; recipe rank_areas): rank intervals
     (Klein-Wright-Wieczorek; individual or joint) and areas versus a reference (Holm or
     simultaneous) passed validation. Report rank intervals, not point ranks; bootstrap
     percentile ranks under-cover and are not offered; suppressed values are never ranked.

14. Round 35 spatial EIV: corrected (error-free) linear slopes when areas are spatially
     correlated: fit_model(method="eiv", spatial="clusters"|"error") or
     census.spatial_eiv.fit_spatial_eiv. Both passed (coverage .863-.918; 145 MI/NY counties;
     up to two error-prone covariates; reliability .7-.9); more error-prone covariates are
     exploratory. Not yet in manifests (fit_eiv spatial_clusters stays refused there).
     R21b post hoc: H1 and H4 still hold under both.

15. Event-count EB smoothing is descriptive Python-library work, not a new tool or
   manifest method: get_recipe('small_area'). Use fixed expected counts, preserve
   WONDER [1,9] suppression, report validation metadata; never impute suppressed
   counts or call EB limits ACS MOEs. Posterior 90% and 200-refit Laird-Louis
   intervals passed Round 27; reference-rate/spatial uncertainty is excluded.
   cr(x,df=3|4|5) and joint_wald FAILED Round 27 and are exploratory only;
   confirmatory manifests refuse either, except binomial/Poisson cr tested with
   joint_test (Round 31). Only non-spatial fit_replicate
   OLS/WLS/binomial/Poisson; centered full-sample knots stay fixed in refits.
   Joint hypotheses give variable, no term, two_sided (or two-sided); R2 applies
   to variable. W has chi-squared(q), recorded df, no coefficient CI or odds ratio.
   HC3 / ACS covariance / their sum matches target; singular covariance is not
   tested. See the protocol for full covariance metadata and validation scope.
16. Segregation: get_recipe('segregation'), then existing manifest tools. Tract
   groups are mutually exclusive counts, within county. Defaults: naive D,
   corrected isolation/H; failed overrides and multigroup H exploratory only.
   Strict 80 replicates, no clipping/holding missing counts fixed. Zero tracts
   recomputed per refit; absent county groups undefined. One-area tests need
   null_value; compare_geoid uses replicate differences. release/compare_release
   select independent non-overlapping releases; variances add. First minus
   comparison, one-sided tests center on null. No metro pooling. Any tract
   group-count CV above .15 makes a county exploratory only (most real ones).
"""

REVIEW_INSTRUCTIONS = """\
ACS concordance review tools. Call get_research_protocol first. Drafters use
draft_crosswalk_override / draft_rule_override; a DIFFERENT identity reviews with
record_crosswalk_review / record_rule_review. Never review your own draft.
"""


def resolve_profile(argv: Optional[Sequence[str]] = None, env: Optional[Dict[str, str]] = None) -> str:
    """Profile from ``--profile NAME`` / ``--profile=NAME`` in argv, else the
    environment variable, else ``full``. Raises ValueError for unknown names."""
    env = os.environ if env is None else env
    name = env.get(ENV_VAR) or DEFAULT_PROFILE
    args = list(argv or [])
    for i, arg in enumerate(args):
        if arg == "--profile" and i + 1 < len(args):
            name = args[i + 1]
        elif arg.startswith("--profile="):
            name = arg.split("=", 1)[1]
    name = name.strip().lower()
    if name not in PROFILES:
        raise ValueError(f"Unknown MCP profile '{name}'. Choose from {sorted(PROFILES)}.")
    return name


def tools_for(profile: str, available: Sequence[str]) -> List[str]:
    """Tool names in a profile that are actually registered, in profile order."""
    wanted = PROFILES[profile]
    if wanted is None:
        return list(available)
    have = set(available)
    return [name for name in wanted if name in have]


def _fmt(value: Any, spec: str) -> Optional[str]:
    """Format a number, or None when it is missing/NaN/non-numeric."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return format(v, spec) if math.isfinite(v) else None


def _summary_for(name: str, out: Dict[str, Any]) -> str:
    if out.get("success") is False:
        return str(out.get("error") or "The call failed.")
    if name == "derive_estimate" and "estimate" in out:
        est, moe = _fmt(out.get("estimate"), ".4g"), _fmt(out.get("moe"), ".4g")
        if est is None:
            return f"{out.get('method')} estimate undefined (see notes)."
        moe_txt = f"90% MOE {moe}" if moe is not None else "MOE undefined (see notes)"
        return f"{out.get('method')} estimate {est} with {moe_txt}."
    if name == "calculate_significance" and "verdict" in out:
        diff, p = _fmt(out.get("difference"), ".4g"), _fmt(out.get("p_value"), ".3g")
        if diff is None:
            return f"Difference undefined (see notes). {out['verdict']}"
        p_txt = f"p={p}" if p is not None else "p undefined"
        return f"Difference {diff} ({p_txt}). {out['verdict']}"
    if name == "plan_extraction" and "would_block" in out:
        return f"Plan ready; would_block={out['would_block']}."
    if "count" in out and "results" in out:
        return f"{out['count']} result(s)."
    return "Done."


def with_guidance(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a tool so dict results carry ``summary`` and ``next_step`` (and
    ``fix`` with the plain-language meaning of ``error_code`` on failure).
    List results are wrapped as ``{"results": [...]}``. Signature is kept."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        out = fn(*args, **kwargs)
        if isinstance(out, list):
            out = {"success": True, "count": len(out), "results": out}
        if isinstance(out, dict) and isinstance(out.get("summary"), dict):
            # e.g. plan/batch results carry a concordance summary dict under "summary"
            out = {**{k: v for k, v in out.items() if k != "summary"}, "concordance_summary": out["summary"]}
        if not isinstance(out, dict):
            return out
        guided = dict(out)
        guided.setdefault("summary", _summary_for(name, out))
        if out.get("success") is False:
            guided.setdefault("fix", errors.ERROR_CODES.get(str(out.get("error_code")), ""))
            guided.setdefault("next_step", "fix the arguments as described in `fix` and call again, "
                                           "or get_recipe for the standard steps")
        else:
            guided.setdefault("next_step", NEXT_STEPS.get(name, "get_recipe for the next step"))
        return {"summary": guided.pop("summary"), "next_step": guided.pop("next_step"), **guided}

    # A list-returning tool now returns a dict; keep the output schema honest.
    wrapper.__signature__ = inspect.signature(fn).replace(return_annotation=Dict[str, Any])  # type: ignore[attr-defined]
    return wrapper


def build_profile_server(base: Any, profile: str) -> Any:
    """Return a FastMCP server exposing only ``profile``'s tools.

    ``full`` returns ``base`` unchanged. Other profiles get a new FastMCP with
    shorter instructions; core tools use DESCRIPTION_OVERRIDES and
    ``with_guidance`` results."""
    if PROFILES[profile] is None:
        return base
    from mcp.server.fastmcp import FastMCP

    manager = base._tool_manager
    available = [t.name for t in manager.list_tools()]
    instructions = ("Check only the operator-pinned proposition. Formalization review is outside tool authority. "
                    "A refutation is successful evidence; never substitute a related theorem or infer empirical confirmation."
                    if profile == "verification" else
                    CORE_INSTRUCTIONS if profile in CORE_STYLE_PROFILES else REVIEW_INSTRUCTIONS)
    server = FastMCP(f"{base.name} [{profile}]", instructions=instructions)
    for name in tools_for(profile, available):
        tool = manager.get_tool(name)
        if profile in CORE_STYLE_PROFILES:
            fn = with_guidance(name, tool.fn)
            description = DESCRIPTION_OVERRIDES.get(name, tool.description)
        else:
            fn, description = tool.fn, tool.description
        # Python 3.13+ strips docstring indentation at compile time; older versions do not.
        # Normalise so every Python sends the same (shorter) text and the budget holds.
        server.add_tool(fn, name=name, description=inspect.cleandoc(description) if description else description)
    return server

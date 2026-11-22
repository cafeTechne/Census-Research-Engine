# SPDX-License-Identifier: AGPL-3.0-or-later
"""Census Research Engine: MCP server.

Exposes discovery, extraction, cross-vintage concordance review, and research
statistics tools over the Model Context Protocol. The server instructions and
``get_research_protocol`` tell agents how to plan extractions and how to draft
and independently review concordance overrides (docs/agent_protocol.md).
"""

import os
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP
import pandas as pd

from census import (
    DATASET_TABLES,
    PRICE_INDEXES,
    STATE_MAPPING,
    CensusAPIClient,
    PriceIndexUnavailable,
    ResearchOptions,
    add_geoid_column,
    add_reliability_columns,
    archived_vintages,
    available_vintages,
    build_concordance,
    build_entities,
    clean_census_sentinels,
    counties_for_state,
    errors,
    get_default_cache,
    get_local_places_file,
    infer_dataset,
    latest_vintage,
    load_places_from_local,
    is_nationwide,
    load_price_index,
    provisional_advisory,
    load_table_catalog,
    plan_extraction as _plan_extraction,
    price_index_info,
    public_plan,
    resolve_metadata,
    resolve_zip,
    run_batch,
    table_variables,
    validate_all_crosswalks,
    z_test,
    zctas_for_state,
)
from census import adjust_inflation as _adjust_inflation
from census import apply_overrides
from census import calculate_cv as _calculate_cv
from census import describe_variable as _describe_variable
from census import generate_codebook as _generate_codebook
from census.concordance import BLOCKING_KINDS
from census.data_integrity import BundledDataIntegrityError, integrity_error_result, integrity_errors
from census.decennial import DISCLOSURE_AVOIDANCE_ADVISORY, is_decennial, uncertainty_record
from census.metadata import preflight_archives, table_universe
from census.panel import IDENTIFIER_COLUMNS, describe_columns
from census.review import draft_override, record_override
from census.stats import acs_overlap_years
from census import mcp_profiles, recipes, workflows, workflows_geo, workflows_inference, workflows_microdata, workflows_verification

from census.env import load_environment

load_environment()

ROOT = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_PATH = os.path.join(ROOT, "docs", "agent_protocol.md")

_INSTR_HEAD = """\
US Census ACS 5-year data server. Agents run the full workflow, including review.

Extraction:
1. Find tables (search_tables) and variables (list_variables, describe_variable).
   Variable codes are vintage-specific: the same code can mean different things in
   different years.
2. For multi-year work, call plan_extraction first with variables=[...] naming the
   codes your analysis uses (CODE resolves in the latest requested year;
   YEAR:CODE pins a vintage). Check the plan's `selection` and `would_block`.
3. If would_block is false, call batch_download with the same arguments.
4. If it blocks (CONCORDANCE_REVIEW_REQUIRED), do not bypass it with
   concordance_mode='code' or 'strict' for confirmatory work. Review the issues.

Review (overrides in crosswalks/<dataset>/<table>.csv):
- Drafter: check_variable_concordance -> read a census.gov primary source ->
  draft_crosswalk_override(drafted_by='agent:<model>/<session>').
- Reviewer: a DIFFERENT identity (another agent session or a human) independently
  re-checks the evidence and source, then record_crosswalk_review(reviewed_by=...).
  Never review your own draft. When in doubt, choose 'split' over 'merge'.
- merge rows need census.gov sources, generated evidence, and a passing continuity
  check (or a written continuity_exception). Validation enforces all of this.

Table-wide redesigns: draft_rule_override / record_rule_review (same two-identity
review; rules never change numbers in labels and never exempt continuity).

Derived statistics (every result records its `method`):
- Rates: derive_estimate('proportion') only when the numerator is a subset of the
  denominator; otherwise 'ratio'. Combine areas with aggregate_geographies (sum
  counts first, then derive); never average rates or medians.
- Exact MOEs: check_replicate_availability; when available, use replicates
  (use_replicates=True) for any derived estimate that feeds a hypothesis test.
- Medians for custom areas: median_from_distribution (brackets summed first).
- Many comparisons: batch_significance with a correction (default holm); report
  significant_adjusted.
- Tract panels across 2010/2020: batch_download(harmonize_tracts_to=2020) or
  apportion_tracts.
- Nationwide: state_code='all'. Reproducibility: replay_extraction.
- run_validation checks the toolkit against Census-published values.

2020 Census: dataset='dec/dhc' (DHC: P1, P12, H1, H3, ...) or 'dec/pl' (P.L. 94-171,
down to blocks), years 2020 only, through the same plan_extraction / batch_download.
Census counts are not sample-based: MOE/CV are undefined (never 0); significance tools
refuse decennial-only tests (product='decennial'); an ACS estimate can be tested against
a census count with calculate_significance(product='5-year', product2='decennial').

External health data (list_health_sources; get_recipe('external_health_outcome')):
determinant studies keep using the ACS's own measure as the outcome (for disability:
B18101), and use external sources such as CDC PLACES for measures the ACS lacks, such as
diabetes. PLACES is model-based: within a county it varies only with age, sex,
race/ethnicity and education composition, so never test a PLACES outcome against those
(it recovers CDC's model, not the world). USALEEP life expectancy is partly modelled on
income, race/ethnicity and education. County Health Rankings mortality and WONDER exports
are direct death records. create_manifest refuses violations (CIRCULARITY R1/R2).
Use exploratory:true to label an exploratory manifest; deviations remain recorded.
Spatial_se (Bartlett Conley) failed validation: exploratory only, including run_variant.
Round 30 C1 passed the fixed ACS-error validation for unweighted OLS, binomial
and Poisson: use fit_replicate with spatial_clusters={"k":8,"method":"im"},
target="population". Keep supplied ACS replicates; independent sampling error
enters between-cluster spread, without adding replicate variance. The IM estimate
is the unweighted mean of eight cluster coefficients; se_cluster_mean and t(7)
drive intervals and p-values. The estimand is the coefficient on ACS estimates
as observed, not a measurement-error-corrected true slope. Sampling error can
attenuate it; noisy controls can bias it in either direction. A zero naive slope
equates to a zero true slope only with a single error-prone covariate and errors
independent of the outcome's error; do not extend that claim to noisy controls.
Poisson exposure/expected-death offsets remain fixed."""

# BEGIN GENERATED RULES A (scripts/sync_rule_text.py; source: docs/agent_protocol.md <!-- mcp-rules:A --> paragraphs)
_RULES_A = """
C2 IM-EIV failed (unstable corrected moment matrices) and stays refused, even
in exploratory manifests; never substitute C1 for registered EIV without a new
specification. WLS remains unsupported. Only k=8 passed. CR1/WCR refusals remain.
IM still requires population target; scale:robust and spatial_se are mutually
exclusive with spatial_clusters. Labels are fixed before complete-case filtering
(50 seeded EPSG:5070 restarts); every retained group needs >=5 units and full rank.
Whole terms constant within every cluster are absorbed by cluster intercepts,
reported not estimable and cannot be tested. Partial constancy is refused.
R21b EIV re-checks are unavailable; R22 and R29 MI/NY C1 re-checks are post hoc,
author self-review, not independent. Round 44 re-ran the C1 design on OH/PA: it held with
independent areas but under-covered with spatially correlated fields (.70-.85), so C1 is
exploratory outside MI/NY (results carry a note); clusters crossing a state border are flagged.
The corrected-slope G1/G2 replicated on OH/PA (docs/audits/ohpa_revalidation.md). Round 54
(docs/audits/ohpa_revalidation2.md): IM with 4 or 6 within-state clusters did not repair C1 on OH/PA
(worst cells .827, .753); a fresh-seed MI/NY rerun of C1 covered .849 in one cell (linear, 100 km,
reliability .7; Round 30 .885), so treat C1 with low-reliability covariates and strong spatial
correlation cautiously even in MI/NY. IM-8 count slopes and calibrated count slopes replicated on
OH/PA (.875-.912); G2 with up to four error-prone covariates replicated there, G1 with three to five
and G2 with five did not (.807-.859 at reliability .7 with correlated fields).
Round 58 (docs/audits/spatial_outside_validation.md): SCPC (census.scpc.fit_scpc;
fit_model(method="replicate", spatial="scpc")) gives naive-slope intervals that do not assume
independent clusters. It is validated for OLS (rho_bar .05) and Poisson (.10) on MI/NY and OH/PA
alike; binomial SCPC failed at .05/.10 but passes at rho_bar .15 (Round 62, the default for binomial). Round 67: on
North Carolina tracts SCPC under-covered with 100 km fields (.75/.81) at rho_bar .05/.10. Round 71
(docs/audits/tract_spatial_validation.md): tract OLS slopes are validated with rho_bar .20 (the tract default)
or .30 on NC and MI tracts up to 100 km (.885-.988); tract Poisson/binomial SCPC and the tract spatial
error model (.63-.76) are exploratory. fit_model warns when residuals are spatially dependent. A 10,000-draw rerun confirmed IM-8 OLS at .858 in the
low-reliability, correlated MI/NY cell, so prefer SCPC for OLS. With every error-prone covariate's
reliability >= .8, G1/G2 with three to five covariates pass on OH/PA too (reliability is
reported). Calibrated binomial slopes with IM-8 clusters are validated
(fit_model(method="regression_calibration", model="binomial", spatial="clusters")).
Round 63: under the same gate (every reliability >= .8) G1 is validated with up to eight and G2 with
up to seven error-prone covariates (docs/audits/small_many_validation.md).
See docs/audits/im_acs_validation.md and docs/studies/r30_posthoc_im_acs.md.

Round 31 group comparisons: compare_groups (recipe group_comparison) runs t-tests,
one-way ANOVA, ANCOVA and two-way interactions through fit_replicate. Joint tests
use joint_test (manifest statistic; variable or term, two_sided only). Validated
(docs/audits/omnibus_validation.md, n=145): wild score bootstrap for OLS factor tests
and binomial/Poisson spline tests; IM-8 Hotelling for OLS/Poisson factor tests;
Holm pairwise for OLS/binomial/Poisson; simultaneous pairwise for OLS only. F
references failed. Binomial/Poisson factor tests, OLS splines, fewer than 145 areas
and population-target tests with replicates are exploratory. Groups need >=5 areas;
spatial tests need every group in every cluster. Round 27 joint_wald (chi-squared)
stays exploratory; confirmatory binomial/Poisson splines need joint_test hypotheses.

Round 32 PUMS tests: test_association (recipe pums_tests) on PUMS microdata with
the 80 replicate weights. Validated (docs/audits/pums_tests_validation.md, household
clustering, weight CV up to 1.0, 800-3000 households): first-order Rao-Scott
independence tests for tables up to 3x4; k-group mean tests (design Wald F; z for two
groups); differences of proportions, odds ratios, relative risks, differences of means
and medians; Korn-Graubard intervals for one proportion. The design-blind Pearson test
is far too liberal; Wald proportion intervals under-cover for rare outcomes in small
domains; larger tables are exploratory. No continuity corrections: empty 2x2 cells are refused.
Round 56: test_association(kind="inequality", var=<nonnegative income>[, by=<two groups>]) gives
the Gini coefficient (.861-.908), log P90/P10 and log P80/P20 (.888-.923) and the Gini difference
between two groups (.873-.899), all validated with SDR replicate variance. Round 60: with logit-transformed
SDR intervals Atkinson (eps 1) is validated, and Atkinson (.5) and the top-decile share with at least 7,000
records; Theil T still failed, also with 8,000 households (Round 62; exploratory). Results name the interval method. Zero incomes stay in the
Gini; negative incomes are refused; heaped quantiles are flagged as for medians.

Round 33 rank methods (recipe rank_methods): correlation_matrix returns
validated_intervals per pair. Spearman and Kendall Fisher-type intervals passed
without replicates; Pearson and partial (one control) intervals pass only with
replicates (ACS replicate variance added), else exploratory. Estimand: the observed-
estimate correlation (attenuated). compare_groups(method="rank"): Brunner-Munzel
superiority (two groups) and Kruskal-Wallis (3+), validated for independent areas.
All correlation intervals under-covered (0.60-0.89) with spatially correlated areas. Round 48:
correlation_matrix(spatial=True) uses the effective sample size (Spearman .875-.917, Kendall
.862-.905, Pearson with replicates .864-.967). Round 59: partial correlations (one control,
replicates) use the effective n of the residual series (.869-.971), and all of these intervals and
the effective-n alpha replicated on OH/PA (docs/audits/spatial_correlation_validation.md).
OLS fit_model/compare_groups add model diagnostics (VIF, Cook's distance, Breusch-Pagan,
RESET): information only, never a gate.

Round 34 ranking (recipe rank_areas): rank_areas gives Klein-Wright-Wieczorek rank
intervals (individual, or joint for all areas) and each area versus a reference (fixed
value, or a weighted mean of the areas whose errors it shares; Holm or simultaneous).
Validated; conservative. Report rank intervals, not point ranks. Bootstrap percentile
ranks under-covered badly and are not offered. Non-numeric (suppressed) values are
excluded, never ranked. Areas are treated as independent samples.

Round 35 spatial EIV: corrected (error-free) linear slopes when areas are spatially
correlated: fit_model(method="eiv", spatial="clusters"|"error") or
census.spatial_eiv.fit_spatial_eiv. Both passed (coverage .863-.918; 145 MI/NY counties;
up to two error-prone covariates; reliability .7-.9). Round 46 extended both to three and four
error-prone covariates (coverage .876-.927, docs/audits/glm_correction_validation.md; at reliability .7 with
correlated fields the point estimates were unstable, mean bias up to +.17 on .5); Round 53 to five
(coverage .864-.925, docs/audits/glm_correction2_validation.md; at reliability .7 with correlated fields up
to 10% of fits failed and estimates were very unstable); six failed at reliability .7. Round 63: when every
error-prone covariate's estimated reliability is >= .8, "clusters" is validated with up to eight and "error" with
up to seven (docs/audits/small_many_validation.md); otherwise more than five are exploratory.
Round 53: fit_model(method="regression_calibration", se_method="jackknife") is validated for binomial,
poisson and negbin slopes (binomial with the default bootstrap is exploratory);
fit_model(method="regression_calibration", model="poisson"|"negbin", spatial="clusters", exposure=...)
calibrates error_covariates then fits IM-8 count slopes (validated).
In manifests: fit_eiv args.spatial (Round 43); fit_eiv spatial_clusters stays refused.
Round 61 manifest options: fit_replicate args.spatial_scpc {} or {rho_bar} (SCPC naive slopes; OLS,
Poisson with exposure; binomial with trials (rho_bar .15/.20, Round 62); population target, no weights/scale/spatial_se);
regression_calibration args.spatial "clusters" with model poisson/negbin (exposure) or binomial
(trials); correlation_matrix args.spatial true with interval "validated" (effective-n intervals).
R21b post hoc: H1 and H4 still hold under both.

Round 36 composite indices (full profile tool build_index; recipe composite_index):
first principal component or equal weights; full-sample standardisation and loadings
fixed in every replicate. Validated: per-area score intervals (with replicates) and the
Feldt interval for Cronbach's alpha (independent areas; it under-covers with spatial
dependence; build_index(spatial=True) uses the effective sample size, validated .912-.926 in Round 48). Quintile stability and typologies are descriptive. An outcome cannot be an
indicator of the index used to explain it (circularity).
Round 73 (docs/audits/methods73_validation.md): build_index(method="loadings", loadings={indicator: weight})
applies a paper's published fixed loadings (two or more indicators); its per-area replicate intervals are
validated (mean coverage .897-.899, every area >= .878); standardize=True rescales scores to mean 0, SD 1.

Round 73 three-level models (full profile multilevel_model with groups=[top, middle], e.g.
["state", "county"]): REML random intercepts; fixed-effect intervals use t(G_top - 1) and are
validated (.904-.913 with 30 or 49 top units). Variance shares are reported; their jackknife
intervals are exploratory (screened on 100 draws only); share_intervals=False skips them. The
three-level model takes no sampling_se, replicates or random slopes. Expected counts for indirect
standardization: census.wonder_reference.expected_counts (national WONDER age x sex rates; period_years,
or person_years with the ACS age x sex mix). Round 75 manifests: method "multilevel" (groups "county_fips"
or ["state_fips", "county_fips"]); an "indices" block (ACS indicators; weights fixed in replicates; an
index cannot explain its own indicator); expected_count "person_years" (an external variable).

Round 37 agreement (full profile tool check_agreement; recipe agreement): bias (b - a)
and Cohen's kappa of quintile classes passed validation for independent areas. Bland-Altman
limits of agreement (observed and error-free) use moment-based SEs since Round 48 (validated,
.884-.936). Lin's concordance correlation intervals failed (exploratory).

Round 38 combining evidence (full profile tool combine_estimates; recipe
combine_estimates): pooling uses Paule-Mandel + Hartung-Knapp (validated for up to 4
estimates; Round 48: 5-10 with the variance factor truncated at 1, .874-.918); the fixed-effect interval only if homogeneity is declared in advance;
DerSimonian-Laird under-covers with heterogeneity. TOST equivalence (margin set in
advance) and z-test power/minimum detectable effects are validated. Pooling states is a
new analysis, never a reinterpretation of a registered study.

Round 39: compare_groups(outcomes=[...]) adds a joint MANOVA/MANCOVA test (multivariate wild
score bootstrap, one sign per area; validated, size .090-.101; Pillai's trace shown for
comparison). Count slopes: fit_model(model="negbin", exposure=...) uses NB2 with HC3
(validated .885-.901, including overdispersion and excess zeros); Poisson HC3 under-covered
with strong overdispersion (.81-.87) and zero-inflated Poisson failed (exploratory).

Round 40: fit_model(model="beta") (shares in 0-1; logit mean; HC0 sandwich) and
fit_model(model="median") (median regression; kernel SE) passed validation (.885-.917; naive
target; independent areas). Beta model-based SEs failed. Adding replicate variance
over-covered, so it is not added. Survey-weighted PUMS ordinal,
multinomial, median and probit models were added in Round 49 (`pums_regression`); GEE is not available.

Round 41 causal tools (full profile tool estimate_effect; recipe causal): treatment
effects (AIPW default) validated with precisely measured confounders; 2SLS with an
independent second measurement as instrument removes covariate attenuation (validated;
weak instruments flagged); mediation validated only with an exactly measured mediator
(ACS mediator error drops coverage to .69-.72). State the assumptions; confirmatory causal
claims need a registered design.

Round 43 manifest options (opt-in; registered manifests unchanged): correlation_matrix
args.interval "validated" uses the Round 33 intervals (Spearman/Kendall; Pearson/partial
with one control need declared ACS replicates), and a pair the engine labels exploratory
is not tested in a confirmatory run. fit_replicate args.model "negbin" with exposure
(NB2-HC3, population target only; no weights, scale or spatial options; external WONDER
counts allowed as for Poisson). fit_eiv args.spatial "clusters" (G1) or "error" (G2):
unweighted OLS, no cluster/spatial_se/spatial_clusters; more than five error-prone
covariates are not tested in a confirmatory run (Rounds 46 and 53). regression_calibration with
model "binomial" needs args.se_method "jackknife" (Round 53); with the default bootstrap it is
exploratory and not tested in a confirmatory run. Round 72: county covariates the ACS lacks (CBP
establishments, ERS county types and rural-urban codes, CHR additional measures) come from a manifest
"context" block or build_analysis_frame(context=[...]) (get_recipe("context_covariates")); they are covariates,
never outcomes. Round 70: for long runs call run_manifest(...,
checkpoint=true) with a fixed output_dir; after a crash, the same call reuses finished analyses (same
manifest and data only) and gives identical results. Progress lines go to stderr (CENSUS_PROGRESS=0
silences them).

Round 45 count repairs: interval-censored NB2 (fit_model(model="negbin", exposure=..., censored=
"<true/false column>") since Round 64; census.missing_censored_its.fit_censored_negbin) uses WONDER
counts hidden as 1-9 as interval information, validated (.869-.898), and never outputs a hidden value; fit_model(model="negbin", spatial="clusters") gives IM-8 count slopes (validated on
the MI/NY geometry; outside it the result carries a note); NB2 with noisy ACS exposures held fixed
covered (.888-.891). within_states=True assigns the eight clusters within each state.

Round 42: fit_model(impute="w") multiply imputes one incomplete covariate (20 draws, Rubin's
rules; validated, also when missingness depends on the outcome). Round 47: impute=["w", "v"] imputes
two by chained equations (validated .898-.916; complete case .84 when missingness depends on the outcome). Exploratory:
census.missing_censored_its.fit_censored_poisson (library only) uses WONDER counts hidden as 1-9 as interval
information without estimating them (under-covered .84-.86, though better than dropping them).
Time series: the interrupted_series tool (Round 64; full profile; census.missing_censored_its.interrupted_series)
for ANNUAL series, never overlapping ACS five-year releases (20-point series: every Round 42 method
under-covered, .47-.81).
Round 48: interrupted_series(method="bootstrap_t") is validated for 30+ annual points
(.883-.896). Round 55: method="bootstrap_t_bc" (bootstrap series at a bias-corrected AR
coefficient) is validated for 20+ points (.867-.889). Round 63: method="bootstrap_t_cons"
(critical values at least the t(n - p - 1) quantile) is validated for 17+ points; at 15 points
every method failed (.849-.855), and the EWC HAR test failed (.61-.72).

Round 76: disparities between population groups within an area (race/ethnicity, sex): the disparity_measures
tool (full profile) or manifest method "disparity" (groups = one rate per mutually exclusive group, populations,
reference declared in advance; list left-out groups in omitted_groups). Report absolute (rd, bgv) and relative
(log_rr, idisp, theil, mld) measures together. Validated: ACS rd and idisp up to a largest group-rate CV of .50,
log_rr/bgv/theil/mld up to .30; counts (Poisson, known populations) rd and log_rr with 20+ events per group (count
idisp/bgv/theil/mld failed, .07-.84: exploratory); 2-6 groups. Kitagawa rate/composition decomposition (manifest
"kitagawa", or disparity_measures(decompose_areas=[a, b])) validated to stratum CV .50 and 20+ events per stratum.

Round 79: decompose_gap (full profile) splits a PUMS gap between two mutually exclusive groups into explained
(composition) and unexplained parts: Oaxaca-Blinder (model="linear") or Fairlie (model="logit", 0/1 outcome), with
SDR replicate-weight intervals. Validated: Oaxaca-Blinder totals from 300 records in the smaller group; detailed
contributions and all Fairlie quantities from 1,000 (.80-.85 at 300). "Explained" is composition, not a causal effect.

Round 78: policies adopted in different years (staggered adoption) in an ANNUAL panel (ACS 1-year with
product="1-year", 2020 refused, or another annual source): difference_in_differences(design="staggered",
first_treated="<column>"). Sun-Abraham (default) is validated (.881-.899, 51 units); method="callaway_santanna" is
validated only with the se column (ACS variance added, .882-.906; without it .848-.868, exploratory). Uniform bands
are descriptive. Synthetic control for one treated unit failed (placebo size .12-.19 at .10): library only,
exploratory. Five-year releases are refused for staggered designs.

Round 77: the joinpoint tool (full profile) describes where an ANNUAL rate series changed trend without a pre-set
date (for a known policy date use interrupted_series). The number of joinpoints is validated (Kim et al. permutation
tests, false-joinpoint rate .012-.023); APC and AAPC intervals failed (.51-.91, joinpoint locations are estimated):
report them as exploratory. Complete years only; overlapping ACS five-year releases refused. joinpoint(rate_ratio=...)
gives the ratio of two directly age-adjusted rates with the Tiwari interval (validated .900-.921).
"""
# END GENERATED RULES A

_INSTR_MID = """Count outcomes without explicit spatial-cluster inference: binomial trials=<name>_denominator
and scale:"robust"; Poisson counts use exposure
and scale:"robust". New external-count manifests refuse scale:"X2" (failed coverage validation).

Inequality and standardized ratios (get_recipe('health_inequality'); existing manifest tools):
method inequality requires outcome/rank_by/positive weights and args.higher_is_more_deprived
(boolean); hypotheses name sii/log_rii/concentration_index only, without term. Ridits run
least to most deprived; positive indices mean higher outcomes among more deprived areas.
Concentration has the reverse sign of the usual income-ranked convention. Default target
conservative combines HC3 and ACS replicate SEs; median rank CV <=15% is validated, above
which warn about rank-error attenuation. External outcomes and their denominator weights
stay fixed; target these_areas is refused for external outcomes. R2 tests rank_by.
method smr requires observed integer counts, distinct population_bands, positive reference_rates
(events per person-year, in band order), and reference_source (hashed citation). Hypothesis log_smr
uses geoid (one GEOID or all); pooled ratios sum observed and expected counts first.
Log statistics test zero; ratio columns exponentiate estimates and limits. SMR target is
conservative only: tests combine Poisson and expected-count replicate log variance; exact
Garwood limits condition on expected counts. No replicates means zero expected uncertainty,
noted; O=0 has only the exact fixed-E interval. period_years (positive integer, default 1)
scales E for annual rates. Positive integer reference_counts adds sum((E_b/E)^2/D_b) to log
variance; zero reference deaths refused. Both fields hashed. Without counts, reference
rates are fixed. Reference person-years are fixed unless args.reference_population_se gives
their survey SEs (Round 55; validated). Pool band contributions before
squaring because reference rates are shared across areas. Internal-reference covariance
omission is conservative, noted, not refused. Negative band replicates are refused unless
args.negative_replicates is "accept" or "clip" (both validated in Round 51)."""

# BEGIN GENERATED RULES B (scripts/sync_rule_text.py; source: docs/agent_protocol.md <!-- mcp-rules:B --> paragraphs)
_RULES_B = """
Round 29 manual WONDER references: all county and national files are manual
exports; the engine never contacts WONDER. `acs_age_sex_bands` builds the fixed
20-band B01001 order (male youngest–oldest, then female). `smr` may replace literal
rates/counts with `reference_export: {file, sha256}`; `period_years` must match the
footer. Optional `ages_under: 75` selects the registered under-75 standard.
National suppressed reference cells are refused after dropping Not Stated;
state references require explicit `state` registration and are refused at runtime
if suppressed. No invented reference counts. `expected_count` derivations use
the same population bands, pinned reference and period, including ACS replicates.
Poisson offsets remain fixed during regression refits; reference-aware SMR
combined intervals provide the separate sensitivity, not corrected slope inference.
Matched suppressed outcomes are distinct from unmatched GEOIDs and unsuppressed
missing outcomes. Complete-case regressions/SMRs exclude suppressed counties,
record county IDs and [n,9n] excluded-death bounds. EB is descriptive only.
WONDER outputs: no sub-national counts 1–9 or values derived from them; no raw
exports in the repo or releases. Keep study states only, omit national death-count
vectors/complementary totals, mask censored counties in every product and run
`census.wonder_outputs.audit_outputs` before packaging. Sensitivity endpoint
assignments stay internal and output coefficients only; they are not strict bounds.
"""
# END GENERATED RULES B

_INSTR_TAIL = """SMR refuses negative ACS band replicates under its fixed validation domain, even with positive E.
Area HC3 assumes independence. R1 applies to external outcomes/counts. Reused LBW associations
are exploratory. No new tools are needed.


Round 27: get_recipe("small_area") distinguishes ACS Fay-Herriot estimates from descriptive
Python-library eb_poisson_gamma event-count smoothing. No new MCP tool or manifest smoothing
method. Preserve WONDER interval-censored counts, fixed expected counts and validation metadata;
never invent suppressed counts or ACS MOEs from EB limits. Posterior 90% and 200-refit
Laird-Louis intervals passed; reference-rate and spatial uncertainty are excluded.
cr(x,df=3|4|5) and joint_wald FAILED the fixed false-positive criterion: exploratory only,
confirmatory manifests refused, except binomial/Poisson cr tested with joint_test (Round 31). Only non-spatial fit_replicate OLS/WLS/binomial/Poisson;
centered full-sample knots stay fixed. Joint hypotheses use variable, no term, two_sided
(or two-sided); R2 applies to variable. HC3/sampling/summed covariance matches target.
Singular covariance is not tested; W is chi-squared(q), with df, no coefficient CI or odds
ratio. See get_research_protocol for scope, covariance metadata and limitations.


Round 28 segregation: get_recipe("segregation"), then existing manifest tools. Tract groups
are mutually exclusive counts, within county; no metro/pre-aggregation. Defaults are
bias-corrected (Round 50). Failed overrides (naive isolation/H since Round 52) and H with six
or more groups are exploratory only.
Strict 80 tract/group replicates; no missing counts held fixed. Negative replicate counts
are refused unless args.negative_replicates is "clip" (Round 51: validated for the
bias-corrected versions). Zero tracts recomputed per refit, absent groups undefined. Hypotheses
need geoid plus explicit null_value for one area; compare_geoid uses per-replicate
differences. release/compare_release select independent non-overlapping five-year releases;
variances add; such release contrasts are validated only with two groups and a larger
noise level below .50 (Round 52); same-release county contrasts likewise, except corrected
D (Round 57). args.group_quarters {gq, total, max_share} leaves out group-quarters tracts. First minus comparison; one-sided tests center on null.
A county is validated with 5+ populated tracts when its noise level (largest group median
tract CV) is in range (Rounds 50/52/66: bias-corrected D [.15, .75), isolation finite, H below
1 for two groups, .50 for three, finite for four to six) or every tract CV is <= .15
(Round 28); otherwise exploratory and confirmatory tests on it are refused. See protocol.


Inflation: default index is R-CPI-U-RS (the Census Bureau's ACS index); 'c-cpi-u'
matches CPS ASEC income reports. Never pass guessed values via cpi_table.
Branch on error_code in failed results.
Call get_research_protocol for the full protocol; get_recipe for short step lists.
"""

INSTRUCTIONS = "\n\n".join((_INSTR_HEAD, _RULES_A.strip("\n"), _INSTR_MID, _RULES_B.strip("\n"), _INSTR_TAIL))

mcp = FastMCP("US-Census-ACS-Downloader", instructions=INSTRUCTIONS)


def _tool(fn: Any) -> Any:
    """Register ``fn`` as an MCP tool behind the one integrity boundary: a
    bundled data/metadata checksum failure anywhere below returns
    BUNDLED_DATA_INTEGRITY instead of escaping or being misreported."""
    mcp.tool()(integrity_errors(fn))
    return fn


def _default_year(dataset: str = "acs5") -> int:
    return latest_vintage(dataset) or 2024


def _client(use_cache: bool = True) -> CensusAPIClient:
    return CensusAPIClient(cache=get_default_cache() if use_cache else None)


def _options(**kwargs: Any) -> ResearchOptions:
    return ResearchOptions(**{k: v for k, v in kwargs.items() if v is not None})


def _entities_for(
    geo_level: str,
    state_code: Optional[str],
    place_codes: Optional[List[str]],
    county_codes: Optional[List[str]],
    zcta_codes: Optional[List[str]],
    msa_codes: Optional[List[str]],
    include_pr: bool = False,
) -> Any:
    codes: Optional[List[str]] = None
    names: Dict[str, str] = {}
    if geo_level == "place":
        codes = place_codes
        places_file = None if is_nationwide(state_code) else get_local_places_file(state_code or "")
        if places_file and os.path.exists(places_file):
            names = {p[1]: p[2] for p in load_places_from_local(places_file)}
    elif geo_level in ("county", "tract", "block"):
        codes = county_codes
    elif geo_level == "zcta":
        codes = zcta_codes
    elif geo_level == "msa":
        codes = msa_codes
    return build_entities(geo_level, state_code, codes, names, include_pr=include_pr)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@_tool
def get_research_protocol() -> Dict[str, Any]:
    """Return the full agent protocol: extraction workflow, concordance modes,
    issue kinds, the draft/independent-review process for overrides and rules,
    derived statistics (approximate vs replicate MOEs, medians, multiple
    comparisons), geography changes, and validation against Census values."""
    with open(PROTOCOL_PATH, encoding="utf-8") as f:
        protocol = f.read()
    rules_path = os.path.join(ROOT, "docs", "rule_overrides.md")
    rules = ""
    if os.path.exists(rules_path):
        with open(rules_path, encoding="utf-8") as f:
            rules = f.read()
    return {"path": PROTOCOL_PATH, "protocol": protocol, "rule_overrides": rules}


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------


@_tool
def list_states() -> List[Dict[str, str]]:
    """List all supported US states and territories with their 2-digit FIPS codes."""
    return [
        {"state_code": code, "state_name": name}
        for code, name in sorted(STATE_MAPPING.items(), key=lambda x: x[1])
    ]


@_tool
@integrity_errors
def list_vintages(dataset: str = "acs5", refresh: bool = False) -> Dict[str, Any]:
    """List ACS 5-year release years available for a dataset.

    Args:
        dataset: 'acs5' (detailed), 'profile', 'subject', or 'cprofile'.
        refresh: Also query the live Census API catalog for releases newer than
            the offline metadata archive.
    """
    years = available_vintages(dataset, _client() if refresh else None, refresh)
    return {
        "dataset": dataset,
        "years": years,
        "archived_years": archived_vintages(dataset),
        "not_in_archive": sorted(set(years) - set(archived_vintages(dataset))),
    }


@_tool
def list_places(
    state_code: str, search: str = "", limit: int = 100
) -> List[Dict[str, str]]:
    """List incorporated places, cities, towns, and CDPs for a state FIPS code.

    Args:
        state_code: 2-digit state FIPS code (e.g. '36' for New York, '48' for Texas).
        search: Optional substring query to filter place names (case-insensitive).
        limit: Maximum number of places to return (default: 100).
    """
    places_file = get_local_places_file(state_code)
    if not places_file or not os.path.exists(places_file):
        return []
    results: List[Dict[str, str]] = []
    query = search.strip().lower()
    for p in load_places_from_local(places_file):
        if not query or query in p[2].lower():
            results.append(
                {
                    "state_code": p[0],
                    "place_code": p[1],
                    "place_name": p[2],
                    "place_type": p[3],
                    "counties": p[4],
                    "geoid": f"{p[0]}{p[1]}",
                }
            )
            if len(results) >= limit:
                break
    return results


@_tool
def list_counties(state_code: str, year: Optional[int] = None) -> List[Dict[str, str]]:
    """List counties (name + 3-digit FIPS + 5-digit GEOID) in a state.

    Uses the Census API; falls back to county codes from zip2fips.json offline.
    """
    rows = _client().list_geographies(year or _default_year(), "county", state_code=state_code)
    if rows:
        return sorted(
            (
                {
                    "county_code": r.get("county", ""),
                    "county_name": r.get("NAME", ""),
                    "geoid": f"{r.get('state', '')}{r.get('county', '')}",
                }
                for r in rows
            ),
            key=lambda r: r["county_code"],
        )
    return [
        {"county_code": c, "county_name": "", "geoid": f"{state_code}{c}"}
        for c in counties_for_state(state_code)
    ]


@_tool
def list_tracts(
    state_code: str, county_code: str, year: Optional[int] = None
) -> Dict[str, Any]:
    """List all Census tracts (summary level 140) in a county with 11-digit GEOIDs.

    Args:
        state_code: 2-digit state FIPS (e.g. '36').
        county_code: 3-digit county FIPS (e.g. '061' for New York County).
        year: ACS release; 2020+ uses 2020 Census tracts, 2019 and earlier 2010 tracts.
    """
    year = year or _default_year()
    client = _client()
    rows = client.list_geographies(year, "tract", state_code=state_code, county_code=county_code)
    if not rows:
        return errors.error_result(
            errors.API_HTTP_ERROR, client.last_error or "No tracts returned.", tracts=[]
        )
    tracts = sorted(
        (
            {
                "tract_code": r.get("tract", ""),
                "name": r.get("NAME", ""),
                "geoid": f"{r.get('state', '')}{r.get('county', '')}{r.get('tract', '')}",
            }
            for r in rows
        ),
        key=lambda r: r["geoid"],
    )
    return {
        "success": True,
        "state_code": state_code,
        "county_code": county_code,
        "year": year,
        "tract_count": len(tracts),
        "tracts": tracts,
    }


@_tool
def list_zctas(
    state_code: Optional[str] = None,
    county_code: Optional[str] = None,
    zip_code: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """List ZIP Code Tabulation Areas in a state/county, or resolve a ZIP code.

    Uses the bundled zip2fips.json crosswalk (ZIP -> primary county).

    Args:
        state_code: 2-digit state FIPS (e.g. '48').
        county_code: Optional 3-digit county FIPS to narrow results.
        zip_code: Resolve a single 5-digit ZIP to its state/county instead.
        limit: Maximum ZCTAs returned (default 500).
    """
    if zip_code:
        resolved = resolve_zip(zip_code)
        if not resolved:
            return errors.error_result(errors.INVALID_INPUT, f"ZIP code {zip_code} not found.")
        return {"success": True, "resolved": resolved}
    if not state_code:
        return errors.error_result(errors.INVALID_INPUT, "Provide state_code or zip_code.")
    zctas = zctas_for_state(state_code, county_code)
    return {
        "success": True,
        "state_code": state_code,
        "county_code": county_code,
        "zcta_count": len(zctas),
        "zctas": zctas[:limit],
        "has_more": len(zctas) > limit,
        "note": "ZIP codes are USPS routes; ZCTAs approximate them. PO-box-only "
        "ZIPs have no ZCTA and return no Census data.",
    }


@_tool
@integrity_errors
def search_tables(
    query: str, limit: int = 25, year: Optional[int] = None, dataset: Optional[str] = None
) -> Union[List[Dict[str, str]], Dict[str, Any]]:
    """Search ACS 5-year tables (detailed, data profile, subject, comparison profile)
    by code or keyword.

    Args:
        query: Table code (e.g. 'B01001', 'DP03', 'S1701') or keyword (e.g. 'poverty').
        limit: Maximum number of matching tables to return (default: 25).
        year: Release to search (default: latest archived release).
        dataset: Search one dataset only, e.g. 'dec/dhc' or 'dec/pl' (2020 Census).
    """
    all_tables: Dict[str, str] = {}
    for ds in (dataset,) if dataset else ("acs5", "profile", "subject", "cprofile"):
        catalog = load_table_catalog(ds, year) or DATASET_TABLES.get(ds, {})
        all_tables.update(catalog)
    q = query.strip().lower()
    matches: List[Dict[str, str]] = []
    for code, desc in sorted(all_tables.items()):
        if q in code.lower() or q in desc.lower():
            matches.append({"table_code": code, "description": desc, "dataset": dataset or infer_dataset(code)})
            if len(matches) >= limit:
                break
    return matches


@_tool
@integrity_errors
def list_variables(
    table_code: str, year: Optional[int] = None, limit: int = 50, dataset: Optional[str] = None
) -> Dict[str, Any]:
    """List a table's variables and labels for one release.

    Args:
        table_code: ACS table code (e.g. 'B01001', 'DP02'), or a 2020 Census table
            with dataset='dec/dhc' / 'dec/pl' (e.g. 'P12').
        year: Release year (default: latest archived). Labels and codes differ
            between releases.
        limit: Maximum variables returned (default 50).
        dataset: Override the inferred endpoint (e.g. 'dec/dhc').
    """
    dataset = dataset or infer_dataset(table_code)
    year = year or _default_year(dataset)
    variables, source = table_variables(table_code, dataset, year, _client())
    items = sorted(variables.items())
    return {
        "table_code": table_code,
        "dataset": dataset,
        "year": year,
        "metadata_source": source,
        "universe": table_universe(table_code, dataset, year),
        "total_variables": len(items),
        "variables": [{"code": c, "label": m["label"]} for c, m in items[:limit]],
        "has_more": len(items) > limit,
    }


@_tool
@integrity_errors
def describe_variable(code: str, year: Optional[int] = None, dataset: Optional[str] = None) -> Dict[str, Any]:
    """Label, concept, table, and universe for one variable code in one release.

    Use this to confirm what a code means in each year before pooling years.

    Args:
        code: Variable code (e.g. 'DP02_0016PE', 'B19013_001E', or a 2020 Census
            count such as 'P12_002N').
        year: Release year (default: latest archived).
        dataset: Override the inferred endpoint ('dec/dhc' or 'dec/pl' for the 2020
            Census; '<code>N' codes default to 'dec/dhc').
    """
    return _describe_variable(code, year, dataset=dataset, client=_client())


# ---------------------------------------------------------------------------
# Data tools
# ---------------------------------------------------------------------------


@_tool
@integrity_errors
def fetch_table_data(
    year: int,
    state_code: Optional[str],
    table_code: str,
    geo_level: str = "place",
    place_code: Optional[str] = None,
    county_code: Optional[str] = None,
    tract_code: Optional[str] = None,
    zcta_code: Optional[str] = None,
    msa_code: Optional[str] = None,
    dataset: Optional[str] = None,
    compute_reliability: bool = False,
    clean_sentinels: bool = True,
    use_cache: bool = True,
    max_rows: int = 500,
) -> Dict[str, Any]:
    """Fetch one release of a table for one geography, with that release's labels.

    Single-year, so no concordance checks apply. To compare years, use
    plan_extraction and batch_download.

    Args:
        year: ACS 5-year end-year (e.g. 2022).
        state_code: 2-digit state FIPS code (e.g. '36'); not needed for 'us'/'msa'.
        table_code: Detailed ('B01001'), data profile ('DP03'), subject ('S1701')
            or comparison profile ('CP03') table code.
        geo_level: 'us', 'state', 'county', 'tract', 'place', 'zcta', or 'msa' ('block'
            with dataset='dec/pl', one state and county).
        place_code: Required if geo_level is 'place' (e.g. '51000' for New York city).
        county_code: County FIPS for 'county'/'tract' levels (default '*' = all).
        tract_code: Optional 6-digit tract code (default all tracts).
        zcta_code: ZCTA(s) for 'zcta' level, comma-separated (default '*').
        msa_code: CBSA code(s) for 'msa' level (default '*').
        dataset: 'acs5', 'profile', 'subject' or 'cprofile' (inferred if omitted), or the
            2020 Census 'dec/dhc' / 'dec/pl' (counts: no MOE; see `uncertainty`).
        compute_reliability: Add standard error, CV % and reliability columns.
        clean_sentinels: Replace Census jam values (-666666666 etc.) with null.
        use_cache: Read/write the local SQLite query cache.
        max_rows: Maximum rows returned in 'data' (default 500).
    """
    preflight_archives(dataset or infer_dataset(table_code), [year])
    client = _client(use_cache)
    try:
        raw_data = client.fetch(
            year=year,
            state_code=state_code,
            table_code=table_code,
            geo_level=geo_level,
            place_code=place_code,
            county_code=county_code,
            tract_code=tract_code,
            zcta_code=zcta_code,
            msa_code=msa_code,
            dataset=dataset,
        )
    except ValueError as exc:
        return errors.error_result(errors.INVALID_GEO_LEVEL, str(exc), data=[])

    if not raw_data or len(raw_data) < 2:
        code = errors.API_HTTP_ERROR if client.last_error else errors.NO_DATA
        return errors.error_result(
            code,
            f"No data returned for year {year}, table {table_code}, {geo_level} level. "
            f"{client.last_error or ''}".strip(),
            data=[],
        )

    dataset = dataset or infer_dataset(table_code)
    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
    df = df.loc[:, ~df.columns.duplicated()]  # NAME appears twice in group() calls
    df = add_geoid_column(df, geo_level)
    if clean_sentinels:
        df = clean_census_sentinels(df)
    if compute_reliability:
        df = add_reliability_columns(df)

    metadata = resolve_metadata(table_code, dataset, year, client)
    rename = {
        code: label
        for code, label in describe_columns(df.columns, metadata).items()
        if code not in IDENTIFIER_COLUMNS
    }
    formatted_df = df.rename(columns=rename)
    formatted_df = formatted_df.astype(object).where(pd.notna(formatted_df), None)

    decennial = is_decennial(dataset)
    return {
        "success": True,
        "year": year,
        "state_code": state_code,
        "table_code": table_code,
        "dataset": dataset,
        "geo_level": geo_level,
        "uncertainty": uncertainty_record(geo_level) if decennial else None,
        "advisories": [DISCLOSURE_AVOIDANCE_ADVISORY] if decennial else [],
        "row_count": len(formatted_df),
        "columns": list(formatted_df.columns),
        "data": formatted_df.head(max_rows).to_dict(orient="records"),
        "truncated": len(formatted_df) > max_rows,
    }


@_tool
def query_data_profile(
    profile_code: str,
    year: Optional[int] = None,
    state_code: Optional[str] = None,
    geo_level: str = "state",
    place_code: Optional[str] = None,
    county_code: Optional[str] = None,
    zcta_code: Optional[str] = None,
    msa_code: Optional[str] = None,
    compute_reliability: bool = False,
    max_rows: int = 500,
) -> Dict[str, Any]:
    """Query an ACS 5-year Data Profile with pre-computed rates and percentages.

    DP02 social, DP03 economic, DP04 housing, DP05 demographic. Percent values
    are the *PE columns, their MOEs the *PM columns.

    Args:
        profile_code: 'DP02', 'DP03', 'DP04' or 'DP05'.
        year: ACS 5-year end-year (default: latest archived).
        state_code: 2-digit state FIPS (required except for 'us' / 'msa' / 'zcta').
        geo_level: 'us', 'state', 'county', 'tract', 'place', 'zcta', or 'msa'.
        place_code / county_code / zcta_code / msa_code: Entity filters.
        compute_reliability: Add SE / CV / reliability columns.
        max_rows: Maximum rows returned.
    """
    code = profile_code.strip().upper()
    if code not in DATASET_TABLES["profile"]:
        return errors.error_result(
            errors.INVALID_INPUT,
            f"Unknown data profile '{profile_code}'. Choose from {sorted(DATASET_TABLES['profile'])}.",
        )
    result = fetch_table_data(
        year=year or _default_year("profile"),
        state_code=state_code,
        table_code=code,
        geo_level=geo_level,
        place_code=place_code,
        county_code=county_code,
        zcta_code=zcta_code,
        msa_code=msa_code,
        dataset="profile",
        compute_reliability=compute_reliability,
        max_rows=max_rows,
    )
    result["profile_title"] = DATASET_TABLES["profile"][code]
    return result


@_tool
def plan_extraction(
    state_code: Optional[str],
    table_code: str,
    start_year: int,
    end_year: int,
    geo_level: str = "state",
    variables: Optional[List[str]] = None,
    place_codes: Optional[List[str]] = None,
    county_codes: Optional[List[str]] = None,
    zcta_codes: Optional[List[str]] = None,
    msa_codes: Optional[List[str]] = None,
    output_format: str = "panel",
    dataset: Optional[str] = None,
    concordance_mode: str = "fail",
    continuity_check: bool = True,
    inflation_base_year: Optional[int] = None,
    price_index: str = "r-cpi-u-rs",
    include_pr: bool = False,
    allow_provisional_index: bool = False,
    harmonize_tracts_to: Optional[int] = None,
    product: str = "5-year",
    allow_experimental_2020: bool = False,
) -> Dict[str, Any]:
    """Dry run of batch_download: call counts, concordance issues, and whether it
    would block. Downloads no data (at most one cached national call per year for
    the continuity check). Arguments match batch_download.

    Read `selection` to confirm each variable resolved to the intended measure,
    and `issues` (blocking first) before downloading.
    """
    if start_year > end_year:
        return errors.error_result(errors.INVALID_INPUT, "start_year must be <= end_year.")
    try:
        entities = _entities_for(
            geo_level, state_code, place_codes, county_codes, zcta_codes, msa_codes, include_pr
        )
    except ValueError as exc:
        return errors.error_result(errors.INVALID_GEO_LEVEL, str(exc))
    plan = _plan_extraction(
        table_code,
        entities,
        list(range(start_year, end_year + 1)),
        output_format,
        _options(
            concordance_mode=concordance_mode,
            continuity_check=continuity_check,
            inflation_base_year=inflation_base_year,
            price_index=price_index,
            allow_provisional_index=allow_provisional_index,
            harmonize_tracts_to=harmonize_tracts_to,
            product=product,
            allow_experimental_2020=allow_experimental_2020,
        ),
        dataset,
        variables,
        _client(),
    )
    return public_plan(plan)


@_tool
def batch_download(
    state_code: Optional[str],
    table_code: str,
    start_year: int,
    end_year: int,
    geo_level: str = "place",
    variables: Optional[List[str]] = None,
    place_codes: Optional[List[str]] = None,
    output_format: str = "both",
    output_dir: Optional[str] = None,
    county_codes: Optional[List[str]] = None,
    zcta_codes: Optional[List[str]] = None,
    msa_codes: Optional[List[str]] = None,
    dataset: Optional[str] = None,
    concordance_mode: str = "fail",
    continuity_check: bool = True,
    allow_unverified_concordance: bool = False,
    clean_sentinels: bool = True,
    compute_reliability: bool = False,
    inflation_base_year: Optional[int] = None,
    price_index: str = "r-cpi-u-rs",
    include_codebook: bool = False,
    use_cache: bool = True,
    slug_style: str = "label",
    include_pr: bool = False,
    allow_provisional_index: bool = False,
    harmonize_tracts_to: Optional[int] = None,
    product: str = "5-year",
    allow_experimental_2020: bool = False,
) -> Dict[str, Any]:
    """Batch-download a table across years and geographies to research-ready files.

    Multi-year runs build columns by concept (not raw code) and, in the default
    'fail' mode, stop with CONCORDANCE_REVIEW_REQUIRED when selected variables have
    unresolved cross-release issues. Run plan_extraction first.

    Args:
        state_code: 2-digit state FIPS (e.g. '36'), or 'all' for every state + DC
            (county/place: one request per year; tract: one per state per year;
            omit codes). Optional for 'us', 'msa', 'zcta'.
        table_code: Table code ('B01001', 'DP03', 'S1701', 'CP03').
        start_year: Starting ACS 5-year end-year (e.g. 2015).
        end_year: Ending year (e.g. 2022).
        geo_level: 'us', 'state', 'county', 'tract', 'place', 'zcta', or 'msa'; the 2020
            Census also offers 'block group' and 'block' (block: dec/pl, or dec/dhc H1).
        variables: Codes the analysis uses ('B19013_001', '2018:DP02_0002', or concept
            IDs). Omitted = whole table, so any drift in the table can block.
        place_codes: Place FIPS codes (required for 'place').
        output_format: 'both', 'wide_only', 'melted_only', 'excel', 'panel' (tidy
            GEOID x Year CSV) or 'parquet'.
        output_dir: Destination folder (default 'downloads' in workspace root).
        county_codes: Counties for 'county' or 'tract' (omitted = all in state).
        zcta_codes: ZCTAs for 'zcta' (omitted = all ZIPs in state via zip2fips.json).
        msa_codes: CBSA codes for 'msa' (omitted = all metro/micro areas).
        dataset: 'acs5', 'profile', 'subject', 'cprofile' (inferred if omitted), or the
            2020 Census 'dec/dhc' (DHC) / 'dec/pl' (P.L. 94-171); years 2020 only.
        concordance_mode: 'fail' (default), 'strict' (exploration), or 'code' (legacy).
        continuity_check: Check national continuity of multi-year concepts.
        allow_unverified_concordance: Required for multi-year 'code' mode.
        clean_sentinels: Replace Census jam values (-666666666 etc.) with null.
        compute_reliability: Add SE, CV % and reliability columns per estimate.
        inflation_base_year: Convert dollar variables to constant dollars of this year.
        price_index: 'r-cpi-u-rs' (Census Bureau standard for ACS, default),
            'cpi-u', or 'c-cpi-u' (matches CPS ASEC income reports).
        include_codebook: Write <table>_codebook.csv alongside the data.
        use_cache: Use the local SQLite query cache (.cache/census_cache.db).
        slug_style: Panel column names: 'label' (readable) or 'code' (Stata-safe).
        include_pr: With state_code='all', also include Puerto Rico (72).
        allow_provisional_index: Allow index years built from fewer than 12
            published months (2025: October never published); adds an advisory.
        harmonize_tracts_to: 2010 or 2020: apportion a tract panel spanning the
            2010/2020 tract change to one tract vintage (panel/parquet only).
        product: "5-year" (default) or "1-year" (areas of 65,000+ people only;
            timelier, non-overlapping releases; never mix with 5-year in one comparison),
            or "decennial" (2020 Census DHC unless dataset='dec/pl'; counts are not
            sample-based: no MOE/SE/CV columns, a disclosure-avoidance advisory and an
            `uncertainty` record in the metadata).
        allow_experimental_2020: 1-year only: Census published no standard 2020
            1-year estimates; opt in to acknowledge the gap (2020 is skipped with an advisory).
    """
    if start_year > end_year:
        return errors.error_result(errors.INVALID_INPUT, "start_year must be <= end_year.")
    base_dir = output_dir or os.path.join(ROOT, "downloads")
    try:
        entities = _entities_for(
            geo_level, state_code, place_codes, county_codes, zcta_codes, msa_codes, include_pr
        )
    except ValueError as exc:
        return errors.error_result(errors.INVALID_GEO_LEVEL, str(exc))
    options = _options(
        allow_provisional_index=allow_provisional_index,
        harmonize_tracts_to=harmonize_tracts_to,
            product=product,
            allow_experimental_2020=allow_experimental_2020,
        clean_sentinels=clean_sentinels,
        compute_reliability=compute_reliability,
        inflation_base_year=inflation_base_year,
        price_index=price_index,
        include_codebook=include_codebook,
        use_cache=use_cache,
        slug_style=slug_style,
        concordance_mode=concordance_mode,
        continuity_check=continuity_check,
        allow_unverified_concordance=allow_unverified_concordance,
    )
    return run_batch(
        table_code=table_code,
        entities=entities,
        years=list(range(start_year, end_year + 1)),
        output_dir=base_dir,
        output_format=output_format,
        options=options,
        dataset=dataset,
        variables=variables,
    )


# ---------------------------------------------------------------------------
# Concordance review tools
# ---------------------------------------------------------------------------


@_tool
@integrity_errors
def check_variable_concordance(
    table_code: str,
    start_year: int,
    end_year: int,
    variables: Optional[List[str]] = None,
    dataset: Optional[str] = None,
    include_nonblocking: bool = False,
    limit: int = 100,
) -> Dict[str, Any]:
    """Report how a table's variables line up across releases, with evidence.

    Offline (uses the metadata archive); no continuity check (plan_extraction
    adds that). Use this to draft override decisions: each issue lists the
    concept IDs, codes, labels per year, and label similarity.

    Args:
        table_code: e.g. 'DP02', 'S1701', 'B27001'.
        start_year, end_year: Release range.
        variables: Limit to these codes / YEAR:CODE / concept IDs (default: all).
        dataset: Override the inferred endpoint.
        include_nonblocking: Also list informational issues (redefined, etc.).
        limit: Maximum issues and concepts returned.
    """
    dataset = dataset or infer_dataset(table_code)
    conc = build_concordance(table_code, dataset, list(range(start_year, end_year + 1)), _client())
    override_report = apply_overrides(conc)
    selected, unknown, resolution = conc.explain_selection(variables)
    if unknown:
        return errors.error_result(
            errors.INVALID_VARIABLES, f"Not found: {unknown}", unknown_variables=unknown
        )
    issues = [
        i.to_dict()
        for i in conc.issues_for(selected)
        if include_nonblocking or i.kind in BLOCKING_KINDS
    ]
    reps = conc.representative_bases()
    concepts = [
        {
            "concept_id": cid,
            "panel_base": reps[cid],
            "label": conc.concepts[cid].canonical,
            "codes_by_year": {str(y): conc.concepts[cid].codes[y] for y in conc.concepts[cid].years},
            "statuses": conc.concepts[cid].statuses,
        }
        for cid in sorted(selected, key=lambda k: reps.get(k, k))
    ]
    return {
        "success": True,
        "summary": conc.summary(),
        "selection": resolution,
        "issues": issues[:limit],
        "issue_count": len(issues),
        "concepts": concepts[:limit],
        "concept_count": len(concepts),
        "overrides": override_report,
    }


@_tool
def draft_crosswalk_override(
    table_code: str,
    entries: List[str],
    decision: str,
    drafted_by: str,
    rationale: str,
    source_url: str = "",
    target_concept_id: str = "",
    dataset: Optional[str] = None,
) -> Dict[str, Any]:
    """Draft an override decision with machine-generated evidence (step 1 of 2).

    Saves evidence to crosswalks/evidence/ and returns draft rows with an empty
    reviewed_by. A DIFFERENT reviewer must then call record_crosswalk_review.

    Args:
        table_code: e.g. 'B27001'.
        entries: The (year, code) cells covered, as 'YEAR:CODE' strings.
        decision: 'merge', 'split', or 'exclude'. Prefer 'split' when unsure.
        drafted_by: Your identity, 'agent:<model>/<session>' or 'human:<name>'.
        rationale: Why, citing what the source says.
        source_url: census.gov primary source (required for merge).
        target_concept_id: For merge: the concept to merge into (from
            check_variable_concordance).
        dataset: Override the inferred endpoint.
    """
    dataset = dataset or infer_dataset(table_code)
    parsed = []
    for entry in entries:
        try:
            year, code = entry.split(":", 1)
            parsed.append((int(year), code.strip()))
        except ValueError:
            return errors.error_result(errors.INVALID_INPUT, f"Entry '{entry}' must be 'YEAR:CODE'.")
    try:
        draft = draft_override(
            table_code, dataset, parsed, decision, drafted_by, rationale,
            source_url, target_concept_id, client=_client(),
        )
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, str(exc))
    return {"success": True, **draft}


@_tool
def record_crosswalk_review(
    row: Dict[str, str],
    reviewed_by: str,
    table_code: str,
    dataset: Optional[str] = None,
) -> Dict[str, Any]:
    """Approve a drafted override row as an independent reviewer (step 2 of 2).

    Only call this after re-checking the evidence and the census.gov source
    yourself. reviewed_by must differ from the row's drafted_by. The row is
    validated against all review requirements before it is written.

    Args:
        row: One draft row returned by draft_crosswalk_override.
        reviewed_by: Your identity, 'agent:<model>/<session>' or 'human:<name>'.
        table_code: The table the row belongs to.
        dataset: Override the inferred endpoint.
    """
    dataset = dataset or infer_dataset(table_code)
    return record_override(row, reviewed_by, dataset, table_code, client=_client())


@_tool
def validate_crosswalks() -> Dict[str, Any]:
    """Validate every committed override file against the review requirements."""
    return validate_all_crosswalks(_client())


# ---------------------------------------------------------------------------
# Research statistics tools
# ---------------------------------------------------------------------------


@_tool
def calculate_cv(estimate: float, moe: float, product: Optional[str] = None) -> Dict[str, Any]:
    """Standard error, coefficient of variation and reliability for an ACS estimate.

    SE = MOE / 1.645; CV = SE / estimate x 100.
    Reliability: High (CV <= 15%), Moderate (15-30%), Low (> 30%).

    Args:
        estimate: The ACS estimate.
        moe: Its published 90% margin of error.
        product: 'decennial' is refused: 2020 Census counts have no sampling MOE.
    """
    try:
        return _calculate_cv(estimate, moe, product=product)
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, str(exc))


@_tool
def calculate_significance(
    est1: float,
    moe1: float,
    est2: float,
    moe2: float,
    confidence_level: float = 0.90,
    year1: Optional[int] = None,
    year2: Optional[int] = None,
    product: str = "5-year",
    product2: Optional[str] = None,
) -> Dict[str, Any]:
    """Two-tailed Z-test for whether two ACS estimates differ significantly.

    Z = |X1 - X2| / sqrt(SE1^2 + SE2^2). When year1 and year2 are both given
    (same geography, different 5-year periods), the Census overlapping-sample
    adjustment sqrt(1 - overlap/5) is applied to the SE of the difference.

    Args:
        est1, moe1: First estimate and its 90% MOE.
        est2, moe2: Second estimate and its 90% MOE.
        confidence_level: 0.90, 0.95 or 0.99 (default 0.90, the ACS standard).
        year1, year2: Optional ACS end years for the overlap adjustment.
        product: '5-year' (default) or '1-year' (1-year releases never overlap).
            'decennial' alone is refused (census counts are not sample-based).
        product2: Product of the second value when it differs: 'decennial' tests the
            ACS estimate against a 2020 Census count as a fixed reference (moe2=0);
            the result notes that only ACS sampling error is measured.
    """
    second = product2 or product
    try:
        both_acs = not (is_decennial(product) or is_decennial(second))
        overlap = acs_overlap_years(year1, year2, product, second) if year1 and year2 and both_acs else 0
        return z_test(est1, moe1, est2, moe2, confidence_level, overlap_years=overlap,
                      product1=product, product2=second)
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, str(exc))


@_tool
def adjust_inflation(
    value: float,
    from_year: int,
    to_year: int,
    index: str = "r-cpi-u-rs",
    allow_provisional: bool = False,
) -> Dict[str, Any]:
    """Convert a dollar value between years with an annual price index.

    Args:
        value: Dollar amount in from_year dollars (e.g. 2012 ACS median income).
        from_year: Year of the original dollars (the ACS period end year).
        to_year: Target constant-dollar year.
        index: 'r-cpi-u-rs' (Census Bureau standard for ACS, default), 'cpi-u', or
            'c-cpi-u' (CPS ASEC income reports).
        allow_provisional: Use a year whose annual figure rests on fewer than 12
            published months (2025); the result carries an advisory.
    """
    if index not in PRICE_INDEXES:
        return errors.error_result(errors.INVALID_INPUT, f"index must be one of {PRICE_INDEXES}.")
    try:
        adjusted = _adjust_inflation(value, from_year, to_year, index=index, allow_provisional=allow_provisional)
    except PriceIndexUnavailable as exc:
        return errors.error_result(errors.PRICE_INDEX_UNAVAILABLE, str(exc.args[0]))
    except BundledDataIntegrityError as exc:
        return integrity_error_result(exc)
    table = load_price_index(index, allow_provisional=allow_provisional)
    info = price_index_info(index)
    custom = {"custom_table": info["custom_table"]} if "custom_table" in info else {}
    return {
        "advisory": provisional_advisory(index, [from_year, to_year]) if allow_provisional else None,
        "success": True,
        "value": value,
        "from_year": from_year,
        "to_year": to_year,
        "index": index,
        "index_from": table[from_year],
        "index_to": table[to_year],
        "adjusted_value": adjusted,
        "source": info.get("source", ""),
        **custom,
    }


@_tool
@integrity_errors
def generate_codebook(
    table_code: str,
    year: Optional[int] = None,
    dataset: Optional[str] = None,
    include_moe: bool = True,
    include_reliability: bool = False,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit a machine-readable data dictionary for one release of a table.

    Columns: Variable_Code, Variable_Slug, Measurement_Type, Full_Description,
    Concept, Universe, Unit. For multi-year panels, use batch_download with
    include_codebook=True, which adds concordance columns.

    Args:
        table_code: e.g. 'B19013', 'DP03', 'S1701'.
        year: Release year (default: latest archived).
        dataset: Override endpoint ('acs5', 'profile', 'subject', 'cprofile', or the 2020
            Census 'dec/dhc' / 'dec/pl': counts only, with an Uncertainty column).
        include_moe: Include margin-of-error variables.
        include_reliability: Include derived SE / CV / reliability columns.
        output_path: Optional CSV path to also write the codebook to.
    """
    dataset = dataset or infer_dataset(table_code)
    year = year or _default_year(dataset)
    metadata = resolve_metadata(table_code, dataset, year, _client())
    if not metadata:
        return errors.error_result(
            errors.METADATA_UNAVAILABLE, f"No variable metadata for {table_code} in {year}."
        )

    columns: List[str] = []
    for code in sorted(metadata):
        if is_decennial(dataset) and code.endswith("N"):
            columns.append(code)  # 2020 Census count: no MOE or reliability columns exist
            continue
        if code.endswith("PE"):
            base, moe, pct = code[:-2], f"{code[:-2]}PM", True
        elif code.endswith("E") and not code.endswith("EA"):
            base, moe, pct = code[:-1], f"{code[:-1]}M", False
        else:
            continue
        columns.append(code)
        if include_moe:
            columns.append(moe)
        if include_reliability:
            key = f"{base}P" if pct else base
            columns += [f"{key}_SE", f"{key}_CV", f"{key}_RELIABILITY"]

    codebook = _generate_codebook(
        columns, metadata, universe=table_universe(table_code, dataset, year),
        decennial=is_decennial(dataset),
    )
    if output_path:
        codebook.to_csv(output_path, index=False, encoding="utf-8")
    return {
        "success": True,
        "table_code": table_code,
        "dataset": dataset,
        "year": year,
        "variable_count": len(codebook),
        "output_path": output_path,
        "codebook": codebook.to_dict(orient="records"),
    }



# ---------------------------------------------------------------------------
# Round 7: derived statistics, replicate variance, medians, testing, geography
# (implemented in census.workflows, shared with the CLI)
# ---------------------------------------------------------------------------

for _fn in (
    workflows_verification.verify_proposition,
    workflows.derive_estimate,
    workflows.check_replicate_availability,
    workflows.aggregate_geographies,
    workflows.median_from_distribution,
    workflows.batch_significance,
    workflows.apportion_tracts,
    workflows.replay_extraction,
    workflows.draft_rule_override,
    workflows.record_rule_review,
    workflows.run_validation,
    workflows.download_table,
    workflows.cache_import,
    workflows_inference.build_analysis_frame,
    workflows_inference.fit_model,
    workflows_inference.compare_groups,
    workflows_inference.rank_areas,
    workflows_inference.build_index,
    workflows_inference.check_agreement,
    workflows_inference.combine_estimates,
    workflows_inference.estimate_effect,
    workflows_inference.small_area_estimates,
    workflows_inference.correlation_matrix,
    workflows_inference.minimum_detectable_difference,
    workflows_inference.reliability_profile,
    workflows_inference.trend_test,
    workflows_inference.interrupted_series,
    workflows_inference.disparity_measures,
    workflows_inference.joinpoint,
    workflows_microdata.decompose_gap,
    workflows_inference.make_figure,
    workflows_inference.make_table,
    workflows_inference.make_results_bundle,
    recipes.get_recipe,
    workflows_inference.create_manifest,
    workflows_inference.list_health_sources,
    workflows_inference.run_variant,
    workflows_inference.run_manifest,
    workflows_geo.get_boundaries,
    workflows_geo.make_map,
    workflows_geo.spatial_autocorrelation,
    workflows_geo.spatial_regression,
    workflows_geo.spatial_small_area_estimates,
    workflows_geo.custom_area_mapping,
    workflows_microdata.pums_tabulate,
    workflows_microdata.test_association,
    workflows_microdata.pums_regression,
    workflows_microdata.multilevel_model,
    workflows_microdata.difference_in_differences,
    workflows_microdata.adjust_for_place,
    workflows_microdata.place_adjust_frame,
    workflows_microdata.make_web_map,
):
    _tool(_fn)

# Module-level names so tests and callers can use mcp_server.<tool>(...).
derive_estimate = workflows.derive_estimate
check_replicate_availability = workflows.check_replicate_availability
aggregate_geographies = workflows.aggregate_geographies
median_from_distribution = workflows.median_from_distribution
batch_significance = workflows.batch_significance
apportion_tracts = workflows.apportion_tracts
replay_extraction = workflows.replay_extraction
draft_rule_override = workflows.draft_rule_override
record_rule_review = workflows.record_rule_review
run_validation = workflows.run_validation
download_table = workflows.download_table
cache_import = workflows.cache_import
build_analysis_frame = workflows_inference.build_analysis_frame
fit_model = workflows_inference.fit_model
compare_groups = workflows_inference.compare_groups
rank_areas = workflows_inference.rank_areas
build_index = workflows_inference.build_index
check_agreement = workflows_inference.check_agreement
combine_estimates = workflows_inference.combine_estimates
estimate_effect = workflows_inference.estimate_effect
small_area_estimates = workflows_inference.small_area_estimates
correlation_matrix = workflows_inference.correlation_matrix
minimum_detectable_difference = workflows_inference.minimum_detectable_difference
reliability_profile = workflows_inference.reliability_profile
trend_test = workflows_inference.trend_test
interrupted_series = workflows_inference.interrupted_series
disparity_measures = workflows_inference.disparity_measures
joinpoint = workflows_inference.joinpoint
decompose_gap = workflows_microdata.decompose_gap
make_figure = workflows_inference.make_figure
make_table = workflows_inference.make_table
make_results_bundle = workflows_inference.make_results_bundle
create_manifest = workflows_inference.create_manifest
run_manifest = workflows_inference.run_manifest
list_health_sources = workflows_inference.list_health_sources
run_variant = workflows_inference.run_variant
get_boundaries = workflows_geo.get_boundaries
make_map = workflows_geo.make_map
spatial_autocorrelation = workflows_geo.spatial_autocorrelation
spatial_regression = workflows_geo.spatial_regression
spatial_small_area_estimates = workflows_geo.spatial_small_area_estimates
custom_area_mapping = workflows_geo.custom_area_mapping
pums_tabulate = workflows_microdata.pums_tabulate
test_association = workflows_microdata.test_association
pums_regression = workflows_microdata.pums_regression
multilevel_model = workflows_microdata.multilevel_model
difference_in_differences = workflows_microdata.difference_in_differences
adjust_for_place = workflows_microdata.adjust_for_place
place_adjust_frame = workflows_microdata.place_adjust_frame
make_web_map = workflows_microdata.make_web_map
get_recipe = recipes.get_recipe
verify_proposition = workflows_verification.verify_proposition


def server_for_profile(profile: str) -> FastMCP:
    """FastMCP server exposing one tool profile ('core', 'review', 'full');
    see census/mcp_profiles.py."""
    return mcp_profiles.build_profile_server(mcp, profile)


def main(argv: Optional[List[str]] = None) -> None:
    """Run the FastMCP server over standard I/O.

    ``--profile core|review|full`` (or env CENSUS_MCP_PROFILE) selects the tool
    set; default 'full'. Local models should use 'core'.
    """
    import sys

    profile = mcp_profiles.resolve_profile(sys.argv[1:] if argv is None else argv)
    server_for_profile(profile).run()


if __name__ == "__main__":
    main()

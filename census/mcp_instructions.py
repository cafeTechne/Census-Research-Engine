# SPDX-License-Identifier: AGPL-3.0-or-later
"""Server instruction text for mcp_server.py (extracted in Round 148; rule blocks synced by scripts/sync_rule_text.py)."""

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

Round 87: never apply an area-level result to individuals (ecologic fallacy). When a question is about people, run
pums_regression(..., ecologic_check="<exposure>") to compare the within-PUMA (individual) association with the
between-PUMA and area-level (ecologic) ones. The logit decomposition is validated from 5,000 records; the
risk-difference decomposition and the ecologic gap are exploratory. A contextual effect is not proof of an area cause.

Round 86: report an E-value with ratio estimates (bias_analysis kind="e_value"; also in stratified_analysis and the
marginal measures): the minimum unmeasured-confounder strength that would explain the estimate away. A 2 x 2 table
can be corrected for misclassification (kind="misclassification"); its probabilistic interval failed validation
(exploratory). For a covariable of uncertain causal direction, report results with and without it.

Round 85: a threshold designation on noisy ACS rates is a screening test. designation_accuracy (full profile) gives
each area's probability of truly exceeding the threshold (Fay-Herriot posterior; validated) and the expected
sensitivity, specificity, PPV and NPV of the point, lower-bound, probability-.5 and probability-.8 rules
(exploratory). Report any designated list with its rule's expected PPV and sensitivity.

Round 84: for common binary outcomes (above about 10%) odds ratios overstate risk ratios. Area binomial models:
fit_model(model="binomial", trials=..., marginal="<exposure>") adds the standardized risk ratio, risk difference and
attributable fraction (and dose_levels=5 a dose-response test). PUMS: pums_regression(model="logit",
marginal="<0/1 exposure>") adds the same plus the modified-Poisson prevalence ratio. All validated (.862-.898).

Round 83: stratified_analysis (full profile) gives crude, stratum-specific and Mantel-Haenszel pooled RR/OR/RD
(validated for counts from 5 expected cases per stratum-arm and for PUMS with replicate weights from 300 records per
stratum), the Breslow-Day OR homogeneity test (validated; the RR and PUMS homogeneity tests are exploratory), RERI
for additive interaction (validated) and a descriptive confounder/effect_modifier label (10% rule). Declare
covariable roles before analysis (manifest "covariables"): never adjust for a mediator; report effect modifiers by
stratum. get_recipe("confounding").

Round 82 (Foundations of Epidemiology): area analyses are ECOLOGIC (they describe areas, not individuals) and
CROSS-SECTIONAL (no temporal order): write "is associated with" / "times as high in ... compared with ...", never
"causes", "leads to" or "effect of" (except estimate_effect and DiD, which state their assumptions). Say whether
an outcome is a prevalence (ACS, PLACES) or an incidence rate (WONDER per person-year), with units and period.
An interval that includes the null means "no evidence of a difference", not "no difference". Report allocation
(imputation) shares above 5% (reliability_profile allocation_tables) and give a Table 1 (make_table kind="table1").

Round 81: spatial_scan (full profile) finds clusters of counties with high event counts (Kulldorff Poisson scan).
The primary-cluster p-value is validated with windows up to 50% of the expected total and 999 replicates (size
.099-.116 at .10). Denominators must be exact: ACS-estimated denominators inflate false clusters (.15-.53), and a
denominator _se column (median CV > .01) makes it exploratory. Descriptive unless prespecified=True. Suppressed
WONDER counties must be excluded with a stated rule; counts are never imputed.

Round 80: small_area_estimates(transform="arcsine") for proportions near 0 or 1 (bias-corrected back-transform,
bootstrap MSE; validated .898-.904 per area on MI/NY counties and tracts) and small_area_estimates(temporal=True,
release_column="Year") for 2-3 non-overlapping releases (Rao-Yu; validated .897-.898; overlapping releases refused).

Round 79: decompose_gap (full profile) splits a PUMS gap between two mutually exclusive groups into explained
(composition) and unexplained parts: Oaxaca-Blinder (model="linear") or Fairlie (model="logit", 0/1 outcome), with
SDR replicate-weight intervals. Validated: Oaxaca-Blinder totals from 300 records in the smaller group; detailed
contributions and all Fairlie quantities from 1,000 (.80-.85 at 300). "Explained" is composition, not a causal effect.

Round 101/103: demography_analysis (full profile; library census.demography) gives abridged life tables from WONDER
age-group exports with Chiang II intervals (kind="life_table", validated), Arriaga decomposition of a life-expectancy
change by age and cause (kind="arriaga", exact; use mutually exclusive causes), age-heaping indices (kind="age_quality":
Whipple, Myers, UN accuracy from counts or PUMS with SDR SEs) and census-survival net migration (kind="survival_migration",
descriptive).
## Regression discontinuity (Round 98; repaired Round 105)

Round 98/105: regression_discontinuity (full profile) estimates a jump at a cutoff with the robust bias-corrected local
quadratic. Validated for discrete running variables (PUMS ages) with weight and replicate_prefix, and for continuous
running variables with automatic CCT CER bandwidth h_ik * n^(-1/20) (Round 105). The density test remains exploratory.
Report covariate jumps and placebo cutoffs; a causal reading requires no other change at the cutoff.

Round 97: spatial_model(kind="cv") reports spatial-block and random cross-validation; random folds are optimistic
for models using neighbours, and block CV is itself a lower bound on new-region error (exploratory).
spatial_model(kind="maup") shows how an area-level slope changes over random zonings (descriptive); report it
when an ecological slope drives a conclusion.

Round 96/104: spatial_model(kind="disease_map", outcome=observed counts, expected=expected counts) gives BYM2 smoothed
relative risks with P(RR > threshold). Exceedance probabilities are calibrated (validated). method="B3" (PC prior +
log-grid Jacobian) is validated for relative-risk intervals when median expected count >= 30 without suppressed counts;
B1/B2 and sparse counts (median E < 30) remain exploratory. Suppressed counts stay missing and are predicted from
neighbours; never output counts 1-9.

Round 95/103: demography_analysis(kind="ypll") (library census.surveillance.ypll_from_wonder) computes YPLL from
WONDER age-group exports (end point 65 or 75 on a band boundary; age-adjusted rate validated). Suppressed cells give
bounds only. joinpoint(aberration="historical_limits" | "ears_c2") flags the latest year (validated on flat series);
a trend inflates false alarms, so read a flag as a prompt to look, after checking the trend.

Round 94: disparity_measures(who_measures=True) gives population attributable risk against the best or declared
group (par, par_pct; validated), the SII (validated) and WHO mean differences (mdm, mdb; exploratory, biased upward
when groups are close). compare_years=[y1, y2] gives changes between non-overlapping releases (validated for par,
sii, weighted mean differences). kind="double_disaggregation" and kind="priority_quadrants" give descriptive WHO
tables with reliability and uncertainty flags. Report absolute and relative measures together with the group rates.

Round 93: spatial_model (full profile) kind="gwr" is exploratory (local intervals .71 when slopes vary; report beside
a global model). kind="classify" (k-means) and "regionalize" (SKATER) are descriptive: fix k in advance, give each
feature an _se or _moe column, and report per-area stability; do not interpret groups of areas with stability
below .8 (misclassified 39-50% in validation). kind="diversity" gives entropy diversity with replicate intervals
(exploratory: .847 at small tract n).

Round 92 context sources: pep (Population Estimates, July 1 county population; vintage 2019 or 2024; no MOE;
never mix vintages; a denominator or covariate, never an outcome), lodes (LEHD jobs by workplace or residence;
noise-infused, no MOE) and acs_flows (ACS county-to-county migration 2010-2020 with <name>_moe; later releases give
state partners only). All are covariates; list them with list_health_sources(kind="context").

Round 102: combine_estimates("pool") reports a validated Q-profile interval for tau^2; its prediction interval is
exploratory. leave_one_out, moderators (meta-regression with permutation p; 10+ estimates) and small_study_test
(Egger; 10+ estimates) are exploratory. Report tau^2 with its interval, not the Q test alone.
## Multiple imputation (Round 100)

Round 100: fit_model(method="replicate", impute=[...], impute_method="pmm" | "norm") imputes any number of
incomplete variables, outcome included, by fully conditional specification (validated); report the fraction of
missing information and, when missingness may depend on the missing values, impute_delta sensitivity rows.
## Matching and triple differences (Round 99)

Round 99: estimate_effect(kind="matching", method="nn" | "cem" | "ps"): bias-corrected nearest-neighbour ATE
(validated), coarsened exact matching ATT among matched (validated; report the share matched), propensity caliper
matching. difference_in_differences(design="triple", group, affected_group) uses a within-unit unaffected group
(validated with 51 units).

Round 91: for annual policy panels with a time-varying confounder that past policy can change (treatment-confounder
feedback), never adjust for it by regression (validation .00-.11 coverage). difference_in_differences(design="msm",
first_treated, time_varying_confounders, product="1-year") fits an IP-weighted marginal structural model (effects of
the 1st-3rd treated year). It is exploratory (.80-.88 with 51 units). Time zero is the first period; units treated
then are refused.

Round 90: estimate_effect(kind="treatment") reports positivity diagnostics. With 5% or more of propensities outside
[.05, .95], plain or stabilized IP weighting under-covered (.807-.863; exploratory): use weights="overlap" (overlap-
population effect, validated .877-.906), weights="truncated" (.864-.905) or method="ra" (g-formula, .881-.907), or
restrict to areas with overlap. A flagged IPW versus g-formula disagreement suggests misspecified models.

Round 89: before a causal claim, state the target trial (causal_question: eligibility, intervention, comparator,
time_zero, outcome, follow_up, contrast, target) and a causal diagram (dag: edges, outcome); estimate_effect and
difference_in_differences take both, manifests take both blocks. Without causal_question results are labelled
associational. Adjustment sets come from the diagram (backdoor criterion), never from the 10% change rule; manifests
refuse formulas adjusting for mediators, treatment descendants, colliders or unmeasured nodes, or leaving a backdoor
path open. Social exposures (poverty, education, race) need named intervention versions.

Round 88: successful results of method tools carry method_sources (role method, guidance, data, software,
validation; each with its citation or audit path). Cite the method papers and guidance texts a reported result rests
on; make_results_bundle writes them to references.md and references.bib. CLI: python -m census cite --tool NAME.
Entries marked [details to verify] were recorded without checking the publication.

<!-- mcp-rules:A -->
Rounds 104-107 validated repairs (previously exploratory):
- combine_estimates (k >= 10): Nagashima-Noma-Furukawa prediction interval, truncated Knapp-Hartung meta-regression, and random-effects Egger / Thompson-Sharp test are validated (Round 104).
- estimate_effect(kind="matching", method="nn_att"): bias-corrected nearest-neighbour ATT with Kish effective-df t interval is validated (Round 104).
- spatial_model(kind="disease_map", method="B3"): BYM2 with PC prior and log-grid Jacobian is validated when median expected count >= 30 (sparse areas stay exploratory; Round 104).
- regression_discontinuity: continuous running variables (CCT CER bandwidth h_ik * n^(-1/20)) are validated alongside discrete PUMS ages (Round 105); the density/manipulation test is validated for continuous running variables with n >= 1,000 (Round 112).
- bias_analysis(kind="misclassification", prior_sd=...): observed-table sampling error propagated through corrected_table is validated (Round 105).
- check_agreement: observed Lin's CCC (delete-one-area Fisher-z jackknife) is validated; error-free CCC stays exploratory (Round 106).
- difference_in_differences(design="msm", method="gformula"): Hernán & Robins ch. 21 parametric g-formula + delete-one-unit cluster jackknife is validated for annual panels with 1+ time-varying confounders (VAR(1) transition); IP-weighted MSM stays exploratory (Rounds 106-108).
- designation_accuracy(ppv_intervals=True): FH parametric bootstrap PPV predictive intervals are validated for rules 'prob80', 'point', and 'lower' (Rounds 107/112; also manifest method 'designation').
- disparity_measures(counts=True): count-scale index measures (idisp, bgv, theil, mld) are validated when every group has >= 100 events (Round 112; rd and log_rr remain validated from >= 20 events).
- stratified_pums(homogeneity_method="hotelling_f"): Korn-Graubard Hotelling F homogeneity test is validated when every stratum has >= 500 records (Round 107).
- diversity_index(method="sdr_bc", sample_sizes=...): exact SDR replicate bias-corrected Shannon entropy is validated for areas with >= 150 respondents (Round 108).
- ecologic_check(...): `ecologic_fuller` (Fuller 1987 alpha=4 reliability-corrected ecologic/between-area slope + jackknife) is validated when areas >= 50 and median_area_n >= 80 (Round 109).
- joinpoint(...): `aapc_bootstrap_t` (parametric residual bootstrap with location re-estimation + t(n-2k-2)) is validated for 15+ annual points, 200+ events/year, and k <= 1 (Round 109).
- Manifest methods (28 total): 'designation', 'agreement' (Round 108), 'rdd', 'disease_map' (Round 109), 'joinpoint', 'demography' (Round 110), 'difference_in_differences', 'interrupted_series', 'combine_estimates', and 'bias_analysis' (Round 114; confirmatory manifests accept only validated configurations).

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

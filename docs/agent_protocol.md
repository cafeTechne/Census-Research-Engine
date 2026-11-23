# Agent Protocol: Extraction, Concordance Review, Derived Statistics, and Validation

This protocol governs how agents (and humans) extract multi-year ACS data, decide whether variables are comparable across releases, and record those decisions. The MCP server returns this document from `get_research_protocol`; its rules are enforced in code, not only described here.

Agents are expected to run every step below, including review. The safeguards come from independence (the drafter never reviews its own decision), evidence the code generates and re-verifies, and primary sources, not from requiring a human.

## 1. Why this exists

ACS variable codes do not have stable meanings across releases. The offline audit (`docs/audits/concordance_audit.md`) found, across 2009–2024:

- lines renumbered under new codes (for example, DP02 "average household size" moved from `DP02_0015` to `DP02_0016` in 2019);
- codes reused for different measures (`DP02_0002` was "family households" in 2018 and "married couple family" in 2019);
- definitions changed under the same code (`B27001_006` went from "6 to 17 years" to "6 to 18 years" in 2017);
- large label restructurings in subject tables (2013, 2017) and data profiles.

A panel keyed by code silently mixes these. The pipeline therefore keys columns by **concept** and refuses to merge anything it cannot verify.

## 2. Standard extraction workflow

1. **Find the table and variables.** `search_tables`, then `list_variables` or `describe_variable(code, year)`. Codes are vintage-specific, so check the label in the years you need.
2. **Name your variables.** Pass `variables=[...]` with the codes your analysis uses. Accepted forms:
   - `CODE` (for example `B19013_001` or `DP02_0016PE`): resolved in the **latest** requested year where the code exists;
   - `YEAR:CODE` (for example `2018:DP02_0002`): the measure that code denoted in that year;
   - a concept ID (`c_…`) from a concordance report.
   Always read the plan's `selection` field to confirm each input resolved to the measure you meant.
3. **Plan.** `plan_extraction(...)` with the same arguments as `batch_download`. It returns API call counts, cached calls, the concordance summary, issues, advisories, and `would_block`. It downloads no data; it makes at most one national-level call per year for the continuity check.
4. **If `would_block` is false,** run `batch_download`.
5. **If `would_block` is true,** read `issues` (blocking ones first) and follow section 3. Do not switch to `concordance_mode="code"` or `"strict"` to get around a block for confirmatory analysis.

Single-year requests never block on concordance, because there is nothing to compare. Collating single-year pulls yourself is allowed, but compare codes and labels across years with `describe_variable` or `check_variable_concordance` before pooling them. That is exactly what the concordance does for you.

## 3. Concordance modes

| Mode | Behavior | Use for |
| :--- | :--- | :--- |
| `fail` (default) | Stops with `CONCORDANCE_REVIEW_REQUIRED` if any blocking issue touches a selected variable | Hypothesis tests, anything published or reused |
| `strict` | Proceeds; unresolved items stay in separate columns; issues are listed in the result | Exploration and whole-table browsing |
| `code` | Keys columns by raw code with no checks; multi-year needs `allow_unverified_concordance=True` | Reproducing legacy outputs only |

`fail` is the default because a silently pooled column changes test results without any visible symptom, while a block only costs a review step.

## 4. Issue kinds

| Kind | Blocking | Meaning | Usual resolution |
| :--- | :--- | :--- | :--- |
| `relabeled` | Yes | Same code, similar but different label across years | Review: `merge` if the wording change is cosmetic, `split` if the measure changed |
| `ambiguous` | Yes | Two codes in one year share a label | Review against the table shell; `split` or `exclude` |
| `universe_changed` | Yes | Table universe text differs across years | Review; usually `split` |
| `continuity_flag` | Yes | National values jump significantly and implausibly between adjacent years | Investigate; `split`, or `merge` with a written `continuity_exception` |
| `continuity_unavailable` | Yes | National data missing, so continuity could not be checked | Retry when the API is reachable |
| `metadata_unavailable` | Yes (multi-year) | A year's variable metadata could not be loaded | Refresh the archive (`scripts/fetch_metadata_archive.py`) |
| `invalid_override` | Yes | A crosswalk row failed validation | Fix or remove the row |
| `redefined` | No | Same code, clearly different measure; already split | None |
| `possible_continuation` | No | One concept ends where a similar one starts; kept separate | Optionally `merge` through review |
| `table_absent` | No | The table is not published in that year | None |

Thresholds for `continuity_flag`: the change is significant at 90% (Z-test with the overlapping-period adjustment), and it exceeds 25% relative change (counts and dollars) or 10 percentage points (percentages).

## 5. Override workflow (draft, then independent review)

Decisions are recorded in `crosswalks/<dataset>/<table>.csv`. Each row maps one (year, code) to a decision.

| Decision | Effect | When |
| :--- | :--- | :--- |
| `merge` | Moves the (year, code) into the target concept, so one continuous column | Same measure, cosmetic relabel or renumbering that automatic matching missed |
| `split` | Confirms the (year, code) is its own concept and resolves the review issue | The measure changed |
| `exclude` | Drops the (year, code) from outputs | The line should not be used at all |
| `rule` | A reviewed regex rewrite of one table's labels at one release boundary; every rewritten line that then matches exactly one later line is merged | Systematic redesigns (for example S1701 in 2017 inserted "population for whom poverty status is determined" into every label). Stored in `crosswalks/<dataset>/<table>_rules.csv`; see section 5a |

**When in doubt, choose `split`.** Keeping two measures apart never corrupts data, while a wrong merge does.

### Step A: Drafter

1. Run `check_variable_concordance(table_code, start_year, end_year, variables=[...])` to get the issues, concept IDs, and evidence.
2. Consult a Census primary source: the release's table and geography changes documentation, table shells, or user notes on `census.gov`.
3. Call `draft_crosswalk_override(...)` with your identity in `drafted_by`. The tool generates the evidence (labels, universes, similarity) from archived metadata, runs the continuity check for merges, saves `crosswalks/evidence/<evidence_id>.json`, and returns draft rows with an empty `reviewed_by`.
4. Hand the draft rows and evidence ID to a different reviewer. Do not review your own draft.

### Step B: Reviewer (agent or human)

1. Use a different identity from the drafter (a different agent session, a different model, or a human).
2. Re-derive the conclusion independently: read the evidence file, open the cited `source_url`, and inspect the labels yourself with `describe_variable`. Do not rely on the drafter's rationale.
3. If you agree, call `record_crosswalk_review(row, reviewed_by=<your identity>)`. If you disagree, do not record the row; draft the opposite decision instead, which then needs its own reviewer.

### Requirements enforced by `validate_crosswalks` and at runtime

All rows:
- `rationale`, `drafted_by`, `reviewed_by`, and `reviewed_on` are present;
- identities look like `human:<name>` or `agent:<model>/<session>`, and `reviewed_by` differs from `drafted_by`;
- the code exists in that year's archived metadata.

`merge` rows additionally:
- `source_url` is on `census.gov`;
- `evidence_id` names a file in `crosswalks/evidence/` whose content hash matches its ID and whose metadata still matches the archive when regenerated, so hand-edited or stale evidence is rejected;
- the evidence's continuity check passed, or `continuity_exception` explains why the discontinuity is real.

Invalid rows are never applied; they surface as `invalid_override` issues.

### Identity convention

- Humans: `human:<name or handle>`
- Agents: `agent:<model-id>/<session-or-run-id>`, for example `agent:claude-opus-5-5/2026-11-01T21-40Z-a7f3`

Use a stable session identifier, so that an audit can confirm the drafter and reviewer were different sessions.

## 5a. Table-scoped rules

`draft_rule_override` / `record_rule_review` (CLI: `draft-rule`, `record-rule`) follow the same two-identity process as single-row overrides. A rule applies `re.sub(pattern, replacement, label)` to the canonical labels of the earlier release of one table, at one adjacent release boundary. Validation rejects a rule that changes any number in a label (age bands and dollar bounds must stay blocked), maps two earlier lines to one later line, creates no new match, overlaps another rule, or cites a source outside `census.gov`. Evidence (every rewrite and match) is generated and re-verified. Merged concepts are still continuity-checked; a rule grants no exemption. Full procedure: `docs/rule_overrides.md`, which `get_research_protocol` also returns.

## 6. Price indexes

Constant-dollar conversion defaults to **R-CPI-U-RS**, the index the Census Bureau uses for all ACS years. `price_index="cpi-u"` is available for comparison and `"c-cpi-u"` (chained CPI) for matching CPS ASEC income reports, which Census has adjusted with C-CPI-U from 2000 onward since 2023. Index data lives in `data/price_indexes/` with source checksums. If a year is missing, the run fails with `PRICE_INDEX_UNAVAILABLE`. Do not supply guessed values through `cpi_table`.

**Integrity guarantee (risk R1, closed in Round 13 by decision D13-4).** The shipped price-index CSVs (`data/price_indexes/{cpi_u,c_cpi_u,r_cpi_u_rs}.csv`) and price-parity CSVs (`data/price_parities/{rpp,pce_price_index}.csv`) are generated by scripts from official sources. When one is loaded from the package's own data directory, its exact bytes are hashed and compared with the `csv_sha256` in its sidecar JSON (`<name>.json`, or `rpp.json` for the parity tables). A mismatch, or a missing checksum, raises `BundledDataIntegrityError` naming the file, the expected and actual SHA-256, and the fix (restore with git checkout or reinstall, or rerun `scripts/update_price_indexes.py` / `scripts/update_price_parities.py`). The check runs once per file per process: the parsed table is cached with the check, and clearing the loader caches (`load_price_index.cache_clear()`, `rpp.clear_cache()`) re-reads and re-checks the file, so a file changed during a session is checked again on its next uncached load. MCP tools and the CLI report a failed check as `error_code` `BUNDLED_DATA_INTEGRITY` with a `next_step`. Scope: the CSVs only; the sidecar JSON (source notes, provisional values) is not hashed. Custom data is the caller's responsibility and is not verified. A `cpi_table` is recorded in extraction metadata as caller-supplied. A table from `CENSUS_PRICE_INDEX_DIR` has its path and SHA-256 recorded under `custom_table` in `price_index_info()`, which flows into the extraction metadata and the `adjust_inflation` tool result. A table from `CENSUS_PRICE_PARITY_DIR` has them recorded under `custom_tables` in `price_parity_info()`, `custom_table` in `place_parity()`, and a `CUSTOM RPP TABLE` note from `describe_place_adjustment()` (and `place_adjust_frame`, whose result also carries `custom_table`). Tests: `tests/test_data_integrity.py`.

Years with an unpublished month (2025: October was never published) are excluded. BLS's incomplete-year figure is used only with `allow_provisional_index=True` (`allow_provisional` in `adjust_inflation`), which adds a `PROVISIONAL INDEX` advisory; say so wherever results are reported.

Home values in releases before 2022 were not on the period end-year dollar basis (ACS user note 2023-07). Plans include an advisory when such tables are deflated.

## 7. Error codes

Branch on `error_code`, not on message text: `INVALID_INPUT`, `INVALID_GEO_LEVEL`, `INVALID_OUTPUT_FORMAT`, `INVALID_DATASET`, `INVALID_VARIABLES`, `VINTAGE_UNAVAILABLE`, `PRICE_INDEX_UNAVAILABLE`, `CONCORDANCE_REVIEW_REQUIRED`, `UNVERIFIED_CONCORDANCE`, `METADATA_UNAVAILABLE`, `API_HTTP_ERROR`, `NO_DATA`, `BUNDLED_DATA_INTEGRITY` (a bundled price table failed its checksum: restore or regenerate it; never substitute values).

## 8. Outputs to cite and keep

Every run writes `<table>_extraction_metadata.json`. It records the package version, git commit, metadata checksum per vintage, the concordance mode, the normalization version, the overrides and rules applied, the price index and its source, any tract harmonization, the advisories, the SHA-256 of every output file, and a `replay_command`. Keep it alongside results. `<table>_concordance.csv` maps every output column back to its code in each year.

**Replay.** `replay_extraction(metadata_path)` (CLI: `replay`) re-runs an extraction into a new folder and compares every file, then every cell. Differences caused by Census revising published data return `success=true, verified=false` with the changed cells; report them, they are not errors. Use `refresh=True` to bypass the query cache.

**Nationwide.** `state_code="all"` covers the 50 states and DC (`include_pr=True` adds Puerto Rico). County and place levels take one request per year; tracts take one per state per year. Failed calls are listed in `failed_calls`; re-running resumes from the query cache.

## 9. Derived statistics

Every derived result carries `estimate`, `moe` (90%), `se`, `cv_percent`, `method`, and `notes`. Report the method.

| Need | Tool | Rule |
| :--- | :--- | :--- |
| Rate where the numerator is a subset of the denominator (poverty rate, share 65+) | `derive_estimate("proportion")` | If the radicand is negative the ratio formula is used and `method` says `proportion_ratio_fallback` |
| Ratio of two non-nested estimates (males per female, renters per owner) | `derive_estimate("ratio")` | Never use `proportion` for non-nested quantities |
| Sum, difference, product, percent change | `derive_estimate(...)` | Sums of zero estimates include every MOE (Handbook 2020, ch. 8) |
| Combine geographies | `aggregate_geographies` | Sum counts first, then `derive`; averaging member rates is wrong. Medians, means, and percentages are refused |
| Median for a custom area | `median_from_distribution` | Sums bracket counts, then linearly interpolates as Census does. Top-coded medians return the bracket bound with `+` and no MOE |
| Many geographies tested at once | `batch_significance` | Default `holm`; `bh` for exploratory screening. Report `significant_adjusted` |

**Approximation versus exact variance.** The formulas above ignore covariance and get worse as more estimates are combined. For any derived estimate that feeds a hypothesis test, call `check_replicate_availability(table, year, geo_level)`. When Census publishes Variance Replicate Estimates (2014 onward, a listed subset of detailed tables, never medians), pass `use_replicates=True` (or `method="replicate"`): the statistic is evaluated on all 80 replicates and Var = 4/80 × Σ(rep − est)². Two cases return special values: estimates built only from controlled cells get MOE 0, and uncontrolled cells with zero replicate variance (Census uses a model-based MOE there) get MOE NaN with a note.

**Median MOEs without replicates.** The default approximation fits the Census 50-percent-proportion variance function to the published bracket MOEs. This is a documented adaptation, not a Census-published formula: it tracks published county MOEs within about 10–20%. The PUMS design-factor method is used only when you pass `design_factor`. Medians rebuilt from B19001 income brackets are usually within 1% of the published B19013 but can differ by more than 2% because Census interpolates a finer internal distribution; gross-rent medians (B25063) reproduce B25064 to the dollar.

**Comparing periods.** Comparisons of overlapping 5-year periods share sample; the z-test applies the overlap factor and notes it. Prefer non-overlapping periods (at least 5 years apart) for confirmatory tests.

## 10. Geography changes

- **Tracts across 2010/2020.** Releases through 2019 use 2010 tracts; 2020 onward use 2020 tracts. `batch_download(..., harmonize_tracts_to=2020)` or `apportion_tracts` apportion the other vintage with the Census tract relationship file (land-area weights by default; NHGIS-style population weights via `weights_file`). MOEs assume independent components and exact weights; say so. Counts only: apportion counts, then re-derive rates and medians.
- **Connecticut** switched from eight counties to nine planning regions in the 2022 release; tract GEOIDs differ between 2020–2021 and 2022+. Harmonization recodes them.

## 11. Validation against Census-published values

`run_validation` (CLI: `validate`; script: `scripts/validate_against_census.py`) recomputes values the Census Bureau publishes independently and compares: pipeline cells against raw API cells, Data Profile percentages from detailed tables, replicate MOEs against published MOEs, medians from distributions, Comparison Profile inflation adjustments and significance flags, county sums against states, and (F11) 2020 Census counts against the Census Bureau's invariants and hierarchy. Offline checks run against frozen fixtures in every test run; CI runs the live battery weekly. If your analysis relies on a calculation path, check that the corresponding validation check passes in `docs/audits/validation_report.md`.

## 12. Inference (models, small areas, correlations, figures)

Validated in `docs/audits/inference_validation.md` by simulation with known truth (coverage of nominal 90% intervals).

| Task | Tool | Rule |
| :--- | :--- | :--- |
| Model-ready data | `build_analysis_frame` | Each variable keeps `_se` and `_cv`; `use_replicates=True` attaches Census replicates |
| Regression | `fit_model(method="replicate")` | Intervals default to `target="population"` (model SE; coverage 0.896). `target="these_areas"` uses replicate SEs for the relationship among these areas in this period (0.895). `"conservative"` adds both and is too wide (0.961) |
| Noisy predictors | `fit_model(method="regression_calibration")` | Corrects attenuation (bias removed, coverage 0.89). Validated for ols, wls, poisson and negbin with bootstrap SEs (Round 46: .869-.918); binomial needs `se_method="jackknife"` (Round 53: .882-.904; bootstrap .851). Spatially correlated counts: `spatial="clusters"` with model poisson/negbin (calibration + IM-8, Round 53: .877-.909). Replicates do not correct attenuation. SIMEX under-covers (0.81) and is not for confirmatory use |
| Noisy small areas | `small_area_estimates` (Fay–Herriot) | Reproduces the published `sae` reference to about six significant figures; EBLUP intervals cover 0.897. Report `gamma` (how far each area moved toward the model) |
| Correlations | `correlation_matrix` | Intervals cover the correlation of the observed estimates (0.895). Sampling error shrinks correlations toward zero; `disattenuate=True` reports a corrected value alongside |
| Trends | `trend_test` | Only non-overlapping releases (at least 5 years apart); overlapping sets are refused |
| Planning | `minimum_detectable_difference`, `reliability_profile` | Check whether the data can detect the effect before designing the analysis |
| Figures and tables | `make_figure`, `make_table`, or `figure_dir=` on model tools | Vector files with values CSV, caption, and provenance |

**Pre-registration.** For confirmatory work, write a manifest (`examples/manifests/`), call `create_manifest` to validate it and get its SHA-256, commit it, then `run_manifest`. Every output carries the hash; anything that could not run is listed under `deviations`, never silently substituted. Analyses outside the manifest are labeled exploratory.

**Local models.** `python mcp_server.py --profile core` exposes 13 tools with short descriptions; every result starts with `summary` and `next_step`. Call `get_recipe` first for multi-step tasks. See `docs/local_models.md`.

## 13. Geography and maps

- **Maps:** `make_map(input_path, column, level, year, se_col=...)`. Pass an SE or MOE column so unreliable areas are hatched. Report the class separability printed in the caption; when it is low, adjacent colors are not statistically distinguishable. Use `kind="significance"` with a `batch_significance` output to map change, never raw differences.
- **Boundaries** are matched to the ACS release automatically (2010-based tracts through the 2019 release, 2020-based from 2020; Connecticut planning regions from 2022).
- **Spatial statistics:** `spatial_autocorrelation` (Moran's I, optional local clusters with correction), `spatial_regression` (lag or error; for the error model pass `correct_outcome_error=true` with `se_col` = the outcome's SE column to correct lambda for sampling error, which assumes independent errors across areas: fine for rates, shares and medians, warned for population/household totals), `spatial_small_area_estimates` (spatial Fay–Herriot). Noisy small-area estimates can create or hide clusters: pass replicates, or rerun on Fay–Herriot estimates as a sensitivity check.
- **Tract harmonization** uses decennial block population or housing-unit weights by default (`weight="auto"`); the first national run downloads about 3,200 county block-count requests, then caches them.
- **Custom areas:** `custom_area_mapping(areas_path, ...)` then `aggregate_geographies`. Partial overlaps are reported with their allocation assumption.
- **Errata:** every extraction plan lists Census errata and user notes for the table and releases; mention them in write-ups.
- **Controlled estimates** (Census MOE code -555555555) now keep MOE 0 with a `<code>_CONTROLLED` flag column.

## 14. Microdata, 1-year estimates, and designs

- **PUMS** (`pums_tabulate`, `pums_regression`): use when no published table crosses the variables you need. Standard errors come from the 80 replicate weights. Cells from fewer than 30 records or with CV above 30% are flagged, not suppressed; report the flag. PUMA is the smallest geography.
  `pums_regression` also fits `model="ordered_logit"`, `"ordered_probit"`, `"mnlogit"`, `"median"` and `"probit"` with the replicate weights (each refitted 80 times; Var = 4/80 sum of squared deviations). All five passed the Round 49 validation (coverage .875–.915); model-based SEs under-cover with unequal weights (.62–.887), so never report them.
- **1-year estimates** (`product="1-year"`): only areas of 65,000+ people; the plan lists requested areas with no 1-year data. There is no standard 2020 1-year release. Never compare a 1-year estimate with a 5-year estimate.
- **Multilevel models and difference-in-differences** (`multilevel_model`, `difference_in_differences`): pass the outcome's SE column so sampling error is included. DiD needs non-overlapping releases and a pre-treatment reference period; with three or more pre-periods, report the parallel-trends test.
- **Cost of living** (`adjust_for_place`): only on request; say in results that regional price parities were applied and that they carry their own error.

## 15. 2020 Decennial Census (P.L. 94-171, DHC)

- **Access:** the same tools as the ACS with `dataset="dec/dhc"` (DHC: `P1` total population, `P12` sex by age, `H1` housing units, `H3` occupancy status) or `dataset="dec/pl"` (P.L. 94-171; its `P1` is race), or `product="decennial"`; `years=[2020]` only. Levels: `us`, `state`, `county`, `tract`, `block group`, `place`, and `block` (P.L. 94-171, or DHC `H1`). Variable codes end in `N` (count). Recipe: `get_recipe(name="decennial_counts")`.
- **Uncertainty:** counts are not sample-based: MOE, SE and CV are undefined, never 0, and no such columns are written. They are not error-free: coverage and processing error, and TopDown differential-privacy noise on everything except state population, block housing units and occupied group-quarters facilities. Read the plan's `uncertainty` record and advisories, aggregate blocks and small areas before computing rates, and say in write-ups that 2020 Census figures carry disclosure-avoidance noise.
- **Tests:** never run a significance test between two census counts (tools refuse `product="decennial"`). Testing an ACS estimate against a census count (`calculate_significance(..., product="5-year", product2="decennial")`) measures ACS sampling error only; report the note it returns. `derive_estimate(..., product="decennial")` gives point estimates only.
- **Do not** splice 2020 Census counts into an ACS series, or treat a DHC table code as the same table in P.L. 94-171.

## 16. External health data (CDC PLACES, USALEEP, County Health Rankings, WONDER)

**The rule (enforced by `create_manifest`).** Determinant studies keep using the ACS's own measure as the outcome (for disability: `B18101`), and use external sources for measures the ACS lacks, such as diabetes. Round 21 showed why: refitting the Round 20 disability determinants with CDC PLACES disability as the outcome inflated the education gradient 1.4× and the poverty gradient 1.7× against the ACS crude adult measure (both are PLACES model inputs) and lost the housing cost-burden association the ACS shows (not an input). Within a county, PLACES varies only with age, sex, race/ethnicity and education composition; it carries no tract-level health information.

| Check | Refused when | What to do |
| :--- | :--- | :--- |
| R1 same construct | The external outcome has an ACS equivalent (PLACES `DISABILITY` and the six disability types, `ACCESS2`, `FOODSTAMP`; CHR `v180`) and the analysis is not a comparison with that ACS measure, or tests another term | Use the ACS table as the outcome |
| R2 model inputs | A tested term is built from the outcome model's inputs (PLACES: B01001/B01002, B02001/B03002 and race-iterated tables, B15002/B15003, B17001/C17002; USALEEP: B19113 and income tables, B03002, B15002/B15003, B01003) | Test a direct outcome, keep the term as a control, or write a `circularity_justification` on the hypothesis |

- **Sources** (`list_health_sources`): PLACES (tract and county, model-based, no key); USALEEP (tract life expectancy 2010-2015 on 2010 tracts, partly model-based, flag-2 tracts dropped by default, `apportion_to: 2020` for 2020 tracts); County Health Rankings 2025 (county; mortality measures are direct NCHS records; its BRFSS measures are PLACES estimates; non-commercial research use); WONDER (user-exported files pinned by SHA-256; suppressed counts censored, never zero).
- **Use:** external variables are outcomes only (`fit_eiv`, `fit_replicate`, `fh_regression`), held fixed in replicate refits; cluster PLACES tract models by county (`"cluster": "GEOID.str[:5]"`, validated in `docs/audits/eiv_cluster_validation.md`).
- **Report:** the source's model and uncertainty (methods.md), join counts (`run.json` `external`), and, for model-based outcomes, that associations with covariates outside the model arise only through their correlation with its inputs. Recipe: `get_recipe(name="external_health_outcome")`.


### Count and proportion outcomes

For CHR 2025 `v037` low birth weight (direct NCHS natality 2017–2023), use
`fit_replicate` with `model: "binomial"`, proportion outcome `<name>`,
`trials: "<name>_denominator"` and `scale: "robust"` (HC3 sandwich SEs).
For counts use `<name>_numerator` as the Poisson outcome and
`exposure: "<name>_denominator"`, `scale: "robust"`. Do not use `scale: "X2"`:
Pearson quasi-likelihood SEs under-cover (0.69–0.79 at nominal 0.90) when areas
differ beyond binomial/Poisson chance, and new manifests with it are refused
(docs/audits/robust_se_validation.md; HC3 covered 0.879–0.897). Robust SEs treat
areas as independent; report residual Moran's I as a limitation. Effective-trials fallback,
external negative-binomial/WLS outcomes and count columns in other formula roles
are refused. Suppressed outcomes stay missing; unreliable small counts are
retained and reported. Replicate SEs describe ACS covariate sampling error,
not a GLM measurement-error correction. Binomial hypothesis tables include odds
ratios and their intervals. `exploratory: true` labels the entire registered run
and its analyses exploratory, preserving any blocking deviations.

Spatial standard errors use Bartlett Conley HAC and great-circle distances between
TIGER representative points. The pre-set Round 22 simulation **failed** its
coverage criterion (`docs/audits/spatial_hac_validation.md`): `spatial_se` is
available only in exploratory manifests, direct fits and `run_variant`, never
confirmatory manifests. `cluster` and `spatial_se` are mutually exclusive.

## Inequality and standardized ratios

Use manifest `inequality` for area-level SII, log RII and concentration. Declare
`outcome`, `rank_by`, positive `weights`, and the boolean
`args.higher_is_more_deprived`; hypotheses name only `sii`, `log_rii` or
`concentration_index` (no term). Ridits run least to most deprived: positive
indices mean higher outcomes among more deprived areas. Concentration therefore
has the reverse sign of the usual income-ranked convention. External outcomes
and their `<outcome>_denominator` weights stay fixed in refits. Default target is
`conservative` (HC3 plus ACS replicate uncertainty); median rank CV <=15% is the
validated range. Above it, warn about attenuation from rank error. Area HC3
assumes independent areas. Circularity R2 tests the ranking variable.

Manifest `smr` requires integer `observed` counts, distinct `population_bands`,
finite positive `reference_rates` in events per person-year, and a non-empty
`reference_source` citation. Rates and source are hashed. Hypotheses use
`log_smr`, with one `geoid` or `"all"` for pooled counts/expected counts. Log
statistics test zero; ratio columns exponentiate estimates and limits. SMR tests
use the combined Poisson/replicate log interval (`target: conservative` only),
while Garwood limits condition on expected counts. Zero observed counts have
only an exact fixed-E interval. Optional positive integer `period_years` (default 1)
scales E for a multi-year count period; optional positive integer `reference_counts`
adds sum_b (E_b/E)^2/D_b to log variance. Both fields are hashed. Reference
person-years are fixed unless they are survey estimates: then args.reference_population_se
(one SE per band; Round 55, validated .892-.908) adds sum_b (E_b/E)^2 (se_b/P_b)^2. Zero
reference deaths are refused, and pooled band
contributions are summed before squaring because rates are shared. An internal
reference makes the independent-count interval conservative (not refused).
Without reference_counts, rates are fixed as before. No band replicates
means zero expected-count uncertainty, explicitly noted. Negative ACS band
replicates are used as published (Round 51: library default
`negative_replicates="accept"`; `"clip"` also passed); every replicate expected count
must be positive. Manifests keep the strict refusal unless `args.negative_replicates`
opts in. See recipe
`health_inequality` and the two fixed simulation audits. Reused MI/NY LBW
associations are exploratory.

## Spatial clusters (Round 26)

An eligible explicit spatial-cluster configuration replaces the ordinary binomial
`scale: robust` requirement; the two cannot be combined.

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
Poisson exposure/expected-death offsets remain fixed.

<!-- mcp-rules:A -->
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

## Group comparisons (Round 31)

<!-- mcp-rules:A -->
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

## PUMS tests (Round 32)

<!-- mcp-rules:A -->
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

## Rank methods and diagnostics (Round 33)

<!-- mcp-rules:A -->
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

## Ranking areas (Round 34)

<!-- mcp-rules:A -->
Round 34 ranking (recipe rank_areas): rank_areas gives Klein-Wright-Wieczorek rank
intervals (individual, or joint for all areas) and each area versus a reference (fixed
value, or a weighted mean of the areas whose errors it shares; Holm or simultaneous).
Validated; conservative. Report rank intervals, not point ranks. Bootstrap percentile
ranks under-covered badly and are not offered. Non-numeric (suppressed) values are
excluded, never ranked. Areas are treated as independent samples.

## Spatial EIV (Round 35)

<!-- mcp-rules:A -->
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

## Composite indices (Round 36)

<!-- mcp-rules:A -->
Round 36 composite indices (full profile tool build_index; recipe composite_index):
first principal component or equal weights; full-sample standardisation and loadings
fixed in every replicate. Validated: per-area score intervals (with replicates) and the
Feldt interval for Cronbach's alpha (independent areas; it under-covers with spatial
dependence; build_index(spatial=True) uses the effective sample size, validated .912-.926 in Round 48). Quintile stability and typologies are descriptive. An outcome cannot be an
indicator of the index used to explain it (circularity).
Round 73 (docs/audits/methods73_validation.md): build_index(method="loadings", loadings={indicator: weight})
applies a paper's published fixed loadings (two or more indicators); its per-area replicate intervals are
validated (mean coverage .897-.899, every area >= .878); standardize=True rescales scores to mean 0, SD 1.

<!-- mcp-rules:A -->
Round 73 three-level models (full profile multilevel_model with groups=[top, middle], e.g.
["state", "county"]): REML random intercepts; fixed-effect intervals use t(G_top - 1) and are
validated (.904-.913 with 30 or 49 top units). Variance shares are reported; their jackknife
intervals are exploratory (screened on 100 draws only); share_intervals=False skips them. The
three-level model takes no sampling_se, replicates or random slopes. Expected counts for indirect
standardization: census.wonder_reference.expected_counts (national WONDER age x sex rates; period_years,
or person_years with the ACS age x sex mix). Round 75 manifests: method "multilevel" (groups "county_fips"
or ["state_fips", "county_fips"]); an "indices" block (ACS indicators; weights fixed in replicates; an
index cannot explain its own indicator); expected_count "person_years" (an external variable).

## Agreement between sources (Round 37)

<!-- mcp-rules:A -->
Round 37 agreement (full profile tool check_agreement; recipe agreement): bias (b - a)
and Cohen's kappa of quintile classes passed validation for independent areas. Bland-Altman
limits of agreement (observed and error-free) use moment-based SEs since Round 48 (validated,
.884-.936). Lin's concordance correlation intervals failed (exploratory).

## Combining evidence (Round 38)

<!-- mcp-rules:A -->
Round 38 combining evidence (full profile tool combine_estimates; recipe
combine_estimates): pooling uses Paule-Mandel + Hartung-Knapp (validated for up to 4
estimates; Round 48: 5-10 with the variance factor truncated at 1, .874-.918); the fixed-effect interval only if homogeneity is declared in advance;
DerSimonian-Laird under-covers with heterogeneity. TOST equivalence (margin set in
advance) and z-test power/minimum detectable effects are validated. Pooling states is a
new analysis, never a reinterpretation of a registered study.

## Multivariate tests and count models (Round 39)

<!-- mcp-rules:A -->
Round 39: compare_groups(outcomes=[...]) adds a joint MANOVA/MANCOVA test (multivariate wild
score bootstrap, one sign per area; validated, size .090-.101; Pillai's trace shown for
comparison). Count slopes: fit_model(model="negbin", exposure=...) uses NB2 with HC3
(validated .885-.901, including overdispersion and excess zeros); Poisson HC3 under-covered
with strong overdispersion (.81-.87) and zero-inflated Poisson failed (exploratory).

## Beta and median regression (Round 40)

<!-- mcp-rules:A -->
Round 40: fit_model(model="beta") (shares in 0-1; logit mean; HC0 sandwich) and
fit_model(model="median") (median regression; kernel SE) passed validation (.885-.917; naive
target; independent areas). Beta model-based SEs failed. Adding replicate variance
over-covered, so it is not added. Survey-weighted PUMS ordinal,
multinomial, median and probit models were added in Round 49 (`pums_regression`); GEE is not available.

## Causal tools (Round 41)

<!-- mcp-rules:A -->
Round 41 causal tools (full profile tool estimate_effect; recipe causal): treatment
effects (AIPW default) validated with precisely measured confounders; 2SLS with an
independent second measurement as instrument removes covariate attenuation (validated;
weak instruments flagged); mediation validated only with an exactly measured mediator
(ACS mediator error drops coverage to .69-.72). State the assumptions; confirmatory causal
claims need a registered design.

Round 47 (docs/audits/causal_robustness_validation.md): estimate_effect(calibrate=True) corrects
noisy confounders (AIPW, regression calibration within treatment groups, bootstrap; .889-.905 where
plain AIPW fell to .77-.87) and a noisy mediator (no controls; .883-.898); both need _se or _moe
columns. Without calibrate, noisy confounders make the result exploratory. iv always reports an
Anderson-Rubin interval (.894-.908 at any instrument strength; can be unbounded); the 2SLS Wald interval
also covered at every F, but its estimate is unstable below F = 10, so report the AR interval there.

## Manifest routing (Round 43)

<!-- mcp-rules:A -->
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

## Count repairs (Round 45)

<!-- mcp-rules:A -->
Round 45 count repairs: interval-censored NB2 (fit_model(model="negbin", exposure=..., censored=
"<true/false column>") since Round 64; census.missing_censored_its.fit_censored_negbin) uses WONDER
counts hidden as 1-9 as interval information, validated (.869-.898), and never outputs a hidden value; fit_model(model="negbin", spatial="clusters") gives IM-8 count slopes (validated on
the MI/NY geometry; outside it the result carries a note); NB2 with noisy ACS exposures held fixed
covered (.888-.891). within_states=True assigns the eight clusters within each state.

## Missing data, censored counts, time series (Round 42)

<!-- mcp-rules:A -->
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

## Disparities between population groups (Round 76)

<!-- mcp-rules:A -->
Round 76: disparities between population groups within an area (race/ethnicity, sex): the disparity_measures
tool (full profile) or manifest method "disparity" (groups = one rate per mutually exclusive group, populations,
reference declared in advance; list left-out groups in omitted_groups). Report absolute (rd, bgv) and relative
(log_rr, idisp, theil, mld) measures together. Validated: ACS rd and idisp up to a largest group-rate CV of .50,
log_rr/bgv/theil/mld up to .30; counts (Poisson, known populations) rd and log_rr with 20+ events per group (count
idisp/bgv/theil/mld failed, .07-.84: exploratory); 2-6 groups. Kitagawa rate/composition decomposition (manifest
"kitagawa", or disparity_measures(decompose_areas=[a, b])) validated to stratum CV .50 and 20+ events per stratum.

## Area versus individual associations (Round 87)

<!-- mcp-rules:A -->
Round 87: never apply an area-level result to individuals (ecologic fallacy). When a question is about people, run
pums_regression(..., ecologic_check="<exposure>") to compare the within-PUMA (individual) association with the
between-PUMA and area-level (ecologic) ones. The logit decomposition is validated from 5,000 records; the
risk-difference decomposition and the ecologic gap are exploratory. A contextual effect is not proof of an area cause.

## Bias analysis (Round 86)

<!-- mcp-rules:A -->
Round 86: report an E-value with ratio estimates (bias_analysis kind="e_value"; also in stratified_analysis and the
marginal measures): the minimum unmeasured-confounder strength that would explain the estimate away. A 2 x 2 table
can be corrected for misclassification (kind="misclassification"); its probabilistic interval failed validation
(exploratory). For a covariable of uncertain causal direction, report results with and without it.

## Designating areas by a threshold (Round 85)

<!-- mcp-rules:A -->
Round 85: a threshold designation on noisy ACS rates is a screening test. designation_accuracy (full profile) gives
each area's probability of truly exceeding the threshold (Fay-Herriot posterior; validated) and the expected
sensitivity, specificity, PPV and NPV of the point, lower-bound, probability-.5 and probability-.8 rules
(exploratory). Report any designated list with its rule's expected PPV and sensitivity.

## Risk ratios instead of odds ratios (Round 84)

<!-- mcp-rules:A -->
Round 84: for common binary outcomes (above about 10%) odds ratios overstate risk ratios. Area binomial models:
fit_model(model="binomial", trials=..., marginal="<exposure>") adds the standardized risk ratio, risk difference and
attributable fraction (and dose_levels=5 a dose-response test). PUMS: pums_regression(model="logit",
marginal="<0/1 exposure>") adds the same plus the modified-Poisson prevalence ratio. All validated (.862-.898).

## Confounding and effect modification (Round 83)

<!-- mcp-rules:A -->
Round 83: stratified_analysis (full profile) gives crude, stratum-specific and Mantel-Haenszel pooled RR/OR/RD
(validated for counts from 5 expected cases per stratum-arm and for PUMS with replicate weights from 300 records per
stratum), the Breslow-Day OR homogeneity test (validated; the RR and PUMS homogeneity tests are exploratory), RERI
for additive interaction (validated) and a descriptive confounder/effect_modifier label (10% rule). Declare
covariable roles before analysis (manifest "covariables"): never adjust for a mediator; report effect modifiers by
stratum. get_recipe("confounding").

## Epidemiologic reporting conventions (Round 82)

<!-- mcp-rules:A -->
Round 82 (Foundations of Epidemiology): area analyses are ECOLOGIC (they describe areas, not individuals) and
CROSS-SECTIONAL (no temporal order): write "is associated with" / "times as high in ... compared with ...", never
"causes", "leads to" or "effect of" (except estimate_effect and DiD, which state their assumptions). Say whether
an outcome is a prevalence (ACS, PLACES) or an incidence rate (WONDER per person-year), with units and period.
An interval that includes the null means "no evidence of a difference", not "no difference". Report allocation
(imputation) shares above 5% (reliability_profile allocation_tables) and give a Table 1 (make_table kind="table1").

## Spatial scan (Round 81)

<!-- mcp-rules:A -->
Round 81: spatial_scan (full profile) finds clusters of counties with high event counts (Kulldorff Poisson scan).
The primary-cluster p-value is validated with windows up to 50% of the expected total and 999 replicates (size
.099-.116 at .10). Denominators must be exact: ACS-estimated denominators inflate false clusters (.15-.53), and a
denominator _se column (median CV > .01) makes it exploratory. Descriptive unless prespecified=True. Suppressed
WONDER counties must be excluded with a stated rule; counts are never imputed.

## Small-area proportions and several releases (Round 80)

<!-- mcp-rules:A -->
Round 80: small_area_estimates(transform="arcsine") for proportions near 0 or 1 (bias-corrected back-transform,
bootstrap MSE; validated .898-.904 per area on MI/NY counties and tracts) and small_area_estimates(temporal=True,
release_column="Year") for 2-3 non-overlapping releases (Rao-Yu; validated .897-.898; overlapping releases refused).

## Decomposing a PUMS gap (Round 79)

<!-- mcp-rules:A -->
Round 79: decompose_gap (full profile) splits a PUMS gap between two mutually exclusive groups into explained
(composition) and unexplained parts: Oaxaca-Blinder (model="linear") or Fairlie (model="logit", 0/1 outcome), with
SDR replicate-weight intervals. Validated: Oaxaca-Blinder totals from 300 records in the smaller group; detailed
contributions and all Fairlie quantities from 1,000 (.80-.85 at 300). "Explained" is composition, not a causal effect.

## Spatial cross-validation and MAUP (Round 97)

<!-- mcp-rules:A -->
Round 97: spatial_model(kind="cv") reports spatial-block and random cross-validation; random folds are optimistic
for models using neighbours, and block CV is itself a lower bound on new-region error (exploratory).
spatial_model(kind="maup") shows how an area-level slope changes over random zonings (descriptive); report it
when an ecological slope drives a conclusion.

## Spatial disease mapping (Round 96)

<!-- mcp-rules:A -->
Round 96: spatial_model(kind="disease_map", outcome=observed counts, expected=expected counts) gives BYM2 smoothed
relative risks with P(RR > threshold). Exceedance probabilities are calibrated (validated); relative-risk intervals
are exploratory (under-cover with median expected counts near 5 over few areas). Suppressed counts stay missing and
are predicted from neighbours; never output counts 1-9.

## YPLL and aberration detection (Round 95)

<!-- mcp-rules:A -->
Round 95: YPLL comes from WONDER age-group exports (census.surveillance.ypll_from_wonder; end point 65 or 75 on a
band boundary; age-adjusted rate validated). Suppressed cells give bounds only. joinpoint(aberration=
"historical_limits" | "ears_c2") flags the latest year (validated on flat series); a trend inflates false alarms,
so read a flag as a prompt to look, after checking the trend.

## WHO inequality monitoring (Round 94)

<!-- mcp-rules:A -->
Round 94: disparity_measures(who_measures=True) gives population attributable risk against the best or declared
group (par, par_pct; validated), the SII (validated) and WHO mean differences (mdm, mdb; exploratory, biased upward
when groups are close). compare_years=[y1, y2] gives changes between non-overlapping releases (validated for par,
sii, weighted mean differences). Report absolute and relative measures together with the group rates.

## Spatial models (Round 93)

<!-- mcp-rules:A -->
Round 93: spatial_model (full profile) kind="gwr" is exploratory (local intervals .71 when slopes vary; report beside
a global model). kind="classify" (k-means) and "regionalize" (SKATER) are descriptive: fix k in advance, give each
feature an _se or _moe column, and report per-area stability; do not interpret groups of areas with stability
below .8 (misclassified 39-50% in validation).

## Population Estimates, LODES and migration flows (Round 92)

<!-- mcp-rules:A -->
Round 92 context sources: pep (Population Estimates, July 1 county population; vintage 2019 or 2024; no MOE;
never mix vintages; a denominator or covariate, never an outcome), lodes (LEHD jobs by workplace or residence;
noise-infused, no MOE) and acs_flows (ACS county-to-county migration 2010-2020 with <name>_moe; later releases give
state partners only). All are covariates; list them with list_health_sources(kind="context").

## Marginal structural models (Round 91)

<!-- mcp-rules:A -->
Round 91: for annual policy panels with a time-varying confounder that past policy can change (treatment-confounder
feedback), never adjust for it by regression (validation .00-.11 coverage). difference_in_differences(design="msm",
first_treated, time_varying_confounders, product="1-year") fits an IP-weighted marginal structural model (effects of
the 1st-3rd treated year). It is exploratory (.80-.88 with 51 units). Time zero is the first period; units treated
then are refused.

## Positivity and weighting (Round 90)

<!-- mcp-rules:A -->
Round 90: estimate_effect(kind="treatment") reports positivity diagnostics. With 5% or more of propensities outside
[.05, .95], plain or stabilized IP weighting under-covered (.807-.863; exploratory): use weights="overlap" (overlap-
population effect, validated .877-.906), weights="truncated" (.864-.905) or method="ra" (g-formula, .881-.907), or
restrict to areas with overlap. A flagged IPW versus g-formula disagreement suggests misspecified models.

## Causal question specification (Round 89)

<!-- mcp-rules:A -->
Round 89: before a causal claim, state the target trial (causal_question: eligibility, intervention, comparator,
time_zero, outcome, follow_up, contrast, target) and a causal diagram (dag: edges, outcome); estimate_effect and
difference_in_differences take both, manifests take both blocks. Without causal_question results are labelled
associational. Adjustment sets come from the diagram (backdoor criterion), never from the 10% change rule; manifests
refuse formulas adjusting for mediators, treatment descendants, colliders or unmeasured nodes, or leaving a backdoor
path open. Social exposures (poverty, education, race) need named intervention versions.

## Method attribution (Round 88)

<!-- mcp-rules:A -->
Round 88: successful results of method tools carry method_sources (role method, guidance, data, software,
validation; each with its citation or audit path). Cite the method papers and guidance texts a reported result rests
on; make_results_bundle writes them to references.md and references.bib. CLI: python -m census cite --tool NAME.
Entries marked [details to verify] were recorded without checking the publication.

## Staggered adoption and synthetic control (Round 78)

<!-- mcp-rules:A -->
Round 78: policies adopted in different years (staggered adoption) in an ANNUAL panel (ACS 1-year with
product="1-year", 2020 refused, or another annual source): difference_in_differences(design="staggered",
first_treated="<column>"). Sun-Abraham (default) is validated (.881-.899, 51 units); method="callaway_santanna" is
validated only with the se column (ACS variance added, .882-.906; without it .848-.868, exploratory). Uniform bands
are descriptive. Synthetic control for one treated unit failed (placebo size .12-.19 at .10): library only,
exploratory. Five-year releases are refused for staggered designs.

## Joinpoint and age-adjusted rate ratios (Round 77)

<!-- mcp-rules:A -->
Round 77: the joinpoint tool (full profile) describes where an ANNUAL rate series changed trend without a pre-set
date (for a known policy date use interrupted_series). The number of joinpoints is validated (Kim et al. permutation
tests, false-joinpoint rate .012-.023); APC and AAPC intervals failed (.51-.91, joinpoint locations are estimated):
report them as exploratory. Complete years only; overlapping ACS five-year releases refused. joinpoint(rate_ratio=...)
gives the ratio of two directly age-adjusted rates with the Tiwari interval (validated .900-.921).

## Event-count smoothing and nonlinear exploratory models (Round 27)

For ACS direct estimates with known sampling variance, use Fay–Herriot. For event
counts with fixed expected counts, the Python library exports
`eb_poisson_gamma`; follow `get_recipe("small_area")`. This is descriptive only,
without a manifest smoothing method or a new MCP tool. WONDER exports are manual;
suppressed counts remain missing with [1,9] bounds and contribute interval
probabilities, never zero/midpoint imputations. Equal bounds on published counts
are exact observations. E is expected events, not population; compute it from
exposure times a cited rate in matching time/population units. Optional
`reference_rate` produces rates in the supplied units. Beta is a Gamma rate.
Posterior 90% intervals and Laird–Louis with 200 refits passed the fixed Round 27
criterion; posterior is the default. Preserve DataFrame.attrs with exports and
report the validation note. Reference-rate/expected-count uncertainty and spatial
dependence are excluded. EB intervals are not ACS MOEs, and smoothed rates are
not confirmatory outcomes or evidence of recovered suppressed counts. Existing
maps accept `eb_ratio`; label maps descriptive EB and do not fabricate SEs.

Natural cubic splines `cr(x, df=3|4|5)` and `joint_wald` **failed** the fixed Round
27 false-positive criterion and are exploratory only. Confirmatory manifests
refuse either feature. They are restricted to non-spatial `fit_replicate`
OLS/WLS/binomial/Poisson; no EIV, Fay–Herriot, SIMEX/calibration or spatial fits.
`cr` uses centered constraints and default full-sample quantile knots, frozen in
every replicate. df is required; custom knots and nested spline expressions are
unsupported. The same state is retained when assessing high-CV influence.

Round 31 update: binomial and Poisson `cr` splines are confirmatory-eligible when every
hypothesis on that analysis is a `joint_test` of the spline variable (wild score
bootstrap, validated). OLS splines, individual spline coefficients and `joint_wald` stay
exploratory.

A joint hypothesis uses `statistic: "joint_wald", variable: "x"`, without `term`,
and `direction: "two_sided"` (existing `"two-sided"` is accepted). It jointly tests
standalone design columns involving x, including `C(x)`, excluding interactions.
Circularity R1/R2 applies to the variable. W=b'V^-1 b is referred to chi-squared(q),
where q is recorded in `df`. Model covariance is explicitly HC3; sampling
covariance is 4/80 times uncentered replicate-deviation outer products; conservative
uses their sum. Matrices and term labels are in diagnostics. Existing non-spline
coefficient SE conventions are retained; spline coefficient model SEs are HC3.
A singular covariance/design is not tested and produces a deviation. W has no
coefficient CI or odds ratio. WLS, Poisson, df=4 and categorical terms have
computational checks but were not separately simulation-validated. Do not use
the exploratory results for confirmatory claims.


## Residential segregation (Round 28)

Start with `get_recipe("segregation")`; use existing manifest tools. Method
`segregation` requires tract-level `groups` (mutually exclusive count variables)
and `within: "county"`. Declared groups' sum is tract population. D and isolation
require two groups; isolation refers to group one. H supports multiple groups;
three-group bias-corrected H passed Round 50, four or more groups are exploratory.
No CBSA/metro pooling or pre-aggregation. Tract GEOIDs are eleven-digit strings;
county hypotheses use five digits, preserving leading zeros.

Every group/tract needs all 80 replicates, labelled by Year for multiple releases.
Negative replicate group counts are set to zero before the refits (Round 51; library
default `negative_replicates="clip"`, manifests opt in with `args.negative_replicates:
"clip"`, else strict refusal). No other clipping, missing-row fixing or failed-refit deletion. Zero-total
tracts are excluded in each index refit, recomputing totals. An absent county
group makes the index undefined, noted, and its hypothesis is not tested.
SE=sqrt(4/80 sum(Ir-I)^2). Fixed correction I-4(mean(Ir)-I) uses the same SE.
Round 50 (realistic ACS error) made every default bias-corrected: naive D failed it.
An explicit bias_correction override that failed validation is exploratory only;
confirmatory hypotheses refuse it. Normal intervals/adjusted points are not
clipped to [0,1]. Report selected versions and each row's validation notes.

Hypotheses name statistic, geoid and an explicit null_value for one-area tests.
County contrasts add compare_geoid, default null zero, first minus comparison,
and compute per-replicate differences before variance. Multiple-release tests
require release; compare_release selects the other release (same county if
compare_geoid omitted). Independent non-overlapping five-year releases add
variances, not matched replicate deviations. Overlaps/self-comparisons are refused.
One-sided tests use estimate-null. These are finite-area ACS sampling intervals,
not causal or superpopulation inference. Validation gate (Rounds 50 and 52, real
tract MOEs, non-negative counts, correlated groups; poverty, income and race/ethnicity
groups, MI/NY and OH/PA): a row is validated, with at least five populated tracts, when
the county's noise level (`noise_level`: the largest, over groups, of the median tract
CV) is in [.15, .75) for bias-corrected D (Round 66: .75-1 failed on Texas counties), finite for bias-corrected isolation, below
1.0 for two-group and .50 for three-group bias-corrected H, and finite for four- to
six-group bias-corrected H (six groups: Round 57); or when every tract group-count CV is <= .15 (Round 28,
`max_count_cv`; the only range for naive D). Naive isolation/H failed race groups
(Round 52) and are exploratory. An infinite noise level is never validated. Otherwise
rows are exploratory and confirmatory hypotheses are refused at run time. Counties with
clipped negative replicates are validated for bias-corrected versions only: D below .50,
isolation below .75, two-group H below 1.0, four- to six-group H at any finite level
(Rounds 51 and 57; `clipped_replicates`). Cross-release contrasts need both rows validated,
two groups and a larger noise level below .50 (Round 52); same-release county contrasts
the same, except corrected D (failed, Round 57). Group-quarters tracts (prisons,
dormitories) can be left out with args.group_quarters {gq, total, max_share} or
`exclude_tracts`: a definitional choice to report. No new dependencies or MCP tools.


<!-- mcp-rules:B -->
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

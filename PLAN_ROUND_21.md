# Round 21: External health outcomes (Step 2): CDC PLACES connector and a validation study

**Date:** 2026-11-14
**Status:** Part 1 implemented, study run and reviewed (section 9). Part 2 (sections 10-17, the section 8 work plus the circularity rule, at the owner's request of 2026-11-15) in progress
**Baseline:** v0.19.0 (Round 20, DOI 10.5281/zenodo.24238647)
**Roadmap:** Step 2 of PLAN_ROUND_20 section 0. Step 3 (count outcomes, PLAN_ROUND_20 section 8) stays next.

## 0. Why this round

Round 20 showed the engine can run a public-health study from ACS alone. Most health outcomes, though, are not in the ACS: diabetes, depression and life expectancy come from other systems. Step 2 lets a manifest bring in an external health measure with its provenance, uncertainty and caveats, starting with CDC PLACES, the most used tract-level source.

Round 20's lesson comes first. Tract residuals were spatially autocorrelated and the independence sandwich understated SEs by 2–3× (friction F6). A clustered sandwich was added but not validated. PLACES estimates also share county random effects, so every PLACES model needs clustered SEs. Validating them is a precondition for the study.

## 1. What PLACES is, and what that means for analysis (verified 2026-11-14)

- **Datasets.** Socrata on data.cdc.gov, public domain:
  - 2025 release, tract `cwsq-ngmh` (long format: one row per tract and measure);
  - county `swc5-untb`;
  - GIS-friendly tract `yjkw-uj5s`.
- **Model.** Measures are adult (18+) crude prevalences from BRFSS 2023 (2022 for five measures). They come from multilevel regression and post-stratification:
  - individual age, sex, race/ethnicity and education;
  - the county-level share of adults below 150% of the poverty line (ACS 5-year);
  - state and county random effects;
  - applied to 2020 decennial block population counts and aggregated to tracts.
  - Source: CDC PLACES methodology page.
- **Uncertainty.** 95% intervals are the 2.5th and 97.5th percentiles of 1,000 Monte Carlo draws. They are model-based, not sampling replicates.
- **Tract vintage.** 2020 tracts. Michigan has 2,904 tracts with PLACES rows, which matches the 2020 count of populated tracts, not the 2,813 tracts of 2010; the run checks this against the ACS frame.

**Consequence: the circularity problem.** Within a county, a tract's PLACES value varies only through its age, sex, race/ethnicity and education composition. The model contains no tract-level information about health. So:
- Regressing a PLACES outcome on ACS composition measures (age, race, education, and through the county term, poverty) partly recovers CDC's model, not the world.
- A PLACES association with a determinant the model does not contain (vehicle access, housing cost) can arise only through that determinant's correlation with composition.

The engine must say this wherever PLACES is used.

## 2. Engine work

**B1. Validate the clustered sandwich of `fit_eiv` (F6).**
- **Simulation** (`scripts/eiv_cluster_validation.py`, 500 replications per cell):
  - G clusters of m tracts (G = 30, 60 and 150; n ≈ 3,000);
  - a cluster-shared component in the true covariate and in the model error (within-cluster correlation 0, 0.2 and 0.5);
  - heteroscedastic ACS-type covariate error with synthetic replicates (as in Round 20);
  - the outcome either ACS-type, with correlated error and replicates, or external-type, with independent error and no replicates (B3).
- **Acceptance:**
  - clustered 90% coverage of 0.87–0.93 for G ≥ 60, reported for G = 30;
  - bias removed as in Round 20;
  - the independence sandwich's under-coverage under clustering is shown for comparison.
- Result: `docs/audits/eiv_cluster_validation.md`.
- **Manifest:** `args.cluster` takes a frame column or `GEOID.str[:N]`, for example `GEOID.str[:5]` for county, and validation checks the form.

**B2. `census.health_sources`: external data registry and PLACES connector.**
- **Registry.** `SOURCES["places"]` records:
  - the dataset ids per release and level;
  - licence and attribution;
  - measure ids, units and value type (crude prevalence at tract level);
  - geography vintage;
  - the source model's covariates, as text and as ACS table families (age-sex B01001, race/ethnicity B02001/B03002, education B15002/B15003, poverty B17001/C17002/B17024, used through the county term);
  - the uncertainty type (`model_based`, Monte Carlo 95% interval).
- **Download:**
  - Socrata CSV export over plain HTTPS: no key and no app token.
  - Filtered to the manifest's states and measures, paged, and sent with the engine's generic User-Agent through `census.http.polite_get`.
  - Each page is cached under `.cache/health/places/<release>/<level>/` with a sidecar recording the URL, SHA-256, size and retrieval time.
  - The dataset's `rowsUpdatedAt` is recorded, because Socrata datasets can be revised in place.
  - Offline mode (`CENSUS_HEALTH_OFFLINE`) refuses to download.
- **Parser:**
  - output is a wide frame with `GEOID`, `<name>`, `<name>_se`, `<name>_ci_lower` and `<name>_ci_upper`;
  - SE = (upper − lower) / (2 × 1.96), recorded as an approximation, since Monte Carlo percentile intervals need not be symmetric;
  - malformed rows (wrong GEOID length, non-numeric values, duplicates) raise.
- Offline tests use an injected fetcher.

**B3. Manifest `external` variables.**

  ```json
  "external": [{"name": "places_dis", "source": "places", "release": 2025, "measure": "DISABILITY"}]
  ```

- **Validation:**
  - the source, release and measure are in the registry;
  - the geography level has a dataset for that release;
  - `states` are given;
  - names are unique across variables and derivations;
  - every ACS release uses the source's tract vintage (2020 tracts: ACS 2020 and later), or `harmonize_tracts_to` equals it;
  - `aggregation` is refused;
  - derivations may not reference external variables.
- **Use limits.** External variables may appear **only as the outcome** of `fit_eiv`, `fit_replicate` or `fh_regression`. As a covariate, their non-sampling model error would go uncorrected.
- **Run:**
  - external data are fetched after the ACS analysis frame and joined on GEOID;
  - the run records each file's URL and SHA-256, `rowsUpdatedAt`, matched units, frame units without a value, and source units outside the frame;
  - a fetch failure is a blocking `external_unavailable` deviation;
  - more than 5% of frame units with complete ACS data lacking an external value is a blocking `external_join_failed` deviation, which signals a vintage mismatch.
- **Fixed in replicate refits.** `fit_eiv` and `fit_replicate` hold external variables fixed (new `fixed_variables` for `fit_eiv`). Their error is independent of the ACS sampling error, so the cross term s_i is zero and their variance enters the residual, which the sandwich captures. Run records and methods state this.
- **Circularity guard.** For an analysis with an external outcome whose formula uses a variable from the source model's covariate tables, `create_manifest` returns a note naming the overlap. `methods.md` always carries the source's model description and the within-county caveat. The citation and data-source statement name the external source.

**B4. Housekeeping from the Round 20 friction log.** F10: the analysis frame builds its columns in one concat, which removes the pandas fragmentation warnings. F7 (empty age bands) and F8/F9 stay in the backlog.

## 3. The study: does CDC PLACES see tract disability?

**Question.** Across Michigan and New York tracts, how far do PLACES model-based disability prevalences agree with the ACS direct survey estimates? And does that agreement survive within counties, and beyond age structure, where only demographic composition drives PLACES?

This validates the measurement system. It is the PLAN_ROUND_20 section 7.3 pilot, and it tests the connector, the vintage join and the uncertainty treatment on a question where the answer is checkable.

| Item | Choice | Why |
| :--- | :--- | :--- |
| Units | All MI (26) and NY (36) tracts, 2020 vintage | Test states. PLACES 2025 is on 2020 tracts |
| ACS | 5-year 2024 (2020–2024), `B18101` adult bands (18–34, 35–64, 65–74, 75+, both sexes), Census VRE replicates | Exact replicate SEs; overlaps BRFSS 2023 in time |
| Outcome | `places_dis`: PLACES 2025 `DISABILITY`, crude % of adults with any of six disability types (BRFSS 2023) | The external measure under test |
| Covariate | `acs_dis`: % of civilian noninstitutionalized adults 18+ with any disability (ACS six questions) | Same construct, independent system; crude, as PLACES tract values are crude |
| Composition | `pct65`: share of those adults aged 65+ (same table) | Age is the strongest driver of both measures |
| Estimator | `fit_eiv` (ACS error corrected; the PLACES outcome is external and held fixed), SEs **clustered by county** (`GEOID.str[:5]`, 145 clusters) | B1. PLACES errors share county random effects |
| Reliability | CV screen on `acs_dis` at 30%, flag only | As before |
| Correction | Holm across three hypotheses, 90% intervals | |

**Hypotheses** (`examples/manifests/r21_mi_ny_places_disability_validation.json`):
- **H1** (m1: `places_dis ~ acs_dis + C(state)`): PLACES disability is higher where ACS disability is higher. `acs_dis`, one-sided `greater`.
- **H2** (m2: `places_dis ~ acs_dis + C(county)`): the association holds **within counties**. `acs_dis`, `greater`.
- **H3** (m3: `places_dis ~ acs_dis + pct65 + C(county)`): it holds within counties **beyond adult age structure**. `acs_dis`, `greater`.

**Expectations, stated before the data:**
- H1 is close to certain: both measures rise with age.
- H2 is likely, because tract age composition varies within counties.
- H3 is open. Within counties, after age, PLACES varies only with sex, race/ethnicity and education composition, so H3 asks whether those carry ACS-measured disability.
- The two surveys differ in level: BRFSS adult disability is around 28% nationally, against roughly 15% for ACS adults. So the slope is not expected to be 1, and no hypothesis tests a level.

**Seen before registration:**
- tract `B18101` estimates (Round 20 analysed them, including crude prevalence in E3);
- the PLACES measure list and per-state row counts for the 2025 release.

No PLACES estimate values have been downloaded or viewed. The cache is checked and recorded.

## 4. Protocol

1. B1–B4 with offline tests. B1's simulation passes. Fast gate green.
2. `/code-review high`; fix findings.
3. Write the manifest, run `create_manifest` (records the circularity note), **commit it alone** and push.
4. `run_manifest` live into `studies_output/r21/confirmatory`.
5. Pre-specified **exploratory** analyses (labelled, with the manifest hash), in `scripts/r21_exploratory.py`:
   - **E1:** the independence sandwich versus county-clustered, and naive versus corrected slopes.
   - **E2:** Round 20's determinant models (m1, m2) refitted with `places_dis` as outcome, on the Round 20 analysed frame. Does PLACES reproduce the ACS determinant pattern, or only the composition-driven part? This is the circularity check in practice.
   - **E3:** PLACES `LACKTRPT` (lack of reliable transportation, a health-related social need) against ACS `no_vehicle`.
   - **E4:** H1–H3 without New York City, and per state.
   - **E5:** maps of `places_dis`, `acs_dis` and their standardized gap.
   - **E6:** Moran's I of m3 residuals.
6. Report `docs/studies/r21_mi_ny_places_disability_validation.md`, with the same structure as Round 20, the friction log and the review section (an author self-review, as the owner delegates).

## 5. Acceptance

- The manifest is committed before the first PLACES value download.
- The run is `confirmatory`, or `confirmatory_incomplete` with its deviations reported.
- Every reported number traces to the bundle or a hashed exploratory output.
- B1–B4 have offline tests, and B1 meets its criteria.
- The full suite passes on Python 3.14 and 3.10, except the known 3.10 spatial λ test.

## 6. Out of scope

Other Step 2 connectors (USALEEP, County Health Rankings, SVI, Food Atlas, HRSA, EPA), which reuse the registry next. Also out of scope: external covariates with model error; vintage apportionment of rates (USALEEP and Food Atlas are on 2010 tracts); and Step 3 count outcomes.

## 7. Release

v0.20.0 with a Zenodo DOI, after the review, its fixes, both suites and the report's review section. Study outputs are attached as an archive.

## 8. Next (Round 22 sketch)

- **Step 2, continued.** USALEEP life expectancy, on 2010 tracts, needs rate apportionment through the Round 19 crosswalk with population weights. That is a new, documented approximation, validated on tract splits where both vintages exist. County Health Rankings bring a county-level connector.
- **Step 3.** Ingest WONDER exports (PLAN_ROUND_20 section 8): county premature mortality against the Round 20 determinants.

---

## 9. Implementation status

| Item | Result |
| :--- | :--- |
| B1 | Clustered sandwich validated (`docs/audits/eiv_cluster_validation.md`, 500 per cell): G >= 60 coverage 0.870-0.914, passed; the independence sandwich fell to 0.46-0.88 under clustering. `args.cluster` takes `GEOID.str[:N]` |
| B2 | `census.health_sources` with the CDC PLACES connector (crude-only, deterministic paging, SHA-256 sidecars, revision stamp tied to the download, offline mode) |
| B3 | Manifest `external` variables (outcome-only, single release, vintage check, blocking deviations, circularity notes, methods text); `fit_eiv(fixed_variables=...)` |
| B4 | `analysis_frame` without fragmentation (F10) |
| Review | `/code-review high` before registration: 10 findings fixed (vintage check under `harmonize_tracts_to`, multi-release externals, duplicate measures, paging, revision stamp, cache helper reuse, methods wording) |
| Preregistration | Manifest `11294774...1f76`, committed alone at `2af16e0` (04:34:25Z); first PLACES download 04:34:46Z |
| Results | H1-H3 supported (corrected slopes 0.82, 0.77, 0.82; county-clustered). PLACES levels about 13 points above ACS. E2: PLACES reproduces model inputs (education doubled) but not cost burden, the circularity problem in data |
| Report | `docs/studies/r21_mi_ny_places_disability_validation.md`; friction F1-F7 |

---

# Part 2 (owner request, 2026-11-15): enforce the circularity lesson, then do section 8

The owner asked that the MCP state, and the engine enforce, the lesson of the Part 1 study: **determinant studies keep using the ACS's own measure (for disability: B18101), and use PLACES for measures the ACS lacks, such as diabetes**. Then implement the rest of the plan (section 8, and the Part 1 backlog that blocks it) on this branch before merging.

## 10. What the sources are (verified 2026-11-15)

- **USALEEP** (NCHS, NAPHSIS, RWJF): tract life expectancy at birth e(0) and its SE for 2010-2015 deaths, on **2010 tracts** (Census 2010 codes). Files per state: `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/{ST}_A.CSV` (columns `Tract ID, STATE2KX, CNTY2KX, TRACT2KX, e(0), se(e(0)), Abridged life table flag`). 65,662 tracts (88.8%); Maine and Wisconsin are missing; tracts under 5,000 people over the period are excluded.
  - **It is partly model-based.** Age groups with missing deaths take **predicted** death rates from a zero-truncated Poisson or negative-binomial model. Its covariates are tract quartiles of median family income, population density, % non-Hispanic Black, % Hispanic and % bachelor's or higher (ACS 2011-2015 and the 2010 census), plus a reservation-area indicator (PRCSDA) and region.
  - Abridged life table flag (record layout): 1 = observed rates for all ages; 2 = **predicted for all ages**; 3 = combination. Nationally 4,639 tracts are flag 1, 4,872 flag 2 and 56,915 flag 3 (Arias et al. 2018, Vital Health Stat 2(181)).
  - Consequence: a flag-2 tract's e(0) is a function of its income, race/ethnicity and education composition; flag-3 tracts are partly so. The same circularity rule applies as for PLACES.
- **County Health Rankings & Roadmaps (CHR&R)** analytic data, 2025 release: one CSV, `https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2025_v2.csv` (796 columns; row 1 names, row 2 codes `vNNN_rawvalue`, `_numerator`, `_denominator`, `_cilow`, `_cihigh`, `_flag`; state and national rows mixed in).
  - Mortality measures come from NCHS death records with Census Population Estimates denominators: premature death (v001, YPLL before 75 per 100,000, age-adjusted), premature age-adjusted mortality (v127, deaths under 75 per 100,000, age-adjusted), life expectancy (v147), child (v128) and infant (v129) mortality, drug overdose (v138) and injury deaths (v135); 2020-2022 for the premature measures in the 2025 release. Counties with fewer than 20 deaths are missing.
  - Its BRFSS measures (diabetes v060, frequent physical v144 and mental v145 distress, % disability v180) are **PLACES model estimates**: the same circularity, at county level. % disability (v180) has a direct ACS equivalent.
  - Terms of use: non-commercial research and public-health use; cite "University of Wisconsin Population Health Institute. County Health Rankings & Roadmaps 2025"; no suggested endorsement. The engine caches the file and does not redistribute it.
- **CDC WONDER**: unchanged from PLAN_ROUND_20 section 8.1. County data only through the web form; the engine reads exported text files the user supplies.

## 11. Engine work, Part 2

**C1. The circularity rule, enforced (validation errors, not notes).** Registry: every measure records `kind` (`direct`, `model_based` or `partly_model_based`), its source model's covariate tables, and its **ACS equivalent** (tables that measure the same construct directly: PLACES DISABILITY and the six disability types: B18101-B18107; CHR v180: B18101; PLACES ACCESS2: B27010; PLACES FOODSTAMP: B22001 at household level). In `create_manifest`:
- **R1. Same construct.** An external outcome whose measure has an ACS equivalent is allowed only in a *measurement-comparison* analysis: the model contains a variable built from the equivalent tables, and every hypothesis on that analysis tests such a term. Otherwise: error, with the rule's text ("use the ACS's own measure, B18101, as the outcome; use the external source for measures the ACS lacks, such as diabetes"). Part 1's manifest passes (it is a comparison).
- **R2. Model inputs.** A hypothesis whose tested term draws on the source model's covariate tables (PLACES: age-sex, race/ethnicity, education, poverty; USALEEP: income, race/ethnicity, education) with an external outcome from that model is an error unless the hypothesis carries a written `circularity_justification`, which the methods text repeats. Controls that overlap stay notes.
- **R3. Composition confound stated.** Every analysis with a `model_based` or `partly_model_based` outcome gets the within-county (PLACES) or covariate-imputation (USALEEP) caveat in methods.md, as now.
- **MCP.** The server instructions, the core profile's instructions, `docs/agent_protocol.md` (new section 16, *External health data*), a recipe `external_health_outcome`, and a new tool `list_health_sources` (registry, measure kinds, ACS equivalents, the rule) state the rule in these words.

**C2. USALEEP connector (tract).** `SOURCES["usaleep"]` (release 2018, the publication year; data 2010-2015; tract vintage 2010; `partly_model_based`).
- Per-state A files, cached with SHA-256 sidecars; GEOIDs converted from Census 2010 codes to ACS codes (the existing `census2010_to_acs_geoid`).
- Parser: `<name>`, `<name>_se`, and `<name>_flag`. **Flag 2 (fully predicted) tracts are dropped by default** (`"include_predicted": true` keeps them, and R2 then applies to every tested term); the drop is recorded in run.json.
- **Rate apportionment to 2020 tracts** (`"apportion_to": 2020` on the entry): value_t = sum_s m_st v_s / sum_s m_st, with m_st the 2010 block population in source tract s and target tract t (block-weight crosswalk, Round 13). SE: sqrt(sum_s a_st^2 se_s^2) with a_st = m_st / sum m_st (independent tract estimates). A target needs at least 90% of its population mass covered by sources with a value, else missing. This is an approximation (life expectancy is not additive; a split tract inherits its parent's value), recorded in methods.
  - **Validation:** apportion ACS 2015-2019 crude disability prevalence (2010 tracts) to 2020 tracts and compare with ACS 2016-2020 (2020 tracts) for MI and NY: z-scores of the difference for 1:1, split and merged tracts (`docs/audits/rate_apportionment_validation.md`). Acceptance: median |z| for split and merged tracts no worse than 1.25 times the 1:1 tracts'.
  - **Result (2026-11-15): FAILED for split tracts** (median |z| ratio 1.33; merged 1.05). Consequence: `split: "missing"` is the default (split children are left missing); `split: "inherit"` is available and documented as not validated. A post hoc breakdown suggests children holding 95% or more of the parent's population behave like 1:1 tracts; not adopted, since it was found after the test.
- Join tolerance per source: USALEEP leaves tracts under 5,000 people unpublished (11.2% nationally), and flag-2 tracts are dropped, so its `external_join_failed` limit is 25% (registry `join_missing_limit`; 5% for PLACES, CHR&R and WONDER); the dropped counts are reported in run.json.
- R2 applies to USALEEP outcomes whether or not flag-2 tracts are kept (flag-3 tracts are partly predicted too).

**C3. County Health Rankings connector (county).** `SOURCES["chr"]` (release 2025, county only; `direct` mortality measures; `model_based` BRFSS measures with PLACES covariates and ACS equivalents where they exist).
- The file is cached with a sidecar; HTTP `Last-Modified` and `ETag` are recorded, since CHR&R reissues files.
- Parser: county rows only; `<name>`, `<name>_se` = (cihigh - cilow) / (2 x 1.96), `<name>_numerator`, `<name>_denominator`; flag 2 (suppressed) is missing and flag 1 (unreliable) is recorded.
- Measures the ACS itself supplies (CHR's ACS-derived columns) are not registered: the error says to use the ACS table.

**C4. WONDER export reader (Step 3).** `census.vital_records`:
- `read_wonder_export(path)` parses the tab-delimited export, the footer's dataset and query parameters, and the `Suppressed`, `Unreliable` and `Not Applicable` markers. Suppressed counts are kept as censored [0, 9], never zero. It refuses files without the footer (edited or partial).
- Crude rates get exact Poisson (Garwood) intervals; age-adjusted rates use WONDER's own SE when exported, else Fay-Feuer intervals need age-specific counts and are refused.
- Manifest `external` entries with `"source": "wonder"` take `"file"` and `"sha256"` (the export is pinned by hash; a different file is a validation error at run time).

**C5. Delete-one-cluster jackknife for `fit_eiv` (Part 1 F3).**
- `args.cluster_se`: `"cr1"` (default) or `"jackknife"` (CR3: delete-one-cluster refits from the per-cluster moment sums; exact, no re-estimation of covariances).
- Validated in `scripts/eiv_cluster_validation.py` beside CR1 (same cells). Acceptance: coverage of 0.87-0.93 at G >= 60 and at least CR1's at G = 30.

**C6. Diverging map scheme (Part 1 F1).** `make_map(..., scheme="diverging")`: symmetric breaks around 0 (or `center=`) with a red-blue palette, for residuals and gaps.

**C7. `run_variant` (Part 1 F2, Round 20 F8).** Exploratory refits of a completed run without Python: `run_variant(run_dir, analysis, formula=None, subset=None, cluster=None, cluster_se=None)` checks the analysed files' SHA-256 against run.json, refits, and writes the result labelled `exploratory` with the manifest hash. `subset` keeps or drops GEOID prefixes. Exposed as an MCP tool.

F4 (spatial HAC) and F5 (Round 20 age bands, NYC insets) stay in the backlog.

## 12. Study (Part 2): county premature mortality and the Round 20 determinants

The section 8 Step 3 pilot, with a direct outcome that has no model inputs: does the Round 20 determinant pattern for disability carry over to a hard outcome?

| Item | Choice | Why |
| :--- | :--- | :--- |
| Units | All MI (83) and NY (62) counties | Test states; the outcome is county-level |
| Outcome | `prem_mort`: CHR&R 2025 premature age-adjusted mortality (v127), deaths under 75 per 100,000, NCHS 2020-2022 | Direct vital records; age-adjusted; no ACS inputs (Population Estimates denominator) |
| ACS | 5-year 2022 (2018-2022), county, Census VRE replicates | Period overlaps 2020-2022 |
| Determinants | `pov_rate`, `pct_bachelors`, `no_vehicle`, `cost_burden`, `asdp` (age-standardized disability, all ages, 2000 standard), built as in Round 20 | Same constructs as Round 20 |
| Estimator | `fit_eiv`, outcome held fixed (independent error); units independent (no clustering unit with >= 20 groups above the county) | |
| Correction | Holm across four hypotheses, 90% intervals | |

**Hypotheses** (`examples/manifests/r21b_mi_ny_county_premature_mortality.json`), all `greater`:
- **H1** (m1: `prem_mort ~ pov_rate + C(state)`): premature mortality is higher where poverty is higher.
- **H2** (m2: `prem_mort ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + C(state)`): conditional on the others, higher where more households lack a vehicle.
- **H3** (m2): conditional on the others, higher where more households are cost-burdened.
- **H4** (m3: `prem_mort ~ asdp + C(state)`): higher where age-standardized disability prevalence is higher.

**Expectations stated before the data.** H1 and H4 are likely. H2 and H3 are open: among counties, no-vehicle and cost-burden shares are highest in New York City, whose premature mortality is not the highest in New York, and the county count (145) is small.

**Circularity.** None by construction; `create_manifest` must report no R1 or R2 finding. This is the worked example of the rule.

**Seen before registration:** the CHR&R file's header rows (names and codes) only. No CHR&R values, no county ACS values for these variables.

**Exploratory (labelled, `scripts/r21b_exploratory.py`):**
- **X1:** the same models with v001 (YPLL) and v147 (life expectancy, sign reversed).
- **X2:** jackknife versus CR1 standard errors on Part 1's H1-H3 (C5).
- **X3:** Part 1 E2 re-run with the crude adult ACS measure (`acs_dis`), the follow-up the Part 1 report asked for.
- **X4:** USALEEP tract life expectancy against Round 20 determinants on ACS 2011-2015 (native 2010 tracts, flag-2 tracts dropped, county-clustered), the first tract-level mortality look. Tested terms on education overlap the USALEEP model (R2), so it is reported with that caveat.
- **X5:** a map of m2 residuals (diverging scheme) and Moran's I.

## 13. Protocol, acceptance and release

- C1-C7 come with offline tests; C2's apportionment validation and C5's simulation pass; then `/code-review high` and its fixes.
- Then the manifest is committed alone, run, the exploratory analyses run, and the report written (`docs/studies/r21b_mi_ny_county_premature_mortality.md`, author self-review).
- Both suites run. The release stays **v0.20.0** (not yet tagged), covering Parts 1 and 2; the merge waits for the owner.

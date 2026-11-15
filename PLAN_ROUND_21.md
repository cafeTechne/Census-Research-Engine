# Round 21: External health outcomes (Step 2): CDC PLACES connector and a validation study

**Date:** 2026-11-14
**Status:** Implemented; study run and reviewed (section 9)
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

# Round 20: Public-health determinants: disability, housing cost burden, vehicle access

**Date:** 2026-11-14
**Status:** Implemented; study run and reviewed (section 9)
**Baseline:** v0.18.0 (Round 19, first complete preregistered study)
**Owner direction:** move the engine towards public-health research. The test study uses disability, housing cost burden, vehicle access and the social and economic determinants themselves, not insurance.

## 0. Why this round, and the three-step roadmap

The engine is strong on area-level social and economic measures with exact ACS sampling error. Public-health studies add three things it does not yet have:

| Step | What it adds | Round |
| :--- | :--- | :--- |
| **1. Health studies from ACS alone** | Age standardization of prevalences, a measurement-error-corrected regression for ACS-estimated determinants, and a preregistered disability study | **20 (this round)** |
| **2. External health outcomes** | Connectors for model-based and survey health data (CDC PLACES, USALEEP life expectancy, County Health Rankings and others) with provenance, uncertainty and circularity guards | 21 (section 7) |
| **3. Count-based outcomes** | Deaths, births and cases: rates with population denominators, age-adjusted rates with exact intervals, suppression, count models, small-area smoothing | 22+ (section 8) |

Steps 2 and 3 are specified here so that the roadmap is tracked in one place. Their detailed plans are written in their own rounds, informed by this round's friction log.

## 1. The study

**Question.** Across Michigan and New York census tracts in 2020–2024, is age-standardized disability prevalence higher where more households lack a vehicle and more households are housing-cost burdened, beyond what tract poverty and education account for?

Both determinants are standard social determinants of health:
- vehicle access limits reaching care, work and food;
- cost burden competes with health spending.

Disability is both a consequence and a cause of economic hardship. This is a **cross-sectional ecological association** study. It does not estimate causal effects in either direction.

| Item | Choice | Why |
| :--- | :--- | :--- |
| Release | ACS 5-year 2024 (2020–2024) only | One period on 2020 tracts: no harmonization, so this round's new methods are tested in isolation |
| Units | All tracts in Michigan (26) and New York (36) | Preferred test states |
| Outcome | `asdp`: age-standardized disability prevalence, % of the civilian noninstitutionalized population, `B18101` | Disability rises steeply with age, so crude prevalence mostly measures tract age structure. Direct standardization removes that |
| Standard | 2000 U.S. standard population (NCHS/SEER, Census P25-1130), single ages bundled with checksum. Bands 0–17, 18–34, 35–64, 65–74, 75+ (the `B18101` age groups, with under-5 and 5–17 combined, sexes combined) | The public-health convention, so rates compare with published age-adjusted rates |
| Determinants | `no_vehicle`: % of occupied housing units with no vehicle (`B25044`). `cost_burden`: % of households with housing costs ≥ 30% of income, renters (`B25070`) and owners with and without a mortgage (`B25091`), among those with the ratio computed. `pov_rate`: % below poverty (`B17001`). `pct_bachelors`: % of adults 25+ with a bachelor's degree or higher (`B15002`) | All on the tract VRE list for 2024, so each has exact replicate SEs |
| Replicates | `census_vre`, 80 replicates per table | Needed both for the SEs and for the measurement-error correction (A2) |
| Estimator | `fit_eiv` (A2): least squares corrected for the determinants' sampling error and for its correlation with the outcome's sampling error, using replicate error covariances. Sandwich SE | Round 19's review found covariate noise flattened a slope by about a third, and outcome–covariate error correlation was the same size. Determinants here have CVs of 15–60% at tract level |
| Reliability | CV screen at 30% on the outcome, **flag** only | As in Round 19 |
| Missing | Complete case; a tract with an empty age band has no age-standardized rate (A1) and is dropped and counted | |
| Correction | Holm across the three hypotheses, 90% intervals | |

**Hypotheses** (manifest `examples/manifests/r20_mi_ny_disability_determinants.json`):
- **H1** (m1: `asdp ~ pov_rate + C(state)`, `fit_eiv`): age-standardized disability prevalence is higher in tracts with higher poverty. Coefficient of `pov_rate`, one-sided `greater`.
- **H2** (m2: `asdp ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + C(state)`, `fit_eiv`): conditional on poverty, education and state, disability prevalence is higher where more households lack a vehicle. `no_vehicle`, one-sided `greater`.
- **H3** (m2): conditional on the same, disability prevalence is higher where more households are cost burdened. `cost_burden`, one-sided `greater`.

H1 is expected from the literature and serves as a check on the pipeline. H2 and H3 are open:
- poverty and education absorb much of the shared variation;
- in New York City, vehicle ownership mostly reflects transit, not deprivation;
- cost burden is high both in poor tracts and in expensive ones.

**What the authors had seen before registering:**
- county-level income and education in MI/NY (case study);
- Round 19's tract income and education;
- Round 16's tract poverty-rate sampling-error correlations, which used tract `B17001` replicate files for both releases.

No tract disability, vehicle or cost-burden data have been downloaded or computed (checked against the cache before registration, and recorded in the report).

## 2. Engine work (P0, offline tests first)

**A1. Age standardization (`census.standardize`) and manifest derivation `age_standardized`.**
- **Bundled standard populations.** `data/standard_populations/us2000.csv`: the 2000 U.S. standard population by single year of age, 0–84 and 85+. It is built from SEER's `singleages.pops.tables.csv` by `scripts/update_standard_populations.py`. The raw file is kept in `data/standard_populations/source/`. The sidecar JSON carries the source URL and the SHA-256 of both the raw file and the CSV, and loads are integrity-checked like the price tables.
- **Functions:**
  - `standard_weights(bands, standard="us2000")` gives weights for arbitrary age bands, checked to tile the bands without gaps or overlaps.
  - `direct_standardize(cases, populations, weights)` computes the direct rate sum_a w_a × cases_a / pop_a.
  - `age_adjusted_interval(...)` is the Fay–Feuer (1997) gamma interval. It is not used by this study, which has replicate SEs, but Step 3 needs it for registry counts.
- **Manifest derivation:**

  ```json
  {"name": "asdp", "op": "age_standardized", "as_percent": true, "standard": "us2000",
   "bands": [[0, 17], [18, 34], [35, 64], [65, 74], [75, null]],
   "groups": [{"num": [...], "den": [...]}, ...]}
  ```

  - There is one group per band. A list sums its members, e.g. the male and female cells.
  - `create_manifest` fills `weights` from the bundled standard before hashing, as it does for `rpp_year`. A manifest with explicit `weights` must match the standard, or declare `"standard": "custom"`.
- **Replicates.** On the replicates, the same formula is evaluated on each replicate, so the SE is the exact replicate SE. The frame path gives an approximate MOE from the per-band proportion MOEs.
- **Empty bands.** A band with zero population in the full-sample estimate leaves the rate undefined, so the unit is dropped as complete-case and counted. A zero replicate denominator follows the VRE documentation's ratio convention, as proportions already do.
- **Provenance.** The run records the weights, the standard and its table's SHA-256. `methods.md` states them.

**A2. `fit_eiv`: least squares corrected with replicate error covariances (friction F12).**
- **Estimator.** Let x_i be the design row of unit i built from the estimates, and x_i^(r) the same row built from replicate r (same patsy design information, so factor coding is fixed). The error covariances are S_i = 4/80 Σ_r (x_i^(r) − x_i)(x_i^(r) − x_i)ᵀ and s_i = 4/80 Σ_r (x_i^(r) − x_i)(y_i^(r) − y_i). Then

  β̂ = (Σ x_i x_iᵀ − Σ S_i)⁻¹ (Σ x_i y_i − Σ s_i).

  This is Fuller's (1987, *Measurement Error Models*, sections 2.2 and 3.1) moment estimator with known, heteroscedastic error covariance. Its new feature is that the covariances, including the outcome–covariate cross term, come from the ACS replicates. Interaction and transformed columns get their error covariance directly from their replicate design rows, and error-free columns (factors, constants) get zero.
- **Variance.** The sandwich estimator V = M⁻¹ (Σ ψ_i ψ_iᵀ) M⁻¹, with ψ_i = x_i (y_i − x_iᵀβ̂) − (s_i − S_i β̂) and M = Σ x_i x_iᵀ − Σ S_i. It treats tracts as independent. Round 16 measured that neighbouring tracts' sampling errors are nearly uncorrelated. The SE is reported as `se_total`; `se_model` is the naive model SE, and the naive estimates are reported alongside.
- **Diagnostics.**
  - Each noisy column's reliability, 1 − mean S_jj / Var(x_j), with x_j residualized on the error-free columns.
  - The smallest eigenvalue of M relative to that of X'X.
  - A note when reliability is below 0.5, where moment corrections become unstable. The fit is refused when M is not positive definite.
- **Scope.**
  - OLS only, with an optional `weights` column for WLS.
  - Targets `population` and `conservative` only. `these_areas` is refused: a measurement-error correction is a claim about the relationship, not about these tracts.
  - A unit with an incomplete replicate set raises the same strict-policy error as `fit_replicate`.
- **Manifest.** Method `fit_eiv` (`formula`, optional `args.weights`, `args.target`). Methods text and references are added.
- **Validation.** Offline simulation, with tests and an audit table (`docs/audits/eiv_validation.md`): heteroscedastic covariate error, outcome–covariate error correlation ±0.5, reliabilities 0.95, 0.8 and 0.6, synthetic replicates whose 4/80 sum reproduces the error covariance in expectation. Acceptance: |bias| < 10% of the naive bias, and 90% interval coverage of 0.87–0.93 at reliability ≥ 0.8. Naive OLS and `regression_calibration` are shown for comparison, the latter without the correlated-error term.

**A3. Reliability warning in `fit_replicate` (F12, part two).** `fit_replicate` reports in its diagnostics each numeric covariate's replicate reliability. When any is below 0.9, or two groups of a factor in the formula differ by more than 0.02, it adds a note recommending `fit_eiv`. The run record and `methods.md` carry it. This is a note, not a deviation.

**A4. Study outputs** follow Round 19 A4: the bundle and `analysed/` go to the release as an archive. The repository keeps the manifest, report, figures and summaries.

## 3. Study protocol

1. A1–A3 implemented with offline tests and the simulation validation; fast gate green.
2. Check the cache for tract `B18101`, `B25044`, `B25070` and `B25091` data, and record the result. Write the manifest, run `create_manifest` (fills the weights), and **commit it alone** (the preregistration commit), then push.
3. `run_manifest` live into `studies_output/r20/`.
4. Pre-specified **exploratory** analyses (labelled, with the manifest hash):
   - **E1:** naive `fit_replicate` (`conservative`) and `regression_calibration` versions of m1 and m2, to show what the correction changes.
   - **E2:** m2 without New York City (counties 005, 047, 061, 081, 085), and m2 per state. This tests whether the vehicle association is a transit artefact.
   - **E3:** crude rather than age-standardized prevalence, to show what standardization changes.
   - **E4:** drop CV-flagged tracts; household-weighted WLS.
   - **E5:** Moran's I of m2 residuals (queen contiguity), as the check on the independence assumption.
   - **E6:** maps of `asdp`, `no_vehicle` and `cost_burden`, with reliability marked.
5. The report `docs/studies/r20_mi_ny_disability_determinants.md` uses the same structure as Round 19, including the friction log and the review section.

## 4. Acceptance

- The manifest is committed before the first study data request.
- `confirmatory`, or `confirmatory_incomplete` reported with its deviations.
- Every reported number traces to a bundle file or a hashed exploratory output.
- A1–A3 have offline tests, and A2's simulation meets its criteria. The full suite passes on Python 3.14 and 3.10, except the known local-only 3.10 spatial λ test.

## 5. Out of scope this round

External data sources (Step 2), count outcomes (Step 3), change over time for disability (a later study can reuse Round 19's harmonization), spatial regression and causal designs.

## 6. Release

v0.19.0 with a Zenodo DOI, after `/code-review high` and its fixes, the full suite on Python 3.14 and 3.10, and the review section of the report. The owner delegates the review; it is labelled as an author self-review.

---

## 7. Step 2 (next round): external health-outcome data

### 7.1 Do we need APIs?

No API keys are needed. Every source below offers bulk file downloads (CSV, XLSX or zipped CSV) over plain HTTPS. The engine should treat them like the Census VRE and relationship files: download once into a cache, record the URL, retrieval time and SHA-256, parse locally, and refuse a file whose hash no longer matches the manifest's pinned value.

| Source | What | Geography / vintage | Access (verify URLs when implementing) | Uncertainty |
| :--- | :--- | :--- | :--- | :--- |
| **CDC PLACES** | About 40 model-based adult health measures: diabetes, obesity, COPD, depression, disability types, checkups, smoking and more | Tract, county, place, ZCTA. 2025 release mostly from BRFSS 2023 | data.cdc.gov (Socrata). Full CSV export per dataset, no key (an app token only raises rate limits). 2025 tract GIS-friendly dataset `yjkw-uj5s`, county `swc5-untb`. A state filter can be applied in the export query to avoid the full national file (about 800 MB) | 95% CIs, model-based (not sampling replicates) |
| **USALEEP** (NCHS) | Life expectancy at birth | Tract, **2010 tracts**, 2010–2015 | Static per-state CSV files from NCHS | Published SE |
| **County Health Rankings** | Compiled county measures: premature death, low birthweight, preventable hospitalizations and others | County, annual | Annual national CSV from countyhealthrankings.org | CIs for most measures |
| **CDC/ATSDR SVI** | Social Vulnerability Index | Tract, county | CSV per state or nation from ATSDR | Built from ACS: the engine can recompute it with exact replicate SEs, which is preferable to importing it |
| **USDA Food Access Research Atlas** | Low-income/low-access tract flags, distance to supermarkets | **2010 tracts** (2019 edition) | XLSX download from USDA ERS | None published |
| **HRSA shortage areas** | Primary care, dental and mental health HPSAs | Designation areas (county, tract groups) | CSV from data.hrsa.gov | None (administrative) |
| **EPA air quality** | Annual PM2.5 and ozone summaries | Monitors to county | Pre-generated annual files from EPA AirData (aqs.epa.gov) | Monitor coverage; no area SE |

### 7.2 Engine work (Round 21 sketch)

- **`census.health_sources`.** A registry of connectors, each pinning a dataset id and release and recording URL, licence, retrieval time and SHA-256. It provides a cache under `.cache/health/`, state-filtered downloads where the portal supports them, and parsers into the analysis-frame convention: estimate, SE from published CIs (half-width / z), `method` (`model_based`, `survey`, `administrative`), and geography vintage.
- **Manifest references to external variables,** e.g. `{"name": "diabetes", "ref": "places:2025:DIABETES:CrudePrev"}`. The source version is in the hash, and validation checks the source registry offline.
- **Vintage handling.** 2010-tract sources (USALEEP, Food Atlas) go through Round 19's harmonization, but only for counts. Rates need population-weighted apportionment, a new and documented approximation. Connecticut planning regions and the 2022 county change stay refused or explicit.
- **Uncertainty.**
  - Outcomes with known non-replicate variance use `fh_regression` (existing).
  - Determinants keep `fit_eiv` (A2) for their ACS error.
  - The outcome's error is independent of the ACS error, as a different survey, so the cross term is zero. The manifest declares this and the validator enforces it.
- **Circularity guard.** PLACES estimates come from multilevel regression and post-stratification of BRFSS, using demographic and area-level covariates. Regressing a PLACES outcome on those same covariates partly recovers the model, not the world. Each connector records its source model's covariates (to be verified against CDC's PLACES methodology), and `create_manifest` warns when a formula covariate overlaps them. The report template states it.
- **Spatial dependence of model-based outcomes.** PLACES tract estimates share county and state random effects, so their errors are correlated. Fits must say so, and the sandwich SE should cluster by county.

### 7.3 Pilot study for Step 2 (proposal)

PLACES 2025 tract disability measures (any disability, mobility) compared with Round 20's ACS age-standardized disability prevalence:
- This is a validation study: two independent measurement systems for the same construct.
- It tests the connector, the vintage join and the uncertainty treatment on a question where the answer is checkable.

## 8. Step 3 (after Step 2): count-based outcomes

### 8.1 Data access

- **CDC WONDER** (mortality, natality). County data are available through the web interface only: WONDER's API serves **national** data only, per NCHS vital-statistics data-sharing policy. Counts below 10 are suppressed, and rates from fewer than 20 deaths are flagged unreliable. The engine therefore ingests **exported WONDER text files** that the user downloads. It parses the query parameters from the export footer, records the file hash, and refuses edited files. It does not automate the web form.
- **State vital statistics** (Michigan MDHHS, New York State DOH): published downloadable tables, county or ZIP, per state. Connectors are written per state.
- Unsuppressed or record-level data need an NCHS Research Data Center application and are **out of scope**. The engine stays aggregate and public.

### 8.2 Methods to add

- Crude and age-adjusted rates with the population denominator chosen explicitly: ACS, Census Population Estimates, or WONDER's bridged or single-race estimates. The provenance records which, because the denominators differ.
- Age-adjusted rate intervals by Fay–Feuer gamma (A1 helper) and Tiwari et al. (2006) modification. Poisson exact intervals for crude rates.
- **Suppression handled as censoring** (count in [0, 9]), never zero-filled. Rate models use interval-censored likelihoods or bounds analyses.
- Count models (`poisson`, `negbin` with `exposure`, existing in `census.models`) in manifests with offsets, with overdispersion diagnostics.
- Small-area smoothing: empirical Bayes (Marshall 1991) first. Spatial BYM/ICAR models come later, and only if a study needs them, with validation like Round 16.
- Combining count outcomes with ACS determinants: `fit_eiv` generalizes to GLMs only approximately. A corrected-score or regression-calibration route for Poisson models, with simulation validation, is part of this step.

### 8.3 Pilot study for Step 3 (proposal)

County premature mortality (WONDER exports, ages < 75, age-adjusted) against ACS disability, vehicle and cost-burden determinants for MI and NY counties. This study carries the Round 20 hypotheses to a hard outcome.

---

## 9. Implementation status (2026-11-15)

| Item | Result |
| :--- | :--- |
| A1 | `census.standardize` (bundled 2000 U.S. standard, SHA-256 checked; `standard_weights`, `direct_standardize`, Fay–Feuer `age_adjusted_interval`); manifest derivation `age_standardized` (weights filled by `create_manifest`, exact replicate SEs) |
| A2 | `census.models.fit_eiv` (manifest method `fit_eiv`, `fit_model` method `eiv`). Validation `docs/audits/eiv_validation.md`: passed, coverage 0.89–0.92, bias removed in all 9 cells. Regression calibration coverage fell to 0.04–0.51 with correlated errors |
| A3 | `fit_replicate` reports covariate reliability per factor group and notes low or uneven reliability |
| Review | `/code-review high` before registration: 10 findings fixed. Most serious: the standard table was git-ignored; reliability was grouped by tract instead of state |
| Preregistration | Manifest `b67232d5…f833`, committed alone at `bb53959` (01:58:54Z); first study request 01:59:05Z |
| Results | H1 supported (+0.32 per point of poverty); H2 not supported pooled, but clear outside New York City (exploratory); H3 not supported (opposite sign, concentrated in New York State) |
| Lesson | Residuals are spatially autocorrelated; county-clustered SEs are 2–3× the registered ones (no conclusion changes). `fit_eiv(cluster=...)` added; validating it is the first item for the next health manifest |
| Report | `docs/studies/r20_mi_ny_disability_determinants.md`; friction F1–F5 fixed, F6 partly, F7–F10 backlog |

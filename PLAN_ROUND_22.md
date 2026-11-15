# Round 22: Count outcomes, spatial standard errors and a low birth weight study

Status: **planned, not started** (written 2026-11-15, after v0.20.0 / DOI 10.5281/zenodo.24260044).
Implementer: an external agent. This plan is written to be followed literally: do what it says, in the order
it says, and nothing else. Where a decision is not covered here, choose the smallest change that satisfies
the acceptance criteria, and record the decision in section 9 (implementation status). Do not redesign
anything that is not listed.

---

## 0. Ground rules (read first; these are owner requirements, not suggestions)

1. **Branch.** Work on a new branch `phase22/count-outcomes` created from `phase22/plan` (this plan, one
   commit on top of `defaultBranch` merge commit `07f58c6`, tag `v0.20.0`). The default branch is called `defaultBranch` (not `main`).
2. **No merging, no tags, no releases.** Push the branch and open one pull request against `defaultBranch`.
   The owner decides about merging. Do not create tags or GitHub releases.
3. **No AI attribution anywhere.** Commits and the PR body must not contain `Co-Authored-By`,
   `Generated with`, or any similar line, even if your tooling suggests one.
4. **Secrets.** The Census API key is in `.env` (`CENSUS_API_KEY`). Never print it, log it, commit it or put it in
   any output file. Before committing any output folder, check that the key string does not occur in it (read
   it with `dotenv_values`, search the bytes, print only the count of hits).
5. **No email or personal data** in User-Agent strings or requests. Use a generic client name.
6. **Do not automate CDC WONDER** (its terms forbid it) and do not circumvent bot checks or paywalls. This
   round needs no new download source: everything comes from the Census API, TIGER boundary files (already
   supported by `census/boundaries.py`) and the County Health Rankings file that is already cached at
   `.cache/health/chr/2025/analytic_data2025_v2.csv`.
7. **Circularity rule (owner rule; already enforced as R1/R2 by `census/manifest.py:circularity_errors`).**
   Determinant studies use the ACS's own measure where the ACS has one; model-based external estimates
   (CDC PLACES, County Health Rankings BRFSS measures) are used only for constructs the ACS lacks, and never
   tested against their model's inputs. Do not weaken or bypass R1/R2. The study in this plan uses a direct
   vital-records outcome (low birth weight) that the ACS does not measure, so R1/R2 do not fire; if they fire,
   something is wrong in your registration, not in the rule.
8. **Python.** Use `.venv/bin/python` (there is no `python` command). Supported versions are Python 3.11+
   with SciPy 1.16+. Run the test suite only on the project venv. Do not create other venvs, and do not run
   GitHub CI.
9. **No new dependencies.** Everything below is numpy/scipy/pandas/statsmodels/geopandas code that already
   exists in `requirements.txt`. Do not add PySAL estimators for this; do not add packages.
10. **No new MCP tools.** The tool count stays at 63. New features are new arguments of existing functions,
    documented in the existing tool docstrings and instructions.
11. **Pre-registration discipline (section 5).** You must not compute, plot or look at any association between
    low birth weight and the ACS determinants before the study manifest is committed and pushed. Looking at the
    outcome's own distribution and missingness is allowed (and needed to check feasibility).
12. **Pre-set criteria stay fixed.** The validation criteria in A2 and A4 are fixed here. If a validation fails,
    report FAILED, apply the stated consequence, and do not change the criterion, the simulation design or the
    seeds to make it pass. A post hoc analysis, clearly labelled post hoc, is allowed after the FAILED result.

**What the planner already saw (disclosure for the study's preregistration).** While writing this plan, the
planner looked only at the outcome's coverage in the cached file: 145 Michigan and New York counties; low
birth weight (`v037`) numerator missing for 1 county; median numerator 297 low-weight births; median
denominator 3,917 births. No association with any determinant was computed. Copy this paragraph into the
study report's preregistration section.

---

## 1. Why this round

- Round 21 Part 2 (county premature mortality) left a backlog in its friction log
  (`docs/studies/r21b_mi_ny_county_premature_mortality.md`, section 10):
  - F3: no valid clustering level for a two-state county study, with residual Moran's I 0.195. Standard
    errors assume independence and are probably too small.
  - F5: `run_manifest` labels a run of an exploratory manifest "confirmatory".
  - F6: rate apportionment of split tracts failed validation. A post hoc split by parent-population share
    suggested a rule worth re-testing on held-out states.
- The public-health roadmap (PLAN_ROUND_20 section 8.2) calls for count/proportion outcomes from vital
  records, with overdispersion handled. County Health Rankings 2025 publishes numerators and denominators for
  its vital-records measures, so a count model is possible without any new download.
- The owner's research focus is public health (disability, housing cost burden, vehicle access, social and
  economic determinants), not insurance. Low birth weight is a direct vital-records outcome the ACS does not
  measure, and fits the circularity rule.

## 2. Scope

In scope, in this order:

| Id | Work | Section |
| :--- | :--- | :--- |
| A1 | Manifest flag `"exploratory": true` (friction F5) | 3.1 |
| A2 | Spatial HAC (Conley) standard errors for `fit_eiv` and for `fit_replicate` binomial/Poisson GLMs, with a simulation validation | 3.2 |
| A3 | External count/proportion outcomes in `fit_replicate` (binomial with trials, Poisson with exposure, quasi-likelihood scale), register CHR `v037` low birth weight | 3.3 |
| A4 | Pre-registered re-test of split-tract apportionment on held-out states; new `split: "dominant"` policy only if it passes | 3.4 |
| S  | Study: low birth weight and the Round 20 determinants, Michigan and New York counties | 5 |

Out of scope (do **not** do these, even if they look easy):

- Measurement-error correction (EIV, corrected score, regression calibration) for GLMs. Covariate sampling
  error in GLMs is reported through `se_sampling` from replicates only, as `fit_replicate` already does.
- Negative binomial models for external outcomes, BYM/ICAR or other spatial random-effects models, empirical
  Bayes smoothing.
- New external sources or connectors; WONDER automation; any change to PLACES/USALEEP connectors except
  what A4 requires.
- Map insets, empty age bands, pandas performance, refactors, renames, formatting sweeps.
- Changes to the circularity rule, to existing validation criteria, or to existing study outputs/reports
  (other than the friction-log status column of `docs/studies/r21b_*.md`, see 6.3).

## 3. Engine work

Before writing code, read these to understand existing patterns (do not modify them beyond what is listed):
`census/manifest.py` (`validate_manifest` ~line 815, `circularity_errors`, `create_manifest` ~1224,
`_run_analysis` ~1393, `run_variant` ~1484, `run_manifest` ~1560 and the methods-text builder near ~2496/2796),
`census/models.py` (`_fit`, `_prepare`, `fit_replicate` ~371, `_cluster_jackknife` ~712, `fit_eiv` ~779),
`census/health_sources.py` (`_CHR_MEASURES`, `parse_chr`, `join_external`, `apportion_rates`,
`SPLIT_POLICIES`), `scripts/eiv_cluster_validation.py` and `docs/audits/eiv_cluster_validation.md` (the
validation pattern to copy), `scripts/rate_apportionment_validation.py` and
`docs/audits/rate_apportionment_validation.md`.

**Important existing trap:** in `census/manifest.py`, the decorator `@integrity_errors` must stay directly on
`run_manifest`. Do not insert new functions between that decorator and `run_manifest` (this broke a test in
Round 21).

### 3.1 A1: exploratory manifests

Behaviour:

- New optional top-level manifest key `"exploratory"` (boolean, default `false`). Any other type is a
  validation error: `exploratory must be true or false`.
- When `true`, `run_manifest` sets `analysis_status` to `STATUS_EXPLORATORY` (`"exploratory"`) in `run.json`, in
  the result dict it returns, and in every per-analysis provenance tag. Deviations are still detected and
  recorded exactly as now, but they do not turn the status into `confirmatory_incomplete`.
- The methods text gets one sentence at the start: "This analysis was registered as exploratory (manifest
  flag `exploratory: true`); its results are not confirmatory." Hypothesis results are still reported, with
  the column/label "exploratory" instead of "confirmatory".
- `create_manifest` writes the flag through unchanged and adds a note "registered as exploratory".
- The flag is part of the manifest, so it is covered by the manifest hash. Nothing else changes.

Tests (`tests/test_round22.py`, class `TestExploratoryFlag`): flag true → status "exploratory" in returned
dict and `run.json` and methods text sentence present; flag absent → unchanged behaviour (existing tests
must still pass); flag `"yes"` → validation error; a blocking deviation in an exploratory run → status still
"exploratory", deviation recorded. Use the same offline fixtures/mocks the existing manifest tests use
(look at `tests/test_round21.py` and `tests/test_round21_part2.py` for how runs are faked offline).

### 3.2 A2: spatial HAC (Conley) standard errors

New module `census/spatial_hac.py` (numpy only), with:

```python
EARTH_RADIUS_KM = 6371.0088

def haversine_matrix(lon, lat) -> np.ndarray:
    """n x n great-circle distances in km (inputs in degrees)."""

def conley_meat(scores: np.ndarray, dist_km: np.ndarray, cutoff_km: float) -> np.ndarray:
    """M = sum_i sum_j K(d_ij) s_i s_j', K(d) = max(0, 1 - d / cutoff) (Bartlett). scores is n x k."""

def conley_covariance(scores, bread_inv, dist_km, cutoff_km) -> tuple[np.ndarray, dict]:
    """V = bread_inv @ M @ bread_inv * n / (n - k). Returns (V, info) where info has
    {"kernel": "bartlett", "cutoff_km": c, "n": n, "mean_neighbours": mean count of j != i with d_ij < c,
     "min_eigenvalue": smallest eigenvalue of V, "psd": bool}."""
```

Rules:

- Kernel: Bartlett only. Cutoff must be a finite number > 0, else `ValueError`.
- The radial Bartlett kernel is not guaranteed positive semi-definite in two dimensions. If any diagonal
  element of V is ≤ 0, raise `ValueError("Conley covariance is not positive at cutoff ...")`. If V merely has a
  negative eigenvalue but positive diagonal, keep it and set `psd: False` (reported, not fatal).
- Small-sample factor n/(n − k), k = number of coefficients. No other adjustment.

Coordinates:

- New function `census/spatial_hac.py:unit_coordinates(geoids, level, acs_year)`. It returns a frame
  `GEOID, lon, lat` from TIGER cartographic boundary files via the existing
  `census.boundaries.get_boundaries(level, boundary_vintage(acs_year, level), state)` for each state in the
  GEOIDs. Use `representative_point()` after projecting to EPSG:4269 (as `census/boundaries.py:626` does). Missing
  GEOIDs → `ValueError` listing up to 10.
- It also returns the boundary files' SHA-256 values (the boundary cache already keeps sidecars; reuse them,
  do not recompute if a sidecar exists) so `run_manifest` can record them in provenance.
- Supported levels: `county` and `tract`. Anything else → `ValueError`.

`fit_eiv` (census/models.py):

- New keyword `spatial_se: Optional[Mapping] = None`, e.g. `{"cutoff_km": 150}`, plus keyword
  `coords: Optional[pd.DataFrame] = None` (GEOID, lon, lat). `spatial_se` requires `coords` and is mutually
  exclusive with `cluster` (`ValueError` if both).
- Use the same per-observation moment contributions that the CR1 path already sums per cluster. The Conley
  meat replaces the cluster meat; the bread is unchanged. Do not change the CR1 or jackknife code paths.
- Diagnostics: `diagnostics["spatial_se"] = info` (from `conley_covariance`), plus
  `diagnostics["se_independent"]`, the existing independence SE, for comparison. Add a note:
  "Spatial HAC (Conley) SEs, Bartlett kernel, cutoff C km". The interval/p-value use the Conley SE in place of
  the independence SE (same place where the cluster SE is used today).

`fit_replicate` (census/models.py), GLMs only:

- Same two keywords. Allowed only for `model` in (`binomial`, `poisson`); for other models raise
  `ValueError("spatial_se is supported for binomial and poisson models")`.
- Scores and bread at the full-sample fit (logit/log links, statsmodels defaults):
  - binomial with trials t_i and fitted μ_i: score s_i = x_i t_i (y_i − μ_i); bread A = Σ t_i μ_i (1 − μ_i) x_i x_iᵀ.
  - Poisson with exposure: s_i = x_i (y_i − μ_i); A = Σ μ_i x_i x_iᵀ.
  - V = A⁻¹ M A⁻¹ · n/(n − k). The sandwich does not use the dispersion scale (it is robust to overdispersion).
- The Conley SE replaces `se_model` (the "population" target). `se_sampling` from the replicates is
  unchanged; `se_total` is recomputed from the new `se_model`. Record `diagnostics["se_model_unadjusted"]`
  (the GLM model SE) and `diagnostics["spatial_se"]`.

Manifest (`census/manifest.py`):

- `fit_eiv` allowed args gain `spatial_se`. `fit_replicate` gets an explicit allowed-args check (it has none
  today). The allowed set is the union of what existing code passes through plus the new keys. Before writing
  it, collect the existing args with
  `grep -rn "fit_replicate" tests/ examples/ docs/recipes/ census/recipes.py` and the manifests in
  `examples/manifests/`. Then run `validate_manifest` on every file in `examples/manifests/*.json` to confirm
  none breaks.
- `spatial_se` value: an object with exactly one key `cutoff_km` (number > 0). Anything else → validation error.
- When any analysis has `spatial_se`, `run_manifest` calls `unit_coordinates` once for the analysed units and
  passes `coords`. The provenance records level, boundary year, files and SHA-256, and the cutoff.
- `run_variant` must accept `spatial_se` in `args` (so exploratory cutoffs can be refitted). Check that
  its existing argument validation passes the new key.
- Methods text: one sentence per analysis with spatial SEs: "Standard errors are spatial HAC (Conley 1999)
  with a Bartlett kernel and a C km cutoff, using great-circle distances between unit representative points
  (TIGER/Line cartographic boundaries, year Y); validated in docs/audits/spatial_hac_validation.md."
  Cite: Conley, T. G. (1999). GMM estimation with cross sectional dependence. Journal of Econometrics, 92(1),
  1–45.

Exact-identity unit tests (`tests/test_round22.py`, class `TestConley`; offline, synthetic coordinates):

1. **Independence limit.** With a cutoff below the minimum pairwise distance, `conley_meat` equals
   Σ s_i s_iᵀ (HC0 meat) to 1e-12.
2. **Cluster limit.** Put the units of each of G groups at one identical point, with groups ≥ 10 × cutoff apart.
   Then `conley_meat` equals the CR0 cluster meat Σ_g (Σ_{i∈g} s_i)(Σ_{i∈g} s_i)ᵀ to 1e-10. Do this
   for `fit_eiv` (compare against the meat its CR1 path builds, before CR1's own small-sample factor)
   and for the binomial `fit_replicate` path.
3. Haversine against two known distances: (0,0)–(0,1°) = 111.195 km ± 0.01; Detroit
   (−83.0458, 42.3314) to New York City (−74.0060, 40.7128) ≈ 775 km ± 5.
4. Errors: cutoff ≤ 0; `spatial_se` together with `cluster`; `spatial_se` with `model="ols"` in
   `fit_replicate`; a non-positive diagonal.
5. Manifest: `spatial_se` validation messages; `run_variant` accepts it.

Simulation validation (`scripts/spatial_hac_validation.py` → `docs/audits/spatial_hac_validation.md`;
copy the structure of `scripts/eiv_cluster_validation.py` and its audit):

- Locations: the 145 real Michigan and New York county representative points (2020 cartographic boundary
  files via `unit_coordinates`, cached after the first run).
- Spatial fields: a Gaussian field with exponential covariance exp(−d / r), drawn by Cholesky of the
  145×145 matrix (add 1e-10 to the diagonal), with range r ∈ {0 (independent), 50 km, 100 km}. x and the error
  are independent fields with the same r.
- Linear design (Conley used through the `fit_eiv` OLS sandwich path with no measurement error; if
  `fit_eiv` cannot run without replicates, call the internal sandwich function directly and say so in the
  audit): y = 1 + 0.5 x + e, with x and e at unit variance.
- Binomial design: trials t_i drawn once (seeded) from a lognormal with median 3,900 and log-sd 1.0, rounded,
  minimum 50; logit p_i = −2.6 + 0.3 x_i + u_i with u a spatial field (same r) of SD 0.15 (overdispersion);
  y_i ~ Binomial(t_i, p_i)/t_i.
- Estimators per replicate: independence SE (OLS HC0 / GLM model SE with scale "X2") and Conley at cutoffs
  50, 100, 150, 200 km. Target: the slope (0.5 or 0.3). Nominal 90% Wald intervals.
- 2,000 replicates per (design, r) cell, `numpy.random.default_rng(20261122 + cell_index)`. Report
  coverage, its Monte Carlo SE, mean SE / empirical SD, and the share of fits with `psd: False`.
- **Acceptance (pre-set, do not change): at the default cutoff 150 km, coverage ≥ 0.86 in all six cells
  (2 designs × 3 ranges).**
- **If PASSED:** manifests may use `spatial_se`; the recommended default in docs is 150 km for county studies.
- **If FAILED:** keep the functions and arguments for exploratory use (`run_variant`, direct calls), but
  `validate_manifest` refuses `spatial_se` in confirmatory manifests (allowed when `"exploratory": true`) with
  the message "spatial_se failed its validation (docs/audits/spatial_hac_validation.md); exploratory only".
  The study (section 5) is then registered without spatial SEs.
- Runtime: precompute the Cholesky factor once per r; the whole script should run in minutes. It may use the
  network only for the boundary files.

### 3.3 A3: external count and proportion outcomes in `fit_replicate`

Registry (`census/health_sources.py`, `_CHR_MEASURES`): add

```python
"v037": {"label": "Low birth weight: share of live births under 2,500 grams", "kind": "direct",
         "unit": "proportion of live births (0-1)", "count": {"numerator": "low birth weight births",
         "denominator": "live births"}},
```

and the per-measure source text that the other CHR vital-records measures use, with the data source
"National Center for Health Statistics, Natality files (NVSS), 2017–2023". Before writing it, confirm the years
against the CHR 2025 low birth weight page
(https://www.countyhealthrankings.org/health-data/population-health-and-well-being/quality-of-life/physical-health/low-birth-weight)
and the 2025 data dictionary (https://www.countyhealthrankings.org/sites/default/files/media/document/DataDictionary_2025.pdf).
If the cached `analytic_data2025_v2.csv` documents different years, use the file's years and record the
discrepancy in section 9. Do not register any other new measure.

Note: the CHR file's `v037_rawvalue` is already a proportion (e.g. 0.0705). `parse_chr` already produces
`<name>_numerator` and `<name>_denominator`, and `join_external` already joins them. Check this in a test.
Do not re-implement either.

`fit_replicate` / `_fit` (census/models.py):

- New keyword `scale: Optional[str] = None`. `None` keeps today's behaviour exactly. `"X2"` passes
  `scale="X2"` to the statsmodels GLM `.fit()` (quasi-binomial / quasi-Poisson: SEs multiplied by the square
  root of Pearson χ²/df). It is allowed only with `binomial` and `poisson`, else `ValueError`.
- For `binomial` and `poisson`, always record `diagnostics["pearson_dispersion"]` = Pearson χ² / residual df
  of the full-sample fit, whether or not `scale` is set. Add a note when it exceeds 1.5 and `scale` is not "X2"
  and `spatial_se` is not set: "Pearson dispersion D: model SEs assume no overdispersion; use scale='X2'".
- Replicate refits use the same `scale` (it does not change point estimates, so `se_sampling` is unaffected;
  check this in a test).

Manifest rules (`validate_manifest`), for a `fit_replicate` analysis whose outcome is an external variable:

1. `args.model` must be `ols`, `binomial` or `poisson`. `negbin` and `wls` with an external outcome are
   refused with a message naming this plan's out-of-scope reason ("not validated for external outcomes").
2. `binomial` needs `args.trials` naming `<outcome>_denominator`, where `<outcome>` is that analysis's
   external outcome. The effective-trials fallback (from an SE) is refused for external outcomes.
   `poisson` needs `args.exposure` naming `<outcome>_denominator`, and the outcome must be the count, so
   for Poisson the formula outcome is `<outcome>_numerator`. Allow the `_numerator` and `_denominator`
   column names of a declared external variable in formulas/args only in exactly these two roles.
   Everywhere else they stay unknown names.
3. `binomial` or `poisson` with an external outcome must set `args.scale: "X2"` or `args.spatial_se` (both
   allowed). Otherwise refuse: "overdispersion would be ignored: set scale 'X2' or spatial_se".
4. Units whose outcome is missing (suppressed or absent) are dropped by complete-case, as now. They count
   toward the existing join-missing limit. Low birth weight's "unreliable" flag (numerator < 20) is not a
   suppression: keep those units, and report their count in the methods text ("N counties had fewer than 20
   low-weight births (flagged unreliable by CHR&R); they were kept, weighted by their births").
5. R1/R2 (`circularity_errors`) apply unchanged. Add a test that `v037` with poverty, education, vehicle and
   cost-burden terms raises no R1/R2 error. Add a test that CHR `v060` (diabetes, PLACES-based) tested
   against `pov_rate` still raises R2.

Methods text for these analyses: "Coefficients were estimated by quasi-binomial regression (logit link,
statsmodels GLM, dispersion from Pearson χ²) of the low birth weight proportion with live births as trials"
(Poisson variant analogous: "quasi-Poisson regression of counts with the denominator as exposure"). Report
coefficients on the logit scale and add an odds-ratio column (`exp(estimate)` and exp of the interval ends)
to the hypotheses table in the bundle for binomial analyses. Do not change the table format for other models.

Tests (`tests/test_round22.py`, class `TestCountOutcomes`): scale None vs "X2" (same estimates, SEs ratio =
sqrt(dispersion)); `pearson_dispersion` recorded; overdispersion note; each manifest rule above (accept and
refuse); `v037` registry entry, kind "direct", source text; `parse_chr` on a small synthetic CHR-format file
yields `lbw`, `lbw_numerator`, `lbw_denominator`; an end-to-end offline manifest run with a synthetic external
binomial outcome (follow the offline run pattern of `tests/test_round21_part2.py`).

### 3.4 A4: held-out re-test of split-tract apportionment

Pre-registered hypothesis (record it in the audit before running, and commit the script change and this
hypothesis before the run): **split targets that hold at least 95% of their parent tract's 2010 population
behave like 1:1 targets.**

- Extend `scripts/rate_apportionment_validation.py` with `--parent-share-min 0.95` and `--out`. Do not change its
  default behaviour or its existing output file.
- Held-out states: **Ohio (39) and Pennsylvania (42)**. Do not use Michigan or New York (they generated the
  hypothesis). Same data and method as the Round 21 run: ACS 2015–2019 B18101 crude disability on 2010
  tracts apportioned to 2020 tracts, against ACS 2016–2020 native.
- Output: `docs/audits/rate_apportionment_retest.md` (a new file; the Round 21 audit stays unchanged).
- **Acceptance (pre-set): median |z| of split targets with parent share ≥ 0.95, divided by the median |z| of
  1:1 targets, ≤ 1.25 (the Round 21 criterion).** Also report the other share bands and merged/complex
  targets, as in Round 21.
- **If PASSED:** add `"dominant"` to `SPLIT_POLICIES` in `census/health_sources.py`. `apportion_rates(..., split="dominant")`
  gives a split target its parent's value only when the target holds ≥ 0.95 of the parent's population mass,
  else missing. Allow `split: "dominant"` for USALEEP `apportion_to` in manifests, with methods text citing the
  re-test. **The default stays `"missing"`.** Add tests for the new policy.
- **If FAILED:** no engine change. Record the result in the audit and in section 9.

---

## 4. Documentation and MCP (after A1–A4, before the study)

- `mcp_server.py` INSTRUCTIONS (the "External health data..." block) and the docstrings of `create_manifest`
  and `run_variant` in `census/workflows_inference.py`. Add, in at most 6 short lines:
  - the `exploratory` flag;
  - `spatial_se` (with the validation result and 150 km default for county studies, or "exploratory only" if
    A2 failed);
  - count outcomes (binomial with `<name>_denominator` trials and `scale: "X2"`).

  Keep the existing circularity text verbatim.
- `census/mcp_profiles.py` CORE_INSTRUCTIONS: no change unless a line is now false.
- `docs/agent_protocol.md`: in section 16, add a subsection "Count and proportion outcomes" (the A3 rules) and
  one paragraph on spatial standard errors. Do not renumber sections.
- `docs/recipes/external_health_outcome.md` and the matching `census/recipes.py` entry: add a binomial
  example (the m1 analysis of section 5).
- README "External health data" section: one bullet each for count outcomes and spatial SEs.
- CHANGELOG: new heading `## 0.21.0 (Round 22): count outcomes and spatial standard errors` with bullets
  for A1–A4 and the study. Bump the version to `0.21.0` in `census/__init__.py` (`__version__`),
  `census/pipeline.py` (`PACKAGE_VERSION`), and `CITATION.cff` (`version`, `date-released` = the day you
  finish). `tests/test_packaging.py` checks they match. Do not tag.

---

## 5. Study: low birth weight and the Round 20 determinants, Michigan and New York counties

### 5.1 Order (strict)

1. A1–A4 are done, with tests passing and the A2 and A4 validations run and committed.
2. Write the manifest `examples/manifests/r22_mi_ny_county_low_birth_weight.json`. Run `create_manifest` on
   it (offline validation plus resolution), and commit and push it. The commit message must include the
   manifest SHA-256 (see the commit `15ffb9e` of Round 21 for the format: "Preregister Round 22 study: ...
   (manifest SHA-256 <hash>)").
3. Only then call `run_manifest`.
4. Then run the exploratory analyses (5.5), write the report (5.6), and update the friction log.

### 5.2 Data

- Outcome: County Health Rankings & Roadmaps 2025, measure `v037` (low birth weight), external name `lbw`,
  source `chr`, release 2025, county level. Numerator: low-weight births; denominator: live births; NCHS
  natality 2017–2023 (or as confirmed in A3).
- Determinants: ACS 5-year 2018–2022 (references `2022:...`), the same as Round 21 Part 2.
- Geography: `{"level": "county", "states": ["26", "36"]}`; replicates `{"source": "census_vre"}`;
  `confidence_level` 0.90; correction Holm.
- Variables, derivations and the `cv_screen` exclusion (drop `asdp` from its variable list): copy verbatim from `examples/manifests/r21b_mi_ny_county_premature_mortality.json`
  the definitions of `pov_rate`, `pct_bachelors`, `no_vehicle` and `cost_burden`, with all the raw variables
  they need. Do **not** copy the B18101 disability variables or `asdp` (not used). Keep the variable names
  identical so results are comparable with Round 21 Part 2.

### 5.3 Analyses

Use `fit_replicate` (not `fit_eiv`, which is linear only):

| id | formula | args |
| :--- | :--- | :--- |
| m1 | `lbw ~ pov_rate + C(GEOID.str[:2])` | `{"model": "binomial", "trials": "lbw_denominator", "scale": "X2", "target": "population"}` |
| m2 | `lbw ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + C(GEOID.str[:2])` | same as m1 |

If A2 PASSED, add `"spatial_se": {"cutoff_km": 150}` to both analyses' args (keep `"scale": "X2"`; the
Conley sandwich ignores the scale, but the rule in 3.3 is satisfied either way). If A2 FAILED, do not add
it, and say in the report's limitations that the SEs assume spatial independence.

### 5.4 Hypotheses (all `"statistic": "coefficient"`, `"direction": "greater"`, Holm across H1–H3, 90%)

- **H1 (m1, term `pov_rate`).** "Across Michigan and New York counties, the County Health Rankings &
  Roadmaps 2025 low birth weight proportion (v037: live births under 2,500 g; NCHS natality 2017–2023) is
  higher where the ACS 2018–2022 poverty rate is higher, with state intercepts (quasi-binomial regression,
  logit link, live births as trials)."
- **H2 (m2, term `cost_burden`).** "Conditional on the poverty rate, the bachelor's share, the no-vehicle
  share and state, the county low birth weight proportion is higher where a larger share of households spends
  30% or more of income on housing costs."
- **H3 (m2, term `no_vehicle`).** "Conditional on the poverty rate, the bachelor's share, the cost-burden
  share and state, the county low birth weight proportion is higher where a larger share of occupied housing
  units has no vehicle available."

No other confirmatory hypotheses. Do not add a race/ethnicity term to the confirmatory models. It is the
exploratory X2 below, because a planner-added control after seeing Round 21 results should not change the
registered models.

### 5.5 Exploratory analyses (labelled exploratory everywhere; hashes in `docs/studies/r22/exploratory_summary.json`)

- **X1: without New York City.** A second manifest
  `examples/manifests/r22_x1_without_nyc.json` with `"exploratory": true` (A1). It is identical to the main
  one except for an exclusion of GEOIDs 36005, 36047, 36061, 36081 and 36085 (add `{"rule": "geoid_exclude", "geoids": [...]}` to
  `exclusions`, keeping the main manifest's `cv_screen` entry). Round 21 Part 2 found that these five counties reverse the vehicle
  association.
- **X2: race/ethnicity composition.** `run_variant` can only refit with columns already in the run's
  analysed data, so do X2 as a second exploratory manifest, `examples/manifests/r22_x2_race_composition.json`
  (`"exploratory": true`). It is identical to the main manifest plus raw variables `2022:B03002_001` and
  `2022:B03002_004`, a derivation `pct_nh_black` (proportion, `as_percent: true`), and m2 with `+ pct_nh_black`.
- **X3: spatial SE sensitivity.** Use `run_variant` on m1 and m2 with `spatial_se` cutoffs 50, 100 and 200 km.
  Do this even if A2 failed, labelled "not validated".
- **X4: residual map and Moran's I.** A diverging residual map of m2 (`make_map` with `scheme="diverging"`)
  and Moran's I with queen contiguity, permutation p-value with 999 permutations and seed 20261122, as in
  Round 21 Part 2 X5.
- **X5: Poisson cross-check.** `lbw_numerator ~ ... ` with `model: "poisson"`, `exposure: "lbw_denominator"`,
  `scale: "X2"`, on m2's terms. The coefficients should be close to the logit ones because LBW is rare. Report
  both.

Use `scripts/r22_exploratory.py`, modelled on `scripts/r21b_exploratory.py`, for X3–X5 (X1 and X2 run as manifests). Save outputs
under `studies_output/r22/` (git-ignored, as before), and copy the figures and a sanitized
`exploratory_summary.json` to `docs/studies/r22/`.

### 5.6 Report

`docs/studies/r22_mi_ny_county_low_birth_weight.md`. Copy the section structure of
`docs/studies/r21b_mi_ny_county_premature_mortality.md` exactly: Summary; 1 Question and hypotheses; 2 Data;
3 Preregistration (manifest hash, commit, the planner disclosure paragraph from section 0); 4 Engine work;
5 Results (table with estimate, 90% CI, odds ratio per 10 percentage points = exp(10 × estimate); all four
determinants are derived with `as_percent: true`, so one unit is one percentage point; Holm p, Supported / Not
supported); 6 Exploratory; 7 Interpretation; 8 Limitations; 9 Reproduction (exact commands); 10 Friction log;
11 Review.

- Review section heading: "Review (author self-review at the owner's request, not independent)". It is a
  self-review. Never call it independent.
- Required limitations: ecological (county) inference; LBW years 2017–2023 against ACS 2018–2022; no correction
  for covariate measurement error in a GLM (replicate `se_sampling` only); spatial dependence (with or without
  Conley, per A2); suppressed counties.
- Report results whatever they are. A non-supported hypothesis is a result, not a problem to fix.

### 5.7 Friction log

Keep a friction log while working (anything that needed a workaround, Python code outside the tools, or a
surprising behaviour). Put it in report section 10 with a Status column (Fixed / Backlog). Do not fix friction
items that are out of scope. Log them.

---

## 6. Verification, review and PR

### 6.1 Tests

- New tests live in `tests/test_round22.py` (A1–A3) and `tests/test_round22_a4.py` (A4 policy, only if A4
  passed). Tests must be offline (no network). Mock boundaries and the Census API the way existing tests do.
- Full suite: `.venv/bin/python -m pytest -q -p no:cacheprovider`. It takes about 20 minutes, so run it in the
  background. It must end with 0 failures. Report the exact pass, skip and fail counts in section 9.
- Also run `create_manifest` (validation) on every `examples/manifests/*.json` and report that all are valid,
  except those that were already invalid before your change. Check this on `defaultBranch` first.

### 6.2 Self-review before the study registration

After A1–A4 and before step 5.1.2, review your own diff (`git diff defaultBranch...HEAD`) for correctness:
off-by-one errors in kernel distances, wrong small-sample factors, scores with the wrong sign or weights, the
external-name handling of `_numerator` and `_denominator`, and anything that could change existing
behaviour when the new arguments are absent. Fix what you find, and list the findings and fixes in section 9.

### 6.3 Docs updates in earlier reports

Only this one: in `docs/studies/r21b_mi_ny_county_premature_mortality.md` section 10, change the Status cell
of F3 (spatial HAC) and F5 (exploratory flag), and of F6 if A4 ran, to "Addressed in Round 22 (see
PLAN_ROUND_22.md)", adding the A2/A4 result in a few words. Change nothing else in earlier reports.

### 6.4 PR

- Push `phase22/count-outcomes` and open a PR against `defaultBranch` titled
  "Round 22: count outcomes, spatial standard errors, low birth weight study".
- PR body:
  - what was done (A1–A4, study);
  - the validation results (PASSED/FAILED, with the key numbers);
  - the study results table;
  - test counts;
  - the friction backlog;
  - anything you could not do and why.
- No attribution lines (rule 0.3). Do not merge.

---

## 7. Acceptance checklist (all must be true before opening the PR)

- [ ] A1 implemented and tested; existing tests unchanged and passing.
- [ ] A2 implemented; identity tests pass; `docs/audits/spatial_hac_validation.md` committed with PASSED or
      FAILED and the stated consequence applied.
- [ ] A3 implemented; manifest rules enforced; `v037` registered with confirmed years.
- [ ] A4 re-test run on OH/PA with `docs/audits/rate_apportionment_retest.md` committed; `"dominant"` added
      only if PASSED; default still `"missing"`.
- [ ] Docs/MCP updated per section 4. MCP tool count is still 63.
- [ ] Manifest committed with its hash before `run_manifest`; study run, exploratory run, report written.
- [ ] Full suite 0 failures; all example manifests still valid.
- [ ] No API key, email or attribution lines in any commit, output or PR text.
- [ ] Section 9 of this plan filled in.

## 8. What to do when stuck

- If an existing function does not behave as this plan assumes (an argument is missing, a column is named
  differently), adapt with the smallest change. Record it in section 9 with the file and line. Do not
  restructure the module.
- If a requirement here conflicts with an existing test, do not delete or weaken the test. Stop working on that
  item, record the conflict in section 9 and in the PR body, and continue with the next item.
- If the Census API or the boundary download fails, retry later. Do not switch data sources or years.
- If the study cannot run as registered (for example, too many counties missing), do not edit the committed
  manifest. Record the deviation as the engine reports it, and report the run as `confirmatory_incomplete`.

## 9. Implementation status (to be filled in by the implementer)

| Item | Result | Notes (decisions, deviations, file:line) |
| :--- | :--- | :--- |
| A1 | | |
| A2 code | | |
| A2 validation | | |
| A3 | | |
| A4 | | |
| Docs/MCP | | |
| Self-review findings | | |
| Study registration (hash, commit) | | |
| Study results | | |
| Exploratory X1–X5 | | |
| Test suite counts | | |

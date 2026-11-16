# Does CDC PLACES see tract disability? PLACES 2025 against ACS 2020–2024, Michigan and New York tracts

**Status:** confirmatory run complete; reviewed (section 11 is the author's review, delegated by the owner, so it is not independent)
**Study plan:** [PLAN_ROUND_21.md](https://github.com/cafeTechne/Census-Research-Engine/blob/v0.21.0/PLAN_ROUND_21.md) (archived)
**Manifest:** [`examples/manifests/r21_mi_ny_places_disability_validation.json`](../../examples/manifests/r21_mi_ny_places_disability_validation.json), SHA-256 `11294774f00613a87f902393a8493a56d033591c3dbb6e7a8e4ac86a32221f76`
**Engine:** Census Research Engine, branch `phase21/health-sources` (released as v0.20.0)

## Summary

This is the engine's first study with an outcome from outside the ACS. CDC PLACES publishes model-based prevalences of 40 health measures for every census tract. They are widely used, but within a county they vary only through a tract's demographic composition (section 2). The study asks how far PLACES adult disability agrees with the ACS's direct survey estimate of the same construct, in 8,158 Michigan and New York tracts.

| Hypothesis | Result |
| :--- | :--- |
| **H1** PLACES disability is higher where ACS disability is higher (state intercepts) | **Supported**: +0.82 PLACES points per ACS point (90% CI 0.74 to 0.90) |
| **H2** The same holds within counties | **Supported**: +0.77 (90% CI 0.70 to 0.85) |
| **H3** The same holds within counties beyond adult age structure | **Supported**: +0.82 (90% CI 0.74 to 0.89) |

The run was confirmatory with no deviations. All Holm-adjusted p-values are below 10⁻⁶⁰. Standard errors are clustered by county (145 clusters), as registered.

The two systems agree on which tracts have more disability, but not on how much there is:
- **Levels differ by a factor of almost two.** PLACES averages 29.4% of adults and ACS 16.1%. The surveys ask similar questions in different settings (section 8). So PLACES values should not be read as ACS-comparable rates.
- **The agreement is not just age.** Within counties and holding the share of adults 65+ fixed, the slope is unchanged (H3). The demographic composition PLACES uses (sex, race/ethnicity and education besides age) carries real disability variation.
- **Reproducing the ACS pattern is not the same as measuring the world.** Rerunning Round 20's determinant models with PLACES as the outcome (E2) reproduces poverty and, more strongly, education: these are inputs to the PLACES model. It does not reproduce Round 20's cost-burden association. A PLACES outcome cannot test determinants that are themselves composition (section 7). *Addendum (section 12): against the crude adult ACS measure, the education gradient is inflated about 1.4×, not 2×; the missing cost-burden association is confirmed.*

**Method notes:**
- ACS sampling error in `acs_dis` and `pct65` is corrected by `fit_eiv`. The naive slope is 0.59, not 0.82: the reliability of tract ACS disability is only 0.72.
- The PLACES outcome's model error is independent of the ACS error. It is held fixed in the correction and enters the residual.

## 1. Question and hypotheses

| Id | Hypothesis (as registered, abridged) | Model (`fit_eiv`, OLS, county-clustered SEs) | Test |
| :--- | :--- | :--- | :--- |
| H1 | PLACES adult disability is higher where ACS adult disability is higher (state effects) | m1: `places_dis ~ acs_dis + C(state)` | `acs_dis` > 0 |
| H2 | ...within counties | m2: `places_dis ~ acs_dis + C(county)` | `acs_dis` > 0 |
| H3 | ...within counties, conditional on the share of adults aged 65+ | m3: `places_dis ~ acs_dis + pct65 + C(county)` | `acs_dis` > 0 |

`C(state)` is `C(GEOID.str[:2])` and `C(county)` is `C(GEOID.str[:5])`. Clusters are `GEOID.str[:5]`. The correction is Holm across all three hypotheses, at 90%.

**Expectations stated in the plan before the data:**
- H1 close to certain, because both measures rise with age;
- H2 likely;
- H3 open.

## 2. Data

| Measure | Source | Definition |
| :--- | :--- | :--- |
| `places_dis` | CDC PLACES 2025 release, tract dataset `cwsq-ngmh` (data.cdc.gov, public domain), measure `DISABILITY` | Crude % of adults 18+ reporting any of six disability types (BRFSS 2023), model-based |
| `acs_dis` | ACS 5-year 2024 (2020–2024), `B18101`, the four adult age bands, both sexes | % of civilian noninstitutionalized adults 18+ with any disability |
| `pct65` | Same table | Adults 65+ as a % of adults 18+ |

**How PLACES is made.** Multilevel regression and post-stratification of BRFSS responses. The model uses individual age, sex, race/ethnicity and education, the county share of adults below 150% of poverty (ACS), and state and county random effects. It is applied to 2020 census block population counts and summed to tracts. Within a county, a tract's PLACES value therefore changes only with its composition. The model has no tract-level information about health.

**Uncertainty.**
- **PLACES:** 95% intervals from 1,000 Monte Carlo draws. The engine records SE = interval width / 3.92. The intervals are close to symmetric (median upper/lower half-width ratio 1.05; 5th–95th percentile 0.96–1.18), so the approximation is adequate. These SEs are not used by `fit_eiv`, which takes the outcome's error from the residual.
- **ACS:** Census VRE replicate SEs (80 replicates).

**Join.**
- 8,414 tracts are in the ACS frame. 8,181 have complete ACS data, and 8,158 of those (99.7%) have a PLACES value. The 23 without one are mostly special-use tracts (codes 98xxxx: parks, airports, institutions) and a few New York City tracts.
- 14 PLACES tracts are not in the frame.
- The join limit (5% missing) was not approached.

**Provenance.**
- PLACES file SHA-256 `bc8bcf62…d344`, downloaded 2026-11-15T04:34:46Z, dataset revision `rowsUpdatedAt` 1765560443.
- Replicates canonical SHA-256 `2132417c…3cb6`.
- `bundle.json` SHA-256 `c8af1129…3911`.

**Seen before registration:**
- tract `B18101` estimates (Round 20 analysed them, including crude prevalence);
- the PLACES measure list, per-state row counts and identifier columns (queried without values to design the connector).

No PLACES estimate was downloaded before the preregistration commit `2af16e0` (2026-11-15T04:34:25Z, pushed before the run). `.cache/health` did not exist. The first PLACES download came 21 seconds after the commit.

## 3. Preregistration

The manifest was committed alone at `2af16e0` after the engine work, its code review and the clustered-SE validation. `create_manifest` recorded, for each analysis, the note that the outcome is model-based and that covariates outside the model act only through the model's inputs.

The circularity guard did not flag `pct65`, though it measures an input of the PLACES model (age), because it is built from `B18101` rather than an age-composition table. The guard works at table level. This limitation is documented in the code and in friction F6. H3 uses `pct65` deliberately, as a composition control.

## 4. Engine work in this round

- **`census.health_sources`:**
  - a registry of external sources;
  - the CDC PLACES connector: keyless Socrata CSV export filtered to states, measures and crude values, cached with SHA-256 sidecars;
  - the dataset revision stamp tied to the download;
  - an offline mode.
- **Manifest `external` variables:**
  - joined on GEOID after the ACS frame;
  - outcome-only, for `fit_eiv`, `fit_replicate` and `fh_regression`;
  - single release; vintage checked;
  - blocking `external_unavailable` and `external_join_failed` deviations;
  - circularity notes in `create_manifest` and `methods.md`.
- **`fit_eiv` additions:**
  - `fixed_variables` for outcomes from another survey;
  - `cluster="GEOID.str[:N]"`;
  - the independence SE kept in the diagnostics when a cluster is set.
- **Clustered sandwich validated by simulation** (`docs/audits/eiv_cluster_validation.md`, 500 per cell, 18 cells):
  - **G ≥ 60:** clustered 90% coverage 0.870–0.914, so acceptance passed. Three cells sit at 0.870–0.872, so CR1 is slightly liberal at strong clustering.
  - **Independence sandwich:** fell to 0.58–0.88 under clustering (G ≥ 60; 0.46 at G = 30).
  - **Bias:** removed everywhere.
- **`analysis_frame`** builds columns in one step (Round 20 F10).
- **`/code-review high` before registration:** 10 findings, all fixed. The most consequential were:
  - a `harmonize_tracts_to: 2010` manifest with 2020 releases would have joined 2020-tract PLACES rows to 2010-tract units unflagged;
  - multi-release manifests with external variables validated but could never run;
  - county-level paging was nondeterministic because crude and age-adjusted rows tie on the sort key.

## 5. Results

| | Corrected slope | 90% CI | Clustered SE | Independence SE | Naive slope | Reliability of `acs_dis` |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: |
| H1 (m1) | 0.818 | 0.740 to 0.896 | 0.047 | 0.023 | 0.588 | 0.72 |
| H2 (m2) | 0.771 | 0.695 to 0.847 | 0.046 | 0.029 | 0.500 | 0.65 |
| H3 (m3) | 0.819 | 0.744 to 0.894 | 0.045 | 0.029 | 0.538 | 0.65 |

- In m3, `pct65` has a coefficient of −0.19 (90% CI −0.23 to −0.15). With ACS disability held fixed, PLACES is *lower* in older tracts: PLACES's age gradient is flatter than the ACS's. This is consistent with BRFSS counting more disability among younger adults (cognition and mental-health-related limitations), but that explanation is untested.
- Clustered SEs are 1.6–2.0 times the independence SEs, in line with Round 20's lesson and the simulation.
- Simple correlation of the two measures: 0.63. Between-county variance is 35% of PLACES's total variance but 22% of the ACS's. PLACES is smoother within counties, as its county random effect and composition-only tract variation imply.

## 6. Robustness and exploratory analyses (labelled exploratory)

All analyses are in `docs/studies/r21/exploratory_summary.json`, labelled with the manifest hash and run by `scripts/r21_exploratory.py` on the hashed analysed data.

- **E1.** The registered refit reproduces the bundle exactly. Naive and independence numbers are in the table above.
- **E2: Round 20's models with PLACES as the outcome** (8,056 tracts with both outcomes, county-clustered):

  | Coefficient | ACS age-standardized disability (Round 20 outcome) | PLACES disability |
  | :--- | :--- | :--- |
  | m1 `pov_rate` | +0.32 (0.28 to 0.35) | +0.51 (0.48 to 0.54) |
  | m2 `pov_rate` | +0.30 (0.26 to 0.35) | +0.34 (0.31 to 0.37) |
  | m2 `pct_bachelors` | −0.09 (−0.10 to −0.07) | **−0.20** (−0.21 to −0.18) |
  | m2 `no_vehicle` | +0.006 (−0.009 to 0.020) | −0.016 (−0.039 to 0.007) |
  | m2 `cost_burden` | **−0.09** (−0.14 to −0.05) | +0.02 (−0.01 to 0.05) |

  - PLACES doubles the education gradient. Education is an input to the PLACES model. *(Against the age-standardized ACS outcome; against the crude adult ACS measure the ratio is about 1.4×: section 12.)*
  - PLACES loses the ACS's cost-burden association. Housing cost is not a model input.
  - This is the circularity problem seen in data: a determinant study with a PLACES outcome finds what the model put in.
  - One limit on the comparison: the ACS outcome here is age-standardized (all ages), while PLACES is crude (adults).
- **E3: PLACES "lack of reliable transportation" (`LACKTRPT`) against ACS households with no vehicle.**
  - Pooled: +0.13 (0.07 to 0.19), correlation 0.44.
  - Outside New York City: +0.45 (0.38 to 0.52). As in Round 20, vehicle access means something different in the city.
  - `LACKTRPT` was downloaded after the confirmatory run (SHA-256 `b89b7129…205c`).
- **E4: subsets.**
  - Without New York City: H1–H3 slopes 0.84, 0.78 and 0.80.
  - Michigan: 0.94, 0.85 and 0.87.
  - New York: 0.75, 0.73 and 0.79.
  - All are clearly positive.
- **E5: maps** of `places_dis`, `acs_dis` and the m1 residual, for each state, in `docs/studies/r21/`. The residual map uses a sequential palette for a signed quantity (friction F1).
- **E6: Moran's I of m3 residuals.**
  - Michigan 0.16 and New York 0.26 (both p < 0.001).
  - With county fixed effects and county clusters, the remaining dependence is among neighbouring tracts, partly across county lines. County clustering covers it only within counties (friction F4).

## 7. Interpretation

**What this validates.** PLACES ranks tracts by adult disability in broad agreement with the ACS, within counties too, and beyond age. Users wanting a tract disability measure from PLACES get one that tracks the direct survey estimate, with a slope near 0.8 after correcting the ACS's sampling noise.

**What it does not license:**
1. **Comparing levels with the ACS.** PLACES and ACS differ by about 13 points on average.
2. **Testing determinants that are PLACES model inputs or composition proxies** (education, poverty, age, race/ethnicity) with a PLACES outcome. E2 shows the result is inflated for model inputs and absent for determinants outside the model.
3. **Evaluating local programmes.** CDC states this too.

For determinant studies like Round 20, the ACS's own disability measure is the right outcome. PLACES is useful for measures the ACS lacks (diabetes, depression), with the circularity caution stated.

**Ecological and cross-sectional.** Nothing here concerns individuals or causation.

## 8. Limitations

- **Different instruments.** BRFSS (telephone, adults, self-report, six questions) and ACS (mail, phone and in-person, six questions in different wording, civilian noninstitutionalized) differ, so the slope mixes instrument and model differences.
- **Different periods.** PLACES uses BRFSS 2023 post-stratified to 2020 census counts; ACS covers 2020–2024.
- **Approximate PLACES SE.** The SE from a percentile interval is approximate. It was not used by the estimator.
- **Slightly liberal clustered SEs.** CR1 was slightly liberal in the simulation at strong clustering. With 145 clusters the effect is small, and no conclusion is near a boundary.
- **CV flags.** 1,087 tracts have an ACS disability CV above 30% (flagged, kept). The measurement-error correction is designed for exactly this.
- **Table-level circularity guard** (section 3).

## 9. Reproduction

```
python -c "from census.manifest import run_manifest; run_manifest('examples/manifests/r21_mi_ny_places_disability_validation.json', 'studies_output/r21/confirmatory')"
python scripts/r21_exploratory.py studies_output/r21/confirmatory studies_output/r20/confirmatory studies_output/r21/exploratory
python scripts/eiv_cluster_validation.py
```

- Needs a Census API key for the ACS. PLACES needs no key.
- The bundle, analysed data and exploratory outputs are attached to the v0.20.0 release as `r21_study_outputs.tar.gz`.
- PLACES is a live Socrata dataset. A later download may differ; the run records the SHA-256 and revision stamp of what was used.

## 10. Friction log

| Id | Friction | Status |
| :--- | :--- | :--- |
| F1 | `make_map` has no diverging scheme for signed values (residuals, gaps) | Backlog |
| F2 | Exploratory variants (E2–E4) again needed Python (Round 20 F8) | Backlog: `run_manifest_variant` |
| F3 | Clustered CR1 coverage sits at the 0.87 floor at strong clustering | Backlog: CR2/CR3 or wild cluster bootstrap option, validated the same way |
| F4 | Residual dependence across county lines (Moran's I 0.16 and 0.26 after county effects) | Backlog: spatial HAC (Conley) or larger clusters as a sensitivity check |
| F5 | Round 20 empty age bands (F7) and NYC map insets (F9) remain | Backlog |
| F6 | The circularity guard is table-level; composition shares built from other tables are not flagged | Documented; a variable-level tag would need the concordance's concept labels |
| F7 | 23 tracts with complete ACS data lack PLACES values (special-use tracts) | Recorded in run.json; below the 5% limit |

## 11. Review (author self-review at the owner's request, not independent)

**Preregistration integrity.** Confirmed:
- the manifest commit `2af16e0` predates the first PLACES download (21 seconds later);
- the manifest hash in every bundle file matches;
- no deviation was recorded.

**Checks repeated for this review:**
1. The exploratory refit of m1–m3 reproduces the bundle's estimates and SEs exactly.
2. The PLACES file's SHA-256 matches its sidecar, and the join counts in run.json were recomputed from the analysed frame.
3. The clustered SE is used for the intervals: m1's interval half-width / SE = 1.645.
4. Interval symmetry was checked (section 2).

**Judgement on the claims:**
- **H1–H3 are supported with large margins**, robust to dropping New York City and to analysing each state alone.
- **The level difference is descriptive.** The report does not attribute it to a cause beyond naming the instrument differences.
- **E2's circularity reading is the main substantive claim beyond the hypotheses.** It is exploratory, rests on one study area, and compares an age-standardized ACS outcome with a crude PLACES one. It should be checked on a crude-adult ACS outcome before being cited. That is a short follow-up with the existing data.
- **The `pct65` sign** is reported with its untested explanation marked as such.

**Recommendation.** Have someone independent review the report before citing it externally. Run the crude-adult version of E2 next round.

## 12. Addendum (2026-11-15): E2 with the crude adult ACS measure

The review above asked for E2 on a like-for-like ACS outcome. Round 21 Part 2 ran it as exploratory analysis X3 (`docs/studies/r21b_mi_ny_county_premature_mortality.md` section 6; `docs/studies/r21b/exploratory_summary.json`). It fits Round 20's models on 8,129 tracts with three outcomes, county-clustered, 90% intervals:

| Term | ACS crude adult (`acs_dis`) | PLACES | ACS age-standardized (`asdp`) |
| :--- | ---: | ---: | ---: |
| m1 `pov_rate` | 0.29 (0.25 to 0.33) | 0.49 (0.46 to 0.53) | 0.32 (0.29 to 0.35) |
| m2 `pct_bachelors` | −0.14 (−0.16 to −0.12) | −0.20 (−0.21 to −0.19) | −0.09 (−0.10 to −0.07) |
| m2 `cost_burden` | −0.14 (−0.18 to −0.09) | +0.02 (−0.01 to 0.05) | −0.09 (−0.14 to −0.05) |

- **Correction.** Against the crude adult measure, PLACES inflates the education gradient by about 1.4× (−0.20 against −0.14), not the 2× reported in E2. Part of that difference came from comparing a crude outcome with an age-standardized one.
- **Confirmed.** PLACES inflates the poverty gradient (1.7× in m1). Its cost-burden association is absent, while both ACS measures show it.
- **Consequence.** The circularity reading stands, and the engine now enforces it. `create_manifest` refuses PLACES disability as the outcome of a determinant study (rule R1) and refuses tested terms built from PLACES model inputs (rule R2).


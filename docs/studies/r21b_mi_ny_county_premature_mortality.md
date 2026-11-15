# Premature mortality and the Round 20 determinants: Michigan and New York counties

**Status:** confirmatory run complete; reviewed (section 11 is the author's review, delegated by the owner, so it is not independent)
**Study plan:** [PLAN_ROUND_21.md](../../PLAN_ROUND_21.md) Part 2, section 12
**Manifest:** [`examples/manifests/r21b_mi_ny_county_premature_mortality.json`](../../examples/manifests/r21b_mi_ny_county_premature_mortality.json), SHA-256 `8df6b790ae8bd11347f8069e2a6fca16bf29f08e4606d921efb7578e31d470e2`
**Engine:** Census Research Engine, branch `phase21/health-sources` (to be released as v0.20.0)

## Summary

This is the engine's first study with a **direct** health outcome from outside the ACS: county premature age-adjusted mortality (deaths under 75 per 100,000) from NCHS death records, 2020–2022, as published by County Health Rankings & Roadmaps (CHR&R) 2025. Death records have no ACS inputs, so the circularity rule this round enforces is satisfied by construction. `create_manifest` reported no R1 or R2 finding. The study carries the Round 20 disability determinants to a hard outcome in all 145 Michigan and New York counties.

| Hypothesis (all one-sided, "greater") | Result |
| :--- | :--- |
| **H1** Higher where poverty is higher | **Supported**: +13.0 deaths per 100,000 per poverty point (90% CI 10.6 to 15.5; Holm p = 2.6 × 10⁻¹⁸) |
| **H2** Higher where more households have no vehicle, given poverty, education and cost burden | **Not supported**: −0.90 (−1.82 to 0.02; p = 0.95) |
| **H3** Higher where more households are cost-burdened, given the others | **Not supported**: +0.82 (−1.07 to 2.72; p = 0.47) |
| **H4** Higher where age-standardized disability prevalence is higher | **Supported**: +22.4 per disability point (19.0 to 25.8; p = 7.2 × 10⁻²⁷) |

The run was confirmatory, with no deviations. All 145 counties joined, and no outcome was suppressed. The pre-registration expected H1 and H4, and stated that H2 and H3 were open because county no-vehicle shares are dominated by New York City.

- **Poverty and disability track premature death.** Counties one standard deviation higher in poverty (3.5 points) have about 46 more premature deaths per 100,000 (mean 405). Counties one SD higher in age-standardized disability (2.6 points) have about 58 more. The same pattern holds for years of potential life lost and life expectancy (X1).
- **The vehicle result is a New York City result.** Manhattan has the highest no-vehicle share (78%) and the lowest premature mortality (259). Without the five NYC counties, the no-vehicle coefficient is **+5.8** (90% CI 1.0 to 10.7; exploratory X1b), in the hypothesized direction. With 145 counties, five extreme units decide H2.
- **Cost burden is unrelated to premature mortality** once poverty and education are held fixed. This holds in every variant.

## 1. Question and hypotheses

Round 20 found that tract disability prevalence rises with poverty and falls with education. Its vehicle and cost-burden hypotheses were mixed. Disability is a survey measure. This study asks whether the same determinants track a hard outcome measured independently of the ACS: deaths before age 75.

| Analysis | Formula | Tested |
| :--- | :--- | :--- |
| m1 | `prem_mort ~ pov_rate + C(state)` | H1 `pov_rate` |
| m2 | `prem_mort ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + C(state)` | H2 `no_vehicle`, H3 `cost_burden` |
| m3 | `prem_mort ~ asdp + C(state)` | H4 `asdp` |

There is a Holm correction across the four hypotheses, and intervals are 90%.

## 2. Data

- **Outcome:** CHR&R 2025 analytic data (`analytic_data2025_v2.csv`, SHA-256 `fe94ca50…aefbcf`, 13,085,361 bytes, downloaded 2026-11-15T16:42:29Z, after the manifest commit).
  - Measure v127: premature age-adjusted mortality, deaths among residents under 75 per 100,000, age-adjusted.
  - Source: NCHS mortality files 2020–2022, by county of residence. Denominators are Census Population Estimates.
  - CHR&R leaves counties with fewer than 20 deaths missing; none of the 145 were.
  - Uncertainty: the SE is the published 95% interval width / 3.92.
  - Licence: CHR&R terms (non-commercial research use, citation). The file is cached locally and not redistributed.
- **ACS:** 5-year 2018–2022, counties, with Census VRE replicates for B15002, B17001, B18101, B25044, B25070 and B25091. Variables are built exactly as in Round 20: poverty rate, share of adults 25+ with a bachelor's degree, no-vehicle share, housing cost-burden share (30%+), and age-standardized disability prevalence (all ages, 2000 standard).
- **Estimator:** `fit_eiv`. The outcome is held fixed (independent error, no replicates) and the covariates are corrected for ACS sampling error. Units are treated as independent, because no grouping above the county has 20 or more units in two states.
- **Descriptives** (exploratory summary):

  | Variable | Mean | SD | Min | Max |
  | :--- | ---: | ---: | ---: | ---: |
  | `prem_mort` | 404.9 | 75.8 | 242.4 | 593.1 |
  | `pov_rate` | 13.1 | 3.5 | 4.9 | 26.9 |
  | `pct_bachelors` | 26.8 | 10.0 | 12.2 | 62.8 |
  | `no_vehicle` | 8.7 | 9.0 | 2.2 | 77.9 |
  | `cost_burden` | 26.3 | 5.8 | 16.4 | 54.9 |
  | `asdp` | 13.8 | 2.6 | 7.7 | 21.6 |

  Michigan averages 427.5 and New York 374.5. The NYC counties: Bronx 482.7, Kings 339.3, New York 259.4, Queens 297.5, Richmond 329.0.

## 3. Preregistration

- **Commits:**
  - The engine work and the code-review fixes were committed first (`50f6165`, `8cf2d17`).
  - The manifest was committed **alone** as `15ffb9e` at 2026-11-15T16:41:51Z and pushed.
  - The CHR&R file was first downloaded at 16:42:29Z.
- **Seen before registration:** only the CHR&R file's two header rows (column names and codes). No CHR&R values were seen. No county ACS values for these variables were seen, though Round 20 analysed the same constructs on tracts.
- **create_manifest:** valid. Its notes:
  - m1–m3 have a direct external outcome, so no circularity check applies;
  - the general rule text.
- **Exploratory analyses (X1–X5)** were listed in PLAN_ROUND_21 section 12 before the run.

## 4. Engine work in this round (Part 2)

- **The circularity rule is enforced** (`create_manifest` errors):
  - **R1:** an external outcome whose construct the ACS measures directly (PLACES disability: B18101) is allowed only to compare against that ACS measure;
  - **R2:** a tested term built from the outcome model's inputs needs a written justification.
  - The MCP states the rule in its instructions, the core profile, protocol section 16, a recipe and `list_health_sources`.
- **Connectors:**
  - USALEEP (tract life expectancy). Fully predicted tracts are dropped. New York City comes from its own file.
  - CHR&R (county). Direct mortality measures, plus flagged PLACES-based measures; ACS-derived columns are refused.
  - WONDER exports (pinned by SHA-256; suppressed counts censored).
- **Rate apportionment to 2020 tracts.** Split tracts are left missing because inheriting the parent's rate **failed** its pre-set validation: median |z| ratio 1.33 > 1.25 (`docs/audits/rate_apportionment_validation.md`).
- **`fit_eiv(cluster_se="jackknife")`:** delete-one-cluster SEs. Validated: coverage 0.872–0.916 at G ≥ 60, and better than CR1 at G = 30 (`docs/audits/eiv_cluster_validation.md`).
- **Diverging maps** (`scheme="diverging"`) and **`run_variant`**, which runs exploratory refits of a finished run as an MCP tool.
- **Review:** `/code-review high` before registration found 10 issues, all fixed. Among them:
  - jackknife refits without the reference county were collinear;
  - per-source join limits;
  - WONDER files are now checked at registration;
  - apportionment methods text contradicted the split policy.

## 5. Results

| Term | Corrected | 90% CI | Naive | Reliability |
| :--- | ---: | :--- | ---: | ---: |
| m1 `pov_rate` (H1) | **13.02** | 10.58 to 15.47 | 12.13 | 0.93 |
| m2 `pov_rate` | 9.78 | 7.52 to 12.04 | 8.87 | 0.93 |
| m2 `pct_bachelors` | −3.88 | −4.69 to −3.06 | −3.95 | 0.99 |
| m2 `no_vehicle` (H2) | **−0.90** | −1.82 to 0.02 | −0.68 | 0.99 |
| m2 `cost_burden` (H3) | **0.82** | −1.07 to 2.72 | 0.64 | 0.95 |
| m3 `asdp` (H4) | **22.41** | 19.00 to 25.82 | 20.62 | 0.92 |

- County ACS estimates are reliable (0.92–0.99), so the error correction is small: 7–9% for poverty and disability.
- Holm-adjusted p-values: H1 2.6 × 10⁻¹⁸, H2 0.95, H3 0.47, H4 7.2 × 10⁻²⁷.

## 6. Exploratory analyses (labelled exploratory; hashes in `docs/studies/r21b/exploratory_summary.json`)

- **X1: other mortality outcomes** (CHR&R v001 YPLL before 75 and v147 life expectancy, same file, same models):

  | Term | YPLL per 100,000 | Life expectancy (years) |
  | :--- | ---: | ---: |
  | m1 `pov_rate` | +275 (214 to 337) | −0.30 (−0.38 to −0.23) |
  | m2 `no_vehicle` | −25 (−48 to −1) | +0.05 (+0.02 to +0.07) |
  | m2 `cost_burden` | +12 (−33 to 57) | −0.00 (−0.05 to 0.05) |
  | m3 `asdp` | +511 (433 to 588) | −0.59 (−0.68 to −0.50) |

  All three outcomes tell the same story: poverty and disability carry mortality; the no-vehicle sign is reversed by NYC; cost burden is null.
- **X1b: without the five NYC counties** (140 counties):
  - `no_vehicle` **+5.8** (1.0 to 10.7);
  - `cost_burden` +2.2 (−0.5 to 4.8);
  - `pov_rate` (m2) +6.5 (3.6 to 9.3);
  - H1 slope +14.6, H4 slope +22.3.

  Outside NYC, where a missing vehicle usually means poverty rather than transit, it marks higher premature mortality beyond poverty and education.
- **X2: Part 1 with the jackknife** (`run_variant`; Part 1 manifest `11294774…`). The slopes of PLACES on ACS disability keep their values, and jackknife SEs are 7–14% above CR1:

  | Part 1 model | Jackknife SE | CR1 SE | 90% CI |
  | :--- | ---: | ---: | :--- |
  | m1 | 0.054 | 0.047 | 0.73 to 0.91 |
  | m2 | 0.050 | 0.046 | 0.69 to 0.85 |
  | m3 | 0.048 | 0.045 | 0.74 to 0.90 |

  The Part 1 conclusions are unchanged.
- **X3: Part 1 E2 with the crude adult ACS measure** (the follow-up the Part 1 review asked for; 8,129 tracts, county-clustered):

  | Term | ACS crude adult (`acs_dis`) | PLACES (`places_dis`) | ACS age-standardized (`asdp`) |
  | :--- | ---: | ---: | ---: |
  | m1 `pov_rate` | 0.29 (0.25 to 0.33) | 0.49 (0.46 to 0.53) | 0.32 (0.29 to 0.35) |
  | m2 `pct_bachelors` | −0.14 (−0.16 to −0.12) | −0.20 (−0.21 to −0.19) | −0.09 (−0.10 to −0.07) |
  | m2 `cost_burden` | **−0.14** (−0.18 to −0.09) | +0.02 (−0.01 to 0.05) | −0.09 (−0.14 to −0.05) |
  | m2 `no_vehicle` | 0.02 (0.00 to 0.04) | −0.01 (−0.04 to 0.01) | 0.01 (−0.01 to 0.02) |

  - **Correction to Part 1:** against the like-for-like crude adult measure, PLACES inflates the education gradient by about **1.4×**, not the 2× Part 1 reported. Part of that gap was age standardization.
  - The poverty gradient is inflated 1.7× (m1). Poverty enters the PLACES model at county level.
  - The cost-burden association is present in both ACS measures and **absent in PLACES**. This part of the circularity reading is confirmed, and stronger.
  - The Part 1 report now carries this as an addendum.
- **X4: USALEEP tract life expectancy** (exploratory manifest `e17ffa55…`, not pre-registered; ACS 2011–2015 on native 2010 tracts; county-clustered):
  - **Join:** 6,171 of 7,499 complete tracts (17.7% missing; 957 fully predicted tracts dropped by default).
  - **Results:**

    | Term | Years of life expectancy (90% CI) |
    | :--- | :--- |
    | `pov_rate` | −0.19 (−0.21 to −0.17) |
    | `asdp` | −0.58 (−0.63 to −0.54) |
    | `no_vehicle`, given the others | +0.016 (+0.005 to +0.028) |
    | `cost_burden`, given the others | +0.02 (−0.02 to +0.06), null |

  - `pct_bachelors` (+0.06) is a USALEEP model input. It was used as a control only (rule R2), so its coefficient is not interpreted.
  - A first run left 54% of New York tracts unmatched: New York City's USALEEP file is separate. The connector was fixed before any X4 coefficient was read (section 10, F2).
- **X5: residual map and spatial dependence.** The m2 residual map is `docs/studies/r21b/resid_m2.png` (diverging scheme). The premature mortality maps are `prem_mort_26.png` and `prem_mort_36.png`. Moran's I of the m2 residuals is **0.195** (permutation p = 0.001, queen contiguity).

## 7. Interpretation

- **Poverty and disability are strong county-level markers of premature death in these states.** The associations survive measurement-error correction and appear with three mortality measures and at tract level (USALEEP). They are associations among areas, not causal effects, and not individual risks.
- **Vehicle access is not a usable county determinant across this whole sample.** NYC turns it into an urbanicity marker. The hypothesis was registered pooled, and it is not supported as registered. The NYC-excluded estimate (X1b) is exploratory and should be tested in a pre-registered design that handles transit-rich areas: tract level with county effects, or excluding transit-dense counties by a rule fixed in advance.
- **Cost burden is null for mortality and negative for disability (X3).** Round 20's negative cost-burden coefficient (more burden, less age-standardized disability given poverty) reappears with the crude adult measure. It probably reflects housing markets: high-cost areas attract younger and healthier residents. It is not a protective effect.
- **The circularity lesson holds, and is now enforced.** A PLACES outcome reproduces its model's inputs (poverty 1.7×, education 1.4× against the ACS) and misses the cost-burden pattern the ACS shows. This study used a direct outcome, as the rule requires.

## 8. Limitations

- **Spatial dependence.** County residuals are spatially autocorrelated (Moran's I 0.195), so the independence sandwich probably understates the SEs.
  - With two states, no clustering level has 20 or more groups. The registered SEs are therefore the only ones reported.
  - H1 and H4 have z above 8, so their support is not in doubt. The interval widths are.
- **Small n and leverage.** 145 counties; five NYC counties drive H2.
- **Periods differ:** deaths 2020–2022 against ACS 2018–2022, which covers the COVID-19 years in both. Denominators differ too: Population Estimates against the ACS.
- **The outcome's uncertainty is approximate.** The SE comes from CHR&R's published interval. The outcome is held fixed, so its error enters the residual.
- **Ecological design.** Associations among counties are not individual risks.
- **Exploratory results need confirmation:** X1b, X3 and X4 rest on one study area.

## 9. Reproduction

```bash
# confirmatory
python -c "from census.manifest import run_manifest; run_manifest('examples/manifests/r21b_mi_ny_county_premature_mortality.json', 'studies_output/r21b/confirmatory')"
# exploratory X4 (USALEEP), then X1-X5
python -c "from census.manifest import run_manifest; run_manifest('examples/manifests/r21b_x4_usaleep_exploratory.json', 'studies_output/r21b/x4')"
python scripts/r21b_exploratory.py studies_output/r21b/confirmatory studies_output/r21/confirmatory \
    studies_output/r20/confirmatory studies_output/r21b/x4 studies_output/r21b/exploratory
```

- **Bundle:** `bundle.json` SHA-256 `f2da468a…92e5`.
- **Exploratory summary:** SHA-256 `c0524479…a954`. A copy with local paths removed is in `docs/studies/r21b/exploratory_summary.json`.
- **Required:** the Census API key in `.env` (our runs only). CHR&R and USALEEP downloads are keyless.

## 10. Friction log

| Id | Friction | Status |
| :--- | :--- | :--- |
| F1 | The CHR&R methods text described both the direct mortality source and the PLACES model for a direct measure (source-level text) | Fixed after the run: per-measure source text. The committed run's methods.md keeps the old wording |
| F2 | USALEEP New York City is a separate file (`NYC_A.CSV`); the registry also wrongly marked Maine and Wisconsin missing | Fixed during X4 (exploratory), before any coefficient was read |
| F3 | No valid clustering level for a two-state county study; Moran's I 0.195 | Addressed in Round 22 (see PLAN_ROUND_22.md): A2 FAILED; exploratory only |
| F4 | Leverage of five NYC counties on vehicle access | Design note for future manifests: register the transit-dense exclusion rule, or use tracts within counties |
| F5 | `run_manifest` labels an exploratory manifest's run "confirmatory" | Addressed in Round 22 (see PLAN_ROUND_22.md): exploratory flag implemented |
| F6 | Rate apportionment of split tracts failed validation | Addressed in Round 22 (see PLAN_ROUND_22.md): held-out A4 PASSED; dominant opt-in, default missing |

## 11. Review (author self-review at the owner's request, not independent)

- **Registration order:**
  - The manifest commit (16:41:51Z) precedes the first CHR&R download (16:42:29Z, sidecar).
  - The cache directory held no CHR&R data before the commit.
  - The engine fixes were committed before the manifest.
- **Numbers traced:** each hypothesis row matches `bundle/results/hypotheses.json`. Exploratory numbers come from `exploratory_summary.json` (hash above), and descriptives are recomputed in the script.
- **Rule check:** `create_manifest` on the committed manifest gives no R1 or R2 error, and the notes state that the outcome is direct. The Part 1 manifest still validates (`tests/test_round21.py`).
- **Changes after seeing data:**
  - Only F2, the USALEEP NYC file. It affects the exploratory X4 only and is documented.
  - The confirmatory analysis was not touched.
- **Claims to watch:**
  - H2's failure is reported as registered; the reversed sign is explained, not explained away.
  - X3 corrects a Part 1 claim (2× to 1.4×); the Part 1 report has an addendum.
  - The H1 and H4 interval widths rest on independence (section 8).
- **Recommendation:** an independent review before external citation. Add a spatial-HAC or regional-cluster sensitivity once the engine has it (F3).

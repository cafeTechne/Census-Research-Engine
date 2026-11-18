# Round 29: Ohio / Pennsylvania mortality and poverty

**Author self-review, not independent.** Registered confirmatory protocol; descriptive analyses are labelled separately. Completed 2026-11-18.

Both manifests were committed and pushed at `150e1727ed37dab422f46ffbc919726e3c92f9d2` before either outcome association was computed. This manifest: `r29_oh_pa_replication.json`; canonical SHA-256 `6550cc38cc874b0cec8ef7fb53ede87929345e56136ffc92da3b8d9761b2d68e`. The replication changes geography only; all other fields are identical.

## Registered analysis

County deaths pooled over 2018–2022 are the owner's manual WONDER UCD exports, pinned by SHA-256. National age × sex references are also manual exports. No WONDER network access was used. Expected deaths are five times the ACS 2018–2022 population in each matching age/sex band times the annual national rate (deaths divided by summed annual person-years). H1 uses ages under 75 and all-cause reference rates; H2 and H3 use all ages and their cause-specific rates. The youngest two WONDER groups are combined; Not Stated ages are dropped. All 62 available exports passed structural inventory; only the six registered files enter these studies.

Each Poisson model uses log(expected deaths) as offset, poverty in percentage points (B17001), and a state intercept. HC3 model variance plus 80-replicate ACS poverty variance gives the conservative SE. Offsets stay fixed in these model refits: the slope's interval excludes ACS offset and reference-rate uncertainty. Separate reference-aware county SMR combined intervals include Poisson, ACS expected-count and reference death-count variance; they do not correct the slope's omitted offset uncertainty. Reference person-years are fixed. Internal national-reference covariance is omitted, conservatively, for SMR intervals.

All 155 study county IDs matched. H1/H3 exclude no suppressed counties. H2 excludes 3 suppressed counties; their total deaths are only bounded by [3, 27]. Suppression causes no vintage-mismatch warning. County IDs and nonblocking exclusions are recorded in the run bundle.

| Hypothesis | Counties fitted | Poverty coefficient | Mortality ratio per +1 pp poverty (90% CI) | One-sided Holm p | Supported |
| :--- | ---: | ---: | :--- | ---: | :--- |
| H1: premature_all_causes | 155 | 0.035026 | 1.0356 (1.0276–1.0438) | 1.806e-13 | yes |
| H2: drug_overdose | 152 | 0.058767 | 1.0605 (1.0521–1.0691) | 2.194e-33 | yes |
| H3: heart_disease | 155 | 0.022844 | 1.0231 (1.0163–1.0300) | 1.143e-08 | yes |

Intervals are unadjusted two-sided 90% intervals. Tests are registered positive-direction tests, Holm-corrected over H1–H3 separately in each geography, at alpha 0.10. They are ecological associations and do not establish causation.

## Registered H2 suppression sensitivity

These two endpoint assignments are internal refits, not estimates of the hidden county counts and not strict bounds on the slope. H1/H3 raw p-values remain fixed while the H2 p-value is replaced and the three-test Holm family is recomputed. Only coefficients are output.

| Fit | Poverty coefficient | Holm p | Supported |
| :--- | ---: | ---: | :--- |
| complete-case | 0.058767 | 2.194e-33 | yes |
| all suppressed set to 1 (internal only) | 0.058636 | 6.438e-35 | yes |
| all suppressed set to 9 (internal only) | 0.058681 | 2.761e-34 | yes |

H2 conclusion stable in all three fits: **yes**.

## Held-out replication

OH/PA was separately registered at the same commit. The fixed rule is same coefficient sign and OH/PA Holm p < 0.10; it is not a pooled four-state analysis.

| Hypothesis | Replication holds |
| :--- | :--- |
| H1 | yes |
| H2 | yes |
| H3 | yes |

## Descriptive and exploratory results

Posterior Poisson–Gamma EB SMR maps are descriptive. Censored counties enter the [1,9] likelihood internally and are grey/masked in every published map and value file. EB intervals fix E and omit ACS, reference-rate and spatial uncertainty. Quantile classes show relative levels, not significance; breaks differ between geographies. Maps live in `descriptive/figures/eb_h{1,2,3}.{png,svg}` inside the local archive.

Population-weighted SII and RII use poverty ridits running least to most deprived. These are exploratory summaries with 80 ACS refits of ranks, population weights and O/E; observed deaths and national rates stay fixed. Their intervals exclude common reference-rate uncertainty and spatial dependence, so they are not additional confirmatory evidence.

| Outcome | SII (90% CI) | RII (90% CI) | Median rank CV |
| :--- | :--- | :--- | ---: |
| H1 | 0.616 (0.527–0.706) | 1.807 (1.655–1.974) | 6.85% |
| H2 | 1.320 (0.904–1.736) | 2.645 (1.928–3.630) | 6.83% |
| H3 | 0.408 (0.341–0.474) | 1.451 (1.364–1.544) | 6.85% |

## Limits and disclosure checks

HC3 and ACS refits assume independent counties. Spatial dependence remains unresolved; IM-8 does not support Poisson/ACS here and was not substituted. ACS covariate error can attenuate slopes; GLM measurement-error correction is unavailable. Five-year ACS populations approximate the mortality period's average population. A successful replication does not resolve these limitations or certify nominal spatial coverage. The reported sensitivity only addresses the registered endpoint assignments, not all missingness or selection mechanisms.

Census VRE parsing warned that two rows in the full national B17001 file differ from published MOEs beyond rounding (maximum 0.632); published MOEs remain official and the source is unchanged. No replicate failure, missing study county or blocking deviation occurred.

Disclosure scan passed on 15 structured county frames, including snapshots, EB tables and map values. Protected count/rate/SMR/EB fields are literal `suppressed` for censored counties. No raw exports, national reference death-count vectors, complementary death totals or county sensitivity assignments enter the archive. Only the four registered study states are included. A key scan is required again if packaging is changed.

Reproduce in a fresh checkout with the private local exports and no existing `studies_output/r29/oh_pa`: `.venv/bin/python scripts/r29_mortality.py run --case oh_pa --registration 150e1727ed37dab422f46ffbc919726e3c92f9d2`, then `describe` with the same arguments. The script refuses changed registration bytes and overwriting completed runs. `.venv/bin/python scripts/r29_mortality.py finish --registration 150e1727ed37dab422f46ffbc919726e3c92f9d2` writes both reports and the local archive; it does not publish or release.

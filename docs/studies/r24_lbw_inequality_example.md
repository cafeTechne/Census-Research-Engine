# MI/NY county low birth weight inequality (exploratory)

Author self-review, not independent. This is exploratory because Round 22 already
examined poverty and low birth weight; it is not a new confirmatory test.
Manifest: `examples/manifests/r24_mi_ny_lbw_inequality.json`, SHA-256
`8d1008320c941ab468bf6fcff5319a9d7f43ffc050eec05807d7b0b16b25ad15`.

CHR&R 2025 v037 low birth weight proportions (NCHS natality 2017–2023) were
ranked by ACS 2018–2022 county poverty percentage (B17001). Weights are live
births, not county counts. The run used existing Census/CHR/VRE caches with
network requests blocked. Of 145 MI/NY counties extracted, 144 had complete
outcome/rank/weight data; one missing CHR outcome/denominator was excluded
(GEOID `26083`), recorded in the analysis diagnostics.
Missing values were not treated as zero.

| Index | Estimate | Unadjusted 90% conservative interval |
|:---|---:|:---|
| SII (percentage points) | 1.892 | [-0.103, 3.887] |
| log RII | 0.2244 | [-0.0037, 0.4526] |
| RII (exponentiated) | 1.2516 | [0.9963, 1.5723] |
| Concentration index | 0.0371 | [-0.0020, 0.0763] |

Ridits run from least to most deprived, sharing the weighted mid-rank for ties.
Positive indices mean higher LBW among more deprived areas. **Concentration has
the reverse sign of the usual income-ranked convention.** SII is a fitted
ridit-endpoint difference, not an observed richest/poorest county contrast.
Median poverty-rank CV was **6.63%**, within the <=15% range of the fixed
simulation validation. HC3 model SEs and 80 ACS poverty replicate refits were
combined by quadrature; birth outcomes and birth denominators stayed fixed.
All three intervals include their null (0 for indices, 1 for RII). These
unadjusted intervals are not simultaneous intervals; the manifest separately
applies Holm adjustment to its three hypothesis p-values.

This is a joint MI/NY birth-weighted area gradient without state adjustment or
individual-level interpretation. It differs from the state-adjusted Round 22
regressions. Independent-area HC3 does not account for spatial dependence;
rank error can attenuate gradients, and a conservative interval does not
correct that bias. Reference-rate uncertainty is irrelevant to this example:
no SMR was fitted. No age-specific death counts were fabricated.

Reproduction: run the manifest with the existing caches and
`CENSUS_HEALTH_OFFLINE=1`; outputs are release artifacts, not committed datasets.
Outputs: `r24_study_outputs.tar.gz`, attached (after a key scan) to the release that ships this round.

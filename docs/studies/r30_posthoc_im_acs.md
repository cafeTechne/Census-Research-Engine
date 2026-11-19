# Round 30 post hoc IM/ACS re-checks

**Post hoc; author self-review, not independent. Registered manifests and outputs are unchanged.**

C1 passed linear, binomial and Poisson observed-estimate targets. C2 EIV failed and remains refused; R21b is unavailable. C1 is not measurement-error correction and does not test a general true-slope null when noisy controls are present. Eight fixed clusters, unweighted mean coefficients, between-cluster SE and t(7); no additive ACS SE. Terms constant in all clusters are absorbed by cluster intercepts and cannot be tested. Poisson offsets stay fixed.

All cached input/result SHA-256 values and registered manifest hashes were verified before fitting, with HTTP blocked. MI/NY only: OH/PA is outside the validation geometry and is not re-checked.

## R21B

| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM-8? |
| :--- | ---: | ---: | :--- |
| H1 (m1: pov_rate) | 2.61919e-18 | unavailable | not assessed |
| H2 (m2: no_vehicle) | 0.947005 | unavailable | not assessed |
| H3 (m2: cost_burden) | 0.474521 | unavailable | not assessed |
| H4 (m3: asdp) | 7.16656e-27 | unavailable | not assessed |

C2 failed; no EIV IM coefficients or p-values are invented. The original EIV fits remain the reference.

Reference-fit residual Moran I (2022 cached queen contiguity, row standardized; 999 permutations, seed 20261201):

- m1: I=0.210824, permutation p=0.0010, n=145.
- m2: I=0.195464, permutation p=0.0010, n=145.
- m3: I=0.234582, permutation p=0.0010, n=145.

Per-cluster coefficient estimates (labels 0–7; coefficients only):

- m1: unavailable (C2 IM EIV failed fixed validation; no C1 substitution).
- m2: unavailable (C2 IM EIV failed fixed validation; no C1 substitution).
- m3: unavailable (C2 IM EIV failed fixed validation; no C1 substitution).
## R22

| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM-8? |
| :--- | ---: | ---: | :--- |
| H1 (m1: pov_rate) | 2.65109e-12 | 0.0176306 | yes |
| H2 (m2: cost_burden) | 0.00498352 | 0.0575012 | yes |
| H3 (m2: no_vehicle) | 0.923584 | 0.223059 | n/a: not supported as registered; still not supported |

Registered p-values retain the original Pearson X2 inference, later found to under-cover. This table does not endorse X2. C1 tests naive ACS-estimate associations, not corrected true effects.

Reference-fit residual Moran I (2022 cached queen contiguity, row standardized; 999 permutations, seed 20261201):

- m1: I=0.175693, permutation p=0.0010, n=144.
- m2: I=0.183552, permutation p=0.0010, n=144.

Per-cluster coefficient estimates (labels 0–7; coefficients only):

- m1: terms `Intercept, pov_rate`; absorbed/not estimable `C(GEOID.str[:2])[T.36]`.

| Cluster | Intercept | pov_rate |
| ---: | ---: | ---: |
| 0 | -2.6228 | -0.00360125 |
| 1 | -2.59051 | 0.00935883 |
| 2 | -2.67701 | 0.0216692 |
| 3 | -2.70369 | 0.0127762 |
| 4 | -2.69959 | 0.0304865 |
| 5 | -2.45602 | 0.00460564 |
| 6 | -2.64107 | 0.0151468 |
| 7 | -2.53644 | 0.00904892 |

- m2: terms `Intercept, pov_rate, pct_bachelors, no_vehicle, cost_burden`; absorbed/not estimable `C(GEOID.str[:2])[T.36]`.

| Cluster | Intercept | pov_rate | pct_bachelors | no_vehicle | cost_burden |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -2.11412 | 0.0750677 | -0.0194351 | -0.111953 | -0.00954011 |
| 1 | -3.24671 | -0.0231545 | -0.0125994 | 0.0828251 | 0.0356945 |
| 2 | -3.28369 | -0.043933 | -0.00850182 | 0.0574802 | 0.0518036 |
| 3 | -2.01841 | -0.00685943 | -0.0129784 | -0.023845 | 0.00195645 |
| 4 | -2.83548 | -0.0206059 | -0.00667748 | 0.0539885 | 0.0220863 |
| 5 | -2.91798 | -0.00851227 | 0.00222456 | 0.0288789 | 0.00918136 |
| 6 | -2.84331 | -0.0200809 | -0.00320034 | 0.048251 | 0.00971003 |
| 7 | -2.16206 | -0.0210165 | -0.0106352 | 0.00583901 | 0.0061178 |

## R29

| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM-8? |
| :--- | ---: | ---: | :--- |
| H1 (h1: poverty) | 1.41005e-06 | 0.00152037 | yes |
| H2 (h2: poverty) | 0.0114821 | 0.169021 | no |
| H3 (h3: poverty) | 0.0138239 | 0.00569236 | yes |

H2 excludes its 13 suppressed counties after assignment on all 145. No county values, residual vectors or imputed counts are output. Fixed E omits its ACS and reference-rate uncertainty from slope inference.

Reference-fit residual Moran I (2022 cached queen contiguity, row standardized; 999 permutations, seed 20261201):

- h1: I=0.406546, permutation p=0.0010, n=145.
- h2: I=0.230747, permutation p=0.0030, n=132.
- h3: I=-0.013125, permutation p=0.4060, n=145.

Per-cluster coefficient estimates (labels 0–7; coefficients only):

- h1: terms `Intercept, poverty`; absorbed/not estimable `C(GEOID.str[:2])[T.36]`.

| Cluster | Intercept | poverty |
| ---: | ---: | ---: |
| 0 | -0.123017 | 0.00616441 |
| 1 | -0.248088 | 0.0210839 |
| 2 | -0.685346 | 0.0552281 |
| 3 | -0.601249 | 0.0441987 |
| 4 | -0.49929 | 0.0420615 |
| 5 | -0.33762 | 0.0208929 |
| 6 | -0.499383 | 0.0348046 |
| 7 | -0.568473 | 0.0211119 |

- h2: terms `Intercept, poverty`; absorbed/not estimable `C(GEOID.str[:2])[T.36]`.

| Cluster | Intercept | poverty |
| ---: | ---: | ---: |
| 0 | 0.863861 | -0.110709 |
| 1 | -0.270861 | 0.00642763 |
| 2 | -1.34952 | 0.0848926 |
| 3 | -0.674722 | 0.0178545 |
| 4 | -0.75884 | 0.0661789 |
| 5 | -0.566487 | 0.0465167 |
| 6 | -0.67509 | 0.0356904 |
| 7 | -0.513966 | 0.0254813 |

- h3: terms `Intercept, poverty`; absorbed/not estimable `C(GEOID.str[:2])[T.36]`.

| Cluster | Intercept | poverty |
| ---: | ---: | ---: |
| 0 | 0.150764 | -0.00784399 |
| 1 | -0.332206 | 0.0304396 |
| 2 | -0.319305 | 0.0359949 |
| 3 | -0.269688 | 0.0329878 |
| 4 | -0.0953312 | 0.0236967 |
| 5 | -0.261545 | 0.0161324 |
| 6 | -0.313169 | 0.0260319 |
| 7 | -0.0624474 | 0.00714548 |


## Interpretation and artifacts

These checks leave registered results unchanged. IM with C1 incorporates independent ACS-error variation through the cluster estimates, but does not remove attenuation or control-variable measurement-error bias. Coverage was validated only in the frozen MI/NY simulation; its passing criterion does not establish performance for arbitrary spatial covariance, county geometries or measurement-error regimes. C2 remains unavailable; spatial random effects for corrected EIV inference are the next backlog step.

Supporting coefficients, per-cluster estimates, source hashes and Moran summaries are in `r30_study_outputs.tar.gz`. The R29 part contains coefficients/diagnostics only and passes `census.wonder_outputs.audit_outputs`; no county death counts or derived values for suppressed counties, raw WONDER exports, or national reference death-count vectors are included. The archive is key-scanned locally and not published by this script.

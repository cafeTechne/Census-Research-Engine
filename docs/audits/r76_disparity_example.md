# Round 76 example: family poverty disparities by race/ethnicity (MI and NY counties, 2020-2024)

Exploratory; author self-review, not independent; no registration. Groups: White alone not Hispanic (reference), Hispanic or Latino, all other non-Hispanic families (derived on every replicate). Rates: families below poverty / families (B17010, B17010H, B17010I VRE; B17020 child poverty has no VRE file). 145 counties; 128 have every group present with a nonzero rate.

| Measure | Counties validated | Median estimate | Median 90% CI width |
| :--- | ---: | ---: | ---: |
| rd | 154 of 256 rows | 0.07033 | 0.1278 |
| log_rr | 78 of 256 rows | 0.6959 | 1.169 |
| idisp | 77 of 128 rows | 102.1 | 186.4 |
| bgv | 39 of 128 rows | 0.0007006 | 0.002773 |
| theil | 39 of 128 rows | 0.0408 | 0.1305 |
| mld | 39 of 128 rows | 0.0329 | 0.107 |

Largest counties (90% intervals; ✓ = inside the validated range):

| County | Hispanic RR vs White NH | Other NH RR | Index of Disparity | Max group CV |
| :--- | :--- | :--- | :--- | ---: |
| 26163 | 2.11 (1.89–2.36) ✓ | 2.59 (2.41–2.77) ✓ | 134.92 (119.33–152.53) ✓ | 0.06 |
| 26081 | 4.59 (3.67–5.74) ✓ | 3.26 (2.68–3.96) ✓ | 292.84 (228.59–375.14) ✓ | 0.10 |
| 26125 | 2.68 (2.11–3.40) ✓ | 1.96 (1.73–2.21) ✓ | 131.65 (101.46–170.82) ✓ | 0.15 |
| 36047 | 1.97 (1.82–2.14) ✓ | 1.49 (1.38–1.61) ✓ | 73.26 (61.69–86.99) ✓ | 0.04 |
| 36005 | 3.07 (2.59–3.63) ✓ | 2.20 (1.85–2.62) ✓ | 163.36 (124.78–213.87) ✓ | 0.10 |
| 36081 | 2.01 (1.83–2.20) ✓ | 1.91 (1.75–2.08) ✓ | 95.95 (81.46–113.01) ✓ | 0.04 |
| 36055 | 5.50 (4.63–6.52) ✓ | 4.74 (4.18–5.39) ✓ | 412.00 (351.76–482.55) ✓ | 0.08 |

## Kitagawa: person poverty rate, Wayne (26163) minus Oakland (26125), eight age strata (B17001)

| Component | Estimate (percentage points) | 90% CI | Validated |
| :--- | ---: | :--- | :--- |
| crude_difference | 13.07 | 12.47 to 13.66 | yes |
| rate_effect | 12.79 | 12.20 to 13.38 | yes |
| composition_effect | 0.28 | 0.25 to 0.30 | yes |

Largest stratum-rate CV: 0.063.

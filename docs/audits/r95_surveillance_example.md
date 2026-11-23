# Round 95 example: national YPLL-75 by cause and state uninsured aberration flags (exploratory)

Author self-review, not independent; not a registered study.

## Age-adjusted YPLL-75 per 100,000 person-years, United States

National WONDER manual exports (Underlying Cause of Death), ten-year age groups below 75, 2000 US standard; 90% Fay-Feuer intervals (validated).

| Cause | 2013-2017 | 2018-2022 | Change |
| :--- | ---: | ---: | ---: |
| all causes | 6,623 (6,617-6,630) | 7,581 (7,574-7,588) | +14% |
| heart disease | 923 (921-925) | 963 (961-965) | +4% |
| cancer | 1,237 (1,235-1,239) | 1,119 (1,117-1,121) | -10% |
| unintentional injury | 1,190 (1,186-1,193) | 1,579 (1,576-1,583) | +33% |
| drug overdose | 605 (603-607) | 945 (942-947) | +56% |
| suicide | 423 (421-425) | 458 (456-460) | +8% |
| firearm | 394 (392-395) | 490 (488-492) | +24% |
| liver disease | bounds 180.5-180.7* | bounds 231.5-231.8* | +28% |
| diabetes | bounds 169.7-169.7* | bounds 204.8-205.0* | +21% |
| stroke | 156 (155-157) | 167 (167-168) | +7% |
| clrd | 167 (167-168) | 155 (154-156) | -7% |
| kidney disease | 66 (65-66) | 74 (74-75) | +13% |
| alcohol induced | bounds 196.7-196.9* | bounds 278.8-278.9* | +42% |

\* Some national age-by-sex cells are suppressed (1-9 deaths): bounds with each suppressed cell at 1 and at 9; the change uses the bound midpoints.

## Historical-limits flags, 2023 state uninsured rates

ACS 1-year percent uninsured, 50 states and DC; baseline 2017, 2018, 2019, 2021, 2022 (2020 has no standard release). Flags: high 0, low 10, none 41. Rates fell broadly through 2022 (a trend), so 'low' flags partly reflect the trend, which the method does not model. Chart: `docs/audits/r95_deviation_chart.png` (FIPS codes).

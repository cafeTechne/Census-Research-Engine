# Round 101 example: US life expectancy change and Michigan age-data quality (exploratory)

Author self-review, not independent; not a registered study.

## Life expectancy at birth, United States (owner's national WONDER exports)

e0 2013-2017: 79.09 years; 2018-2022: 77.85 years; change -1.23 years (Chiang II 90% intervals are about +/-0.01 at national scale).

Arriaga decomposition by age band (years of e0):

| Age | Contribution |
| :--- | ---: |
| <1 | +0.026 |
| 1-4 | +0.001 |
| 5-14 | -0.006 |
| 15-24 | -0.051 |
| 25-34 | -0.161 |
| 35-44 | -0.212 |
| 45-54 | -0.131 |
| 55-64 | -0.221 |
| 65-74 | -0.198 |
| 75-84 | -0.090 |
| 85+ | -0.191 |

By underlying cause (mutually exclusive ICD-10 chapters on file; 'other' is the remainder):

| Cause | Contribution |
| :--- | ---: |
| other | -1.031 |
| unintentional injury | -0.322 |
| liver disease | -0.049 |
| diabetes | -0.047 |
| stroke | -0.030 |
| suicide | -0.026 |
| heart disease | -0.019 |
| kidney disease | -0.003 |
| clrd | +0.067 |
| cancer | +0.225 |

'Other' includes COVID-19 (U07.1, 2020-2022), which has no export of its own here and accounts for most of it. Notes: Arriaga (1984) decomposition; causes may overlap if the listed causes are not mutually exclusive (then 'other' is not a remainder). 16 suppressed national cause-by-age cells (1-9 deaths) counted as 0 (each changes a band's rate by under 10 deaths).

## Age-data quality, Michigan

| Source | Whipple | Myers | UN age-sex accuracy |
| :--- | ---: | ---: | ---: |
| 2020 Census (DHC PCT12) | 103.9 | 1.03 | 8.5 |
| PUMS 2019-2023 (weighted; SE) | 99.4 (0.5) | 0.56 (0.09) | 11.0 (1.5) |

Whipple near 100 and Myers near 0 mean no detectable age heaping; the UN index mixes real cohort-size variation (baby boom, migration) with error, so values above 20 do not by themselves indicate bad data in a population with uneven birth cohorts.

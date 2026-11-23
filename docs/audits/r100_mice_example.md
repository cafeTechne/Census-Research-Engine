# Round 100 example: Michigan tract median income with withheld values (exploratory)

Author self-review, not independent; not a registered study. ACS 2019-2023, 2915 populated Michigan tracts; missing values: log income 45, poverty 14, bachelor's 0.

| Term | FCS (PMM) estimate | 90% CI | FMI | Complete cases |
| :--- | ---: | :--- | ---: | ---: |
| Intercept | 11.1626 | 11.1441 to 11.1810 | 0.15 | 11.1764 |
| pov | -0.0225 | -0.0232 to -0.0219 | 0.30 | -0.0232 |
| ba | 0.0094 | 0.0091 to 0.0098 | 0.08 | 0.0093 |

Delta sensitivity (missing incomes assumed lower by the stated factor):

| Missing incomes | Poverty coefficient | Bachelor's coefficient |
| :--- | ---: | ---: |
| x 0.8 | -0.0230 | 0.0094 |
| x 0.9 | -0.0227 | 0.0094 |
| x 1.0 | -0.0225 | 0.0094 |

Withheld medians cluster in small or unusual tracts, so missing-at-random is doubtful; the delta rows show how far conclusions move if those incomes are systematically lower.

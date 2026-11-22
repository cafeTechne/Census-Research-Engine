# Round 79 example: Michigan uninsured gap, Black vs White non-Hispanic adults 19-64 (PUMS 2019-2023)

Exploratory; author self-review, not independent. 'Explained' is composition (age, income-to-poverty, employment, education), not a causal effect. Percentage points; 90% SDR intervals.

## Fairlie (logit)

Records: Black 20988, White 218685.

| Component | Estimate | 90% CI | Validated |
| :--- | ---: | :--- | :--- |
| gap | 2.54 | 2.08 to 3.00 | no |
| explained | 2.73 | 2.59 to 2.88 | yes |
| unexplained | -0.19 | -0.72 to 0.33 | yes |
| explained:AGEP | 0.17 | 0.15 to 0.20 | yes |
| explained:POVPIP | 1.47 | 1.34 to 1.59 | yes |
| explained:ESR | 0.36 | 0.26 to 0.46 | yes |
| explained:SCHL | 0.73 | 0.66 to 0.80 | yes |

## Oaxaca-Blinder (linear probability)

Records: Black 20988, White 218685.

| Component | Estimate | 90% CI | Validated |
| :--- | ---: | :--- | :--- |
| gap | 2.54 | 2.08 to 3.00 | no |
| explained | 2.59 | 2.47 to 2.70 | yes |
| unexplained | -0.05 | -0.53 to 0.44 | yes |
| explained:AGEP | 0.16 | 0.14 to 0.18 | yes |
| explained:POVPIP | 1.42 | 1.32 to 1.51 | yes |
| explained:ESR | 0.26 | 0.19 to 0.33 | yes |
| explained:SCHL | 0.74 | 0.67 to 0.82 | yes |
| unexplained:AGEP | -3.01 | -4.33 to -1.69 | yes |
| unexplained:POVPIP | 2.27 | 1.44 to 3.10 | yes |
| unexplained:ESR | 0.81 | -0.06 to 1.68 | yes |
| unexplained:SCHL | 2.25 | 0.94 to 3.56 | yes |
| unexplained:intercept | -2.36 | -4.53 to -0.20 | yes |

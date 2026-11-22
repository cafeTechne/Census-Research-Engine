# Round 78 example: Medicaid expansion and the state uninsured rate (ACS 1-year, 2010-2023 without 2020)

Exploratory; author self-review, not independent; not a registered replication. Percent uninsured (S2701), 51 units, cohorts {'2014': 26, '2015': 3, '2016': 2, '2017': 1, '2019': 2, '2021': 3, '2022': 2}, 12 never treated within the panel. Event times count observed periods (2020 is skipped).

| Method | Overall ATT (points) | 90% CI | Validated |
| :--- | ---: | :--- | :--- |
| Sun-Abraham | -1.23 | -2.18 to -0.27 | yes |
| Callaway-Sant'Anna + ACS variance | -1.23 | -2.10 to -0.36 | yes |

Sun-Abraham event study (event time 0 = first treated year):

| Event time | Estimate | 90% CI |
| ---: | ---: | :--- |
| -5 | 0.17 | -0.26 to 0.60 |
| -4 | -0.08 | -0.36 to 0.20 |
| -3 | -0.19 | -0.45 to 0.08 |
| -2 | -0.13 | -0.39 to 0.14 |
| 0 | -0.92 | -1.40 to -0.45 |
| 1 | -1.23 | -2.03 to -0.43 |
| 2 | -1.20 | -2.11 to -0.30 |
| 3 | -1.56 | -2.54 to -0.57 |
| 4 | -1.60 | -2.58 to -0.61 |
| 5 | -1.63 | -2.68 to -0.58 |
| 6 | -1.37 | -2.55 to -0.18 |

Pre-trend check (smallest Holm-adjusted p over pre-treatment event times): 0.979.
The literature's 3-5 point reductions concern low-income adults; this all-ages rate dilutes them (most residents were not in the expansion population), so a smaller all-ages effect is expected. Descriptive comparison only.

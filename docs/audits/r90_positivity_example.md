# Round 90 example: positivity diagnostics, metro status and county uninsured rates (exploratory)

Author self-review, not independent; not a registered study. ACS 2019-2023, MI/NY/OH/PA counties (n = 300, 139 metro). Outcome: percent uninsured (S2701); treatment: ERS 2013 metro status; confounders: percent below poverty (S1701) and percent aged 65+ (DP05). There is no target trial here (metro status is not an intervention), so every estimate is associational.

**Positivity:** 7.3% of propensities lie outside [.05, .95]; overlap coefficient 0.61; propensity median 0.60 (metro) and 0.35 (non-metro); effective n 113 of 139 (metro) and 108 of 161 (non-metro); limited overlap: yes.

| Estimator | Estimand | Estimate (points) | 90% CI | Validated |
| :--- | :--- | ---: | :--- | :--- |
| Plain IPW | average treatment effect | -2.69 | -5.23 to -0.15 | no |
| AIPW | average treatment effect | -2.68 | -5.25 to -0.12 | yes |
| g-formula (regression adjustment) | average treatment effect | -1.47 | -2.39 to -0.55 | yes |
| Stabilized weights | average treatment effect | -2.69 | -5.24 to -0.15 | no |
| Truncated weights | average treatment effect | -1.63 | -2.77 to -0.48 | yes |
| Overlap weights | overlap-population effect | -1.66 | -2.75 to -0.57 | yes |

IPW versus g-formula: difference -1.22, threshold 2.11, not flagged.

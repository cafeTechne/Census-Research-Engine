# Round 91 example: Medicaid expansion, uninsured rate and time-varying unemployment (exploratory)

Author self-review, not independent; not a registered study. ACS 1-year, 50 states and DC, 2010-2023 without 2020 (51 units, 39 expanded within the panel). Outcome: percent uninsured (S2701); time-varying confounder: unemployment rate (DP03). Time zero 2010; strategy 'expand and stay expanded'. Effects are percentage points for the first, second and third expanded year versus never expanded.

| Year of expansion | MSM, stabilized weights (90% CI) | MSM, truncated weights (90% CI) | Regression on current unemployment |
| ---: | :--- | :--- | ---: |
| 1 | -2.70 (-3.74 to -1.92) | -2.71 (-3.74 to -1.93) | -3.00 |
| 2 | -3.24 (-4.26 to -2.45) | -3.25 (-4.29 to -2.45) | -3.52 |
| 3 | -3.61 (-4.73 to -2.70) | -3.61 (-4.73 to -2.70) | -3.88 |

Largest stabilized weight 1.32. Validation status: stabilized exploratory, truncated exploratory (`docs/audits/msm_validation.md`). Unemployment is the only time-varying confounder modelled; the no-unmeasured-confounding assumption is strong for state policy. The Round 78 staggered DiD on the same panel adjusted for nothing time-varying.

# Pre-Registered Study (Round 126): US National Life Expectancy (Chiang II), Arriaga Sex-Gap Decomposition & Cause-Specific YPLL-75 (WONDER 2018–2022)

**Date:** 2026-11-26  
**Protocol SHA-256:** `9bc7ba4b7e6f30afdf98923e43767bb7b0a3f164b620201b123e666f359726b8`  
**Script:** `scripts/r126_demography_ypll_study.py`  
**Data:** Owner manual CDC WONDER UCD 2018–2022 national age × sex exports (`external_data/wonder/ucd/2018-2022/national_age_sex/`; national aggregates only, zero suppressed counts).  
**Review status:** Author self-review, not independent.

## 1. Chiang II Abridged Life Tables (90% Intervals, Validated)

| Population | $e_0$ (years) | 90% CI | $e_{65}$ (years) | 90% CI |
| :--- | ---: | :--- | ---: | :--- |
| Total U.S. (2018–2022) | `77.851` | `77.845–77.857` | `19.299` | `19.294–19.303` |
| Female | `80.602` | `80.593–80.610` | `20.551` | `20.545–20.557` |
| Male | `75.155` | `75.146–75.164` | `17.903` | `17.896–17.909` |

## 2. Arriaga Decomposition of Female-Minus-Male $e_0$ Gap (`+5.446` Years)
- **Exact additivity:** $\sum_x \Delta_x = 5.446303$ years vs. $e_{0,F} - e_{0,M} = 5.446303$ years (error `1.78e-15`).
- Largest age-band contributions: **55–64 (`+1.005` yrs)**, **65–74 (`+1.001` yrs)**, **75–84 (`+0.736` yrs)**, **45–54 (`+0.682` yrs)**, and **15–44 combined (`+1.578` yrs)**.

## 3. Age-Adjusted YPLL-75 by Cause (Fay–Feuer 90% Intervals, Validated)

| Cause (2018–2022) | Age-Adjusted YPLL-75 / 100k | 90% CI | Crude YPLL-75 / 100k |
| :--- | ---: | :--- | ---: |
| All causes | `7,580.9` | `7,573.9–7,587.9` | `8,040.2` |
| Cancer | `1,118.6` | `1,116.5–1,120.7` | `1,330.9` |
| Heart disease | `963.4` | `961.4–965.4` | `1,114.1` |
| Drug overdose | `944.7` | `942.1–947.4` | `899.9` |

## 4. Author Self-Review (Not Independent)
- Drug overdose nearly rivals heart disease in premature years of life lost before age 75 (`944.7` vs. `963.4` per 100k), reflecting younger age at death.
- Limitations: 5-year pooled 2018–2022 period spans pre-pandemic and pandemic years (2020–2022); grouped 10-year age bands use standard midpoint assumptions.

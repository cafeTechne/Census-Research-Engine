# Pre-Registered Study (Round 121): Age-65 Medicare Eligibility Discontinuity and Disability Stratification (ACS 2019–2023 PUMS)

**Date:** 2026-11-26  
**Protocol SHA-256:** `b89f68705cef412dbafd208f0690f0b2e851261900cf143ee787bb7e837fc0c9`  
**Script:** `scripts/r121_medicare_rdd_study.py`  
**Data:** Cached ACS 2019–2023 5-Year Person PUMS with 80 SDR replicate weights (`MI`: $N = 155{,}415$ records aged 55–75; held-out replication `OH`: $N = 169{,}801$ records aged 55–75).  
**Review status:** Author self-review, not independent.

## 1. Confirmatory Results (Holm-Adjusted $\alpha = 0.10$, 90% Intervals)

| Hypothesis | Method | Michigan (`26`, $N = 155{,}415$) | Ohio (`39`, $N = 169{,}801$) | Replication |
| :--- | :--- | :--- | :--- | :--- |
| **H1** Uninsurance jump at age 65 | Discrete RDD (SDR) | `-3.15` pp (`-5.38` to `-0.91`), Holm $p = 0.0104$ | `-5.15` pp (`-7.55` to `-2.76`), Holm $p = 0.0004$ | **Replicated** |
| **H2** Public coverage jump at age 65 | Discrete RDD (SDR) | `+50.54` pp (`+45.19` to `+55.89`), Holm $p = 3.26\times 10^{-54}$ | `+49.27` pp (`+45.15` to `+53.40`), Holm $p = 1.14\times 10^{-85}$ | **Replicated** |
| **H3** Disability $\times$ uninsurance (55–64 vs 65–75) | PUMS MH RR + Hotelling $F$ | `RR = 0.811` (`0.739–0.890`), Holm $p = 0.0004$; Hotelling $F = 0.306$ ($p = 0.582$) | `RR = 0.879` (`0.810–0.955`), Holm $p = 0.0099$; Hotelling $F = 0.474$ ($p = 0.493$) | **Replicated** |
| **H4** Sensitivity (age 65 vs 64 uninsurance) | VanderWeele–Ding E-value | `4.31% -> 0.79%`, `RR = 0.182`, `E-value = 10.45` | `6.31% -> 1.27%`, `RR = 0.201`, `E-value = 9.40` | **Replicated** |

## 2. Engine Bug Caught & Fixed
- **Large-sample discrete RDD pilot bandwidth (`census/rdd.py`):** On $N = 155{,}415$ integer ages, `ik_bandwidth` computed a pilot bandwidth $h_1 < 1.0$, leaving zero integer observations in $[65 - h_1, 65)$ and raising `ValueError`. Fixed `census/rdd.py` to fall back to the validated discrete floor (`h = 4.0`) whenever both sides have $\ge 5$ observations, without altering frozen `census/rdd_core.py`. Regression test in `tests/test_round121.py`.

## 3. Author Self-Review (Not Independent)
- All validated procedures (`discrete_replicate` RDD, PUMS MH RR/RD, Round 107 Korn–Graubard Hotelling $F$ homogeneity, and E-values) replicated in direction, magnitude, and significance across Michigan and Ohio.
- Limitations: Cross-sectional 5-year PUMS window (2019–2023); integer age running variable has finite support near 65; disability–uninsurance association (`H3`) reflects Medicaid/SSDI public coverage eligibility among adults with disabilities and is non-causal.

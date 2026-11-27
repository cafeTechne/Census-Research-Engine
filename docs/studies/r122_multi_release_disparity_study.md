# Pre-Registered Study (Round 122): Multi-Release County Poverty Disparity, Rural–Urban DiD, and 4-State Pooling (ACS 2015–2019 vs. 2020–2024)

**Date:** 2026-11-26  
**Protocol SHA-256:** `04428093f57fa3ac643a76e02e0305ed8fbe26cf4bd78f227389e1ff4ae4bb5f`  
**Script:** `scripts/r122_disparity_did_study.py`  
**Data:** Cached non-overlapping ACS 2015–2019 and 2020–2024 5-Year `B17001` VRE replicates + USDA ERS Rural–Urban typology (`MI/NY`: $N = 145$ counties; held-out replication `OH/PA`: $N = 155$ counties).  
**Review status:** Author self-review, not independent.

## 1. Confirmatory Results (Holm-Adjusted $\alpha = 0.10$, 90% Intervals)

| Hypothesis | Method | MI/NY ($N = 145$) | OH/PA ($N = 155$) |
| :--- | :--- | :--- | :--- |
| **H1** Nonmetro minus metro poverty (2020–2024) | Weighted RD (VRE SE) | `-0.10` pp (`-0.32` to `+0.11`), Holm $p = 0.787$ (**not supported**) | `+0.79` pp (`+0.56` to `+1.02`), Holm $p = 2.22\times 10^{-8}$ (**supported**) |
| **H2** Change in nonmetro–metro gap (2019 → 2024) | Independent-release contrast | `-0.68` pp (`-0.98` to `-0.39`), Holm $p = 0.0004$ (**supported**) | `+0.03` pp (`-0.27` to `+0.34`), Holm $p = 0.854$ (**not supported**) |
| **H3** Nonmetro vs. metro trajectory | Two-group DiD (`se="poverty_se"`) | `-0.71` pp (`-1.13` to `-0.29`), Holm $p = 0.0109$ (**supported**) | `-0.37` pp (`-0.73` to `-0.004`), Holm $p = 0.193$ (**not supported** after Holm) |
| **H4** 4-state pooled DiD (MI, NY, OH, PA) | HKSJ meta-analysis (`validated=True`) | **`-0.44` pp** (90% CI `-0.72` to `-0.15`, $\tau^2 = 0.0$; MI `-0.17`, NY `-0.78`, OH `-0.39`, PA `-0.43`) | — |

## 2. Author Self-Review (Not Independent)
- All four states showed the same negative DiD direction (faster county-level poverty decline in nonmetro vs. metro counties from 2015–2019 to 2020–2024), pooling to `-0.44` pp (`90% CI: -0.72` to `-0.15`, $\tau^2 = 0.0$).
- In MI/NY, population-weighted nonmetro poverty converged to metro poverty (`13.64%` vs `13.75%`), whereas in OH/PA a `+0.79` pp population-weighted nonmetro disadvantage persisted (`13.13%` vs `12.34%`).
- Limitations: Ecologic county-level analysis; two-period DiD does not test pre-trends; `k = 4` prediction intervals remain exploratory (validated from $k \ge 10$).

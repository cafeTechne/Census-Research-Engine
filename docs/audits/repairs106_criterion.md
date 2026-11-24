# Round 106 validation criterion: third wave of exploratory-measure repairs

Pre-specified pass criteria for `scripts/repairs106_validation.py` operating on `census/repairs106_core.py`.
Nominal interval level is 90%; pass threshold is **coverage ≥ 0.86** in every cell (`H2c` nominal-.10 size ≤ 0.13).

1. **PUMS replicate Wald homogeneity (`H2c`, 1,000 draws per cell):**
   - Separate exact null DGP for each measure (`rr` constant RR = 1.5; `or` constant OR = 1.8; `rd` constant
     RD = 0.10), `K ∈ {3, 5}`, `n_per_stratum ∈ {300, 1000}`, unequal weights (CV ~ 1) + 80 SDR replicates;
     Hotelling `F(K - 1, 80 - K + 1)` rejection size ≤ 0.13 in every cell.
2. **Designation PPV predictive interval (`Q2c`, 400 draws per cell):**
   - `N ∈ {200, 1000}`, `A ∈ {0.005, 0.02}`, rules `"point"` and `"prob80"`; FH parametric bootstrap with
     rule re-selection `S_b` coverage ≥ 0.86 in every cell.
3. **Ecologic / between-area slope (`E3`, 1,000 draws per cell):**
   - `J = 150` areas, `n_j ∈ {20, 40}` individuals per area, reliability ~ 0.65–0.85; Croon/Fuller
     reliability-corrected slope with delete-one-area jackknife `t(J - 2)` coverage ≥ 0.86 in every cell.
4. **Lin's CCC (`C2`, 2,000 draws per cell):**
   - `n ∈ {50, 145}`, true `CCC ∈ {0.5, 0.8, 0.95}`, with mean shift and scale difference; delete-one-area
     jackknife on Fisher-z(CCC) with `t(n - 2)` coverage ≥ 0.86 in every cell.
5. **Parametric g-formula for annual policy panels (`M5`, 1,000 draws per cell):**
   - Exact Round 91/104/105 cells (`K ∈ {12, 18}`, `Feedback ∈ {0.0, 0.5, 1.0}`, `ψ ∈ {0.0, -2.0}`, 51 units);
     parametric g-formula with delete-one-unit cluster jackknife `t(G - 1)` coverage ≥ 0.86 across all 3
     durations in all 12 cells.

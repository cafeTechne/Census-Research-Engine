# Round 105 validation criterion: second wave of exploratory-measure repairs

Pre-specified pass criteria for `scripts/repairs105_validation.py` operating on `census/repairs105_core.py`.
Nominal interval level is 90%; pass threshold is **coverage ≥ 0.86** in every cell (and **nominal-.10 size ≤ 0.13**
for `H2b`). Candidates that fail remain exploratory; no post-hoc retuning.

1. **Continuous RDD (`R1b`, 1,000 draws per cell):**
   - `n ∈ {2000, 10000}`, curvature `c2 ∈ {0.0, 2.0}`, cubic `c3 ∈ {0.0, 3.0}` (strong curvature where `h_ik`
     covered `.78–.80`); `R1b` CER bandwidth `h_cer = h_ik * n^(-1/20)` robust interval coverage ≥ 0.86 in every cell.
2. **PUMS replicate Wald homogeneity (`H2b`, 1,000 draws per cell):**
   - `K ∈ {3, 5}` strata, `n_per_stratum ∈ {300, 1000}`, unequal weights (CV ~ 1) with 80 SDR replicates, common
     true RR = 1.5 across strata; `H2b` Hotelling `F(K - 1, 80 - K + 1)` nominal-.10 rejection size ≤ 0.13 for
     `rr`, `or`, `rd` in every cell.
3. **Designation PPV predictive interval (`Q2b`, 400 draws per cell):**
   - `N ∈ {200, 1000}` areas with realistic ACS tract-like effective sample sizes (`n_eff ~ Uniform(40, 200)`),
     Fay–Herriot `A ∈ {0.005, 0.02}`, threshold `t = 0.20`, rules `"point"` and `"prob80"`; `Q2b` parametric
     bootstrap PPV predictive interval coverage ≥ 0.86 in every cell.
4. **Probabilistic misclassification (`M1b`, 1,000 draws per cell):**
   - `N = 2000`, true RR ∈ `{1.0, 1.5}`, `kind ∈ {"outcome", "exposure"}`, nondifferential (`Se ~ Beta(0.85, 0.04)`,
     `Sp ~ Beta(0.92, 0.03)`) and differential outcome misclassification; `M1b` propagated-sampling interval
     coverage ≥ 0.86 in every cell (RR and OR).
5. **IP-weighted MSM (`M4`, 500 draws per cell):**
   - Exact Round 91/104 cells (`K ∈ {12, 18}`, `Feedback ∈ {0.0, 0.5, 1.0}`, `ψ ∈ {0.0, -2.0}`, 51 units); `M4`
     Firth-logit + baseline-`L0` + cluster jackknife coverage ≥ 0.86 across all 3 durations in all 12 cells.

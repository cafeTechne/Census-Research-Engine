# Round 40 beta and median regression: pre-set criterion

Frozen with `scripts/beta_median_validation.py`, `census/beta_median_core.py` and the reference targets
(`docs/audits/beta_median_targets.json`) before the full run.

- 145 independent areas. Covariate x ~ N(0, 1) observed with error at reliability 0.9 or 0.7
  (lognormal per-area SEs). Beta: μ = expit(−1.5 + 0.4x), y ~ Beta(30μ, 30(1 − μ)), observed with
  error SE = c·√(μ(1 − μ)) (scaled lognormal pattern), c ∈ {0.02, 0.05}, clipped to [0.001, 0.999].
  Median: y = 1 + 0.5x + centred lognormal noise (σ 0.8), observed with error at reliability 0.9.
  Replicates from `census.simulation.make_replicates`.
- B1 beta ML with model SEs; B2 with HC0 sandwich; B3 = B2 plus the 80-refit replicate variance.
  Q1 median regression with statsmodels' kernel SE; Q2 = Q1 plus the replicate variance.
- Targets: the slope on the observed covariate in a 400,000-area reference per cell.
- Cells: beta 4 (reliability × c), median 2 (reliability); 1,000 draws; seed 20270218 + cell.
- **Acceptance:** 90% coverage ≥ .86 in every cell of the family; failures count as non-coverage.
  Selection: the first passing of B1, B2, B3 and of Q1, Q2.

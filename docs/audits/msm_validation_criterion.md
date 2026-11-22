# Round 91 IP-weighted marginal structural models: pre-set criterion

Frozen with `scripts/msm_validation.py` and `census/msm_core.py` before the full run (tag `criterion-r91`). Author
self-review, not independent.

## Design

The structure is Hernán and Robins, Figure 20.3: treatment-confounder feedback.

- **Units and years.** 51 units (states); K ∈ {12, 18} annual periods. Time zero is year 1, when no unit is treated.
- **Confounder.** L₁ ~ N(0, 1), then L_t = 0.6·L_{t−1} + γ·A_{t−1} + N(0, 1). The feedback strength
  γ ∈ {0, 0.5, 1} is how much past treatment raises the confounder.
- **Treatment ("start and stay on").** For t ≥ 2, an untreated unit starts with probability
  expit(−2.75 + 0.8·L_t); once treated, it stays treated.
- **Outcome.** Y_t = 10 + 0.2t + ψ·A_t + L_t + u + e_t + s_t, with:
  - unit effect u ~ N(0, 1);
  - AR(1) error e_t (coefficient 0.5, innovation SD 1);
  - ACS-like sampling error s_t ~ N(0, 0.5²).

  The direct effect ψ ∈ {0, −2}.
- **Targets.** The effect of being in the d-th treated year versus never treated:
  - ψ₁ = ψ;
  - ψ₂ = ψ + γ;
  - ψ₃ = ψ + γ(1 + 0.6).

  These are exact under the model: L rises by γ·Σ 0.6^k after treatment starts.
- **Cells and draws.** 12 cells (K × γ × ψ); 1,000 draws per cell; seed [20282911, cell, draw]. Bootstrap B = 200
  units resampled (seed [20282912, cell, draw]).

## Estimators

All have 90% percentile cluster-bootstrap intervals that re-estimate the weights in each resample.

| Label | Estimator |
| :--- | :--- |
| M1 | MSM: weighted least squares of Y on year effects and saturated duration indicators, with stabilized IP weights (pooled logistic numerator year, denominator year + L_t) |
| M2 | M1 with weights truncated at the 1st and 99th percentiles |
| N1 | Unweighted regression adjusting for current L_t (comparison) |
| N0 | Unweighted, unadjusted regression (comparison) |

Failures (no unit-year at a reported duration, or a non-converging model) count as non-coverage.

## Acceptance

- M1 passes if 90% coverage of ψ₁, ψ₂ and ψ₃ is ≥ .86 in every cell.
- M2 passes on the same rule.
- N1 and N0 are reported only: their bias and coverage show the feedback problem.
- A failing family stays exploratory.

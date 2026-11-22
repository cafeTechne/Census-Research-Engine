# Round 90 positivity, weights and g-formula: pre-set criterion

Frozen with `scripts/positivity_validation.py` and `census/positivity_core.py` before the full run (tag
`criterion-r90`). Author self-review, not independent.

## Design

- **Areas and confounders.** N ∈ {145, 600} independent areas (145 = MI + NY counties; 600 a tract-scale sample).
  Confounders Z₁, Z₂ ~ N(0, 1) with correlation 0.3 (Round 41).
- **Propensity.** s = (Z₁ − Z₂)/√1.4 and P(T = 1 | Z) = expit(a·s), with a ∈ {0.5, 1.502, 2.045}. That gives about
  0%, 5% and 15% of areas with propensity outside [.05, .95], since 2Φ(−2.944/a) = .05 and .15.
- **Outcome.** y = 1 + τ(Z)·T + 0.5Z₁ + 0.5Z₂ + N(0, 1). τ is 0.5 (constant) or 0.5 + 0.5Z₁ (heterogeneous). The
  ATE is 0.5. The overlap-population effect is E[e(1−e)τ]/E[e(1−e)], from 2,000,000 Monte Carlo draws (seed
  20282990).
- **Cells and draws.** 12 cells (N × a × τ); 2,000 draws per cell; seed [20282991, cell, draw].

## Estimators

All have 90% Wald intervals with a stacked sandwich SE that accounts for the estimated propensity.

| Label | Estimator | Target |
| :--- | :--- | :--- |
| W1 | Stabilized IP weights | ATE |
| W2 | Stabilized weights truncated at the 1st/99th percentiles | ATE |
| W3 | Overlap weights | Overlap-population effect |
| G1 | g-formula: arm-specific linear outcome models | ATE |
| P0 | Plain IPW (statsmodels `TreatmentEffect.ipw`, as in Round 41) | ATE; reported only |

- **Flag:** |W1 − G1| > SE(W1) + SE(G1).
- **Failures** (non-convergence or a propensity of 0 or 1) count as non-coverage and, for the flag, as flagged.

## Acceptance

- Each of W1, W2, W3 and G1 passes if its coverage is ≥ .86 in every cell.
- The flag passes if its rate is ≤ .10 in every cell. All models are correctly specified, so this is its size.
- A family that fails stays exploratory. W2 is expected to be biased for the ATE when effects are heterogeneous and
  overlap is limited (truncation changes the estimand), so a failure there is informative.

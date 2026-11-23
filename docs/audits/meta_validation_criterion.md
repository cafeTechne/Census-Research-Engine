# Round 102 meta-analysis completeness: pre-set criterion

Frozen with `scripts/meta_validation.py`, `census/meta_core.py` and `census/evidence_core.py` before the full run (tag
`criterion-r102`). Author self-review, not independent.

## Pooling design

- **Estimates:** k ∈ {4, 5, 10, 20, 40}. Within-study SEs are 0.1·10^U with U ~ U(0, 1), fixed per cell (seed
  [20283021, cell]), so they vary up to tenfold.
- **Heterogeneity:** I² ∈ {0, .25, .5, .75}, with τ² = I²/(1 − I²)·v_typ (Higgins and Thompson's typical within
  variance).
- **Effects:** θ_i ~ N(0.3, τ²); y_i ~ N(θ_i, v_i). A new study's θ_new ~ N(0.3, τ²).
- **Cells and draws:** 20 cells; 4,000 draws each; seed [20283022, cell, draw].

| Label | Estimator | Target |
| :--- | :--- | :--- |
| P1-PM | Prediction interval, Paule–Mandel τ² | θ_new |
| P1-REML | Prediction interval, REML τ² | θ_new |
| H1 | Q-profile 90% interval | τ² |
| E1 | Egger test at .10 (no small-study effect, so its rejection rate is its size) | — |

The Hartung–Knapp mean is reported.

## Meta-regression design

- **Model:** θ_i = 0.3 + β·x_i + u_i, with x_i ~ N(0, 1) and u_i ~ N(0, τ²).
- **Parameters:** k ∈ {10, 20, 40}, I² ∈ {0, .5} and β ∈ {0, 0.2}, so 12 cells; 1,000 draws each; seed
  [20283023, cell, draw].
- **R1:** Knapp–Hartung 90% interval for β, and a permutation p-value from 199 permutations.

## Acceptance

| Estimator | Pass rule |
| :--- | :--- |
| P1-PM, P1-REML | Coverage ≥ .86 in every cell with k ≥ 10. A failure only below 10 is a gate (validated from 10). |
| H1 | Coverage ≥ .86 in every cell |
| R1 | β coverage ≥ .86 in every cell, and the permutation p-value's rejection rate at .10 is ≤ .10 in every β = 0 cell |
| E1 | Rejection rate ≤ .10 in every cell with k ≥ 10 |

Failing methods stay exploratory.

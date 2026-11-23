# Round 99 matching estimators and triple differences: pre-set criterion

Frozen with `scripts/matching_validation.py`, `census/matching_core.py`, `census/positivity_core.py` and
`scripts/positivity_validation.py` before the full run (tag `criterion-r99`). Author self-review, not independent.

## Matching

- **Design:** the Round 90 design (`positivity_validation.draw`): two confounders, logistic propensity strength
  a ∈ {0.5, 1.502} (good and limited overlap), and an effect that is constant (0.5) or heterogeneous (0.5 + 0.5Z₁).
- **Cells and draws:** N ∈ {145, 600}, so 8 cells; 2,000 draws each; seed [20282991, cell, draw].
- **Targets:**
  - ATT: the mean of τ(Z) over treated units in the draw (sample ATT);
  - ATE: 0.5 (population);
  - for M2, the mean of τ(Z) over the matched treated units in the draw.

| Estimator | Specification |
| :--- | :--- |
| M1-ATT, M1-ATE | Nearest-neighbour matching with 4 matches, bias correction and Abadie–Imbens variance |
| M2 | Coarsened exact matching at covariate quintiles; HC1 interval |
| M3 | Propensity-score caliper matching with a bootstrap percentile interval |

**Pass:** 90% coverage ≥ .86 in every cell, separately for M1-ATT, M1-ATE and M2. M3 is reported; it is expected to
fail.

## Triple differences

- **Panel:** 51 units (26 treated), groups A and B, 10 periods. Treatment starts in period 6 for treated units in
  group A.
- **Outcome:** y = α_ug + λ_gt + γ_ut + τ·D + ε.
  - γ_ut is a unit × period shock common to both groups, including δ·(t − 5)·treated_u. That trend breaks
    group-A-only parallel trends but not the triple-difference assumption.
  - ε is AR(1) within unit × group (ρ = .5, SD .5).
- **Parameters:** τ ∈ {0, −2}, δ ∈ {0, 0.3}, so 4 cells; 2,000 draws each; seed [20282992, cell, draw].
- **Estimators:** T3, the triple difference with CR1 clustering by unit and t(50) intervals. Also reported: D2, the
  simple DiD in group A only (unit and period fixed effects, clustered).

**Pass (T3):** 90% coverage ≥ .86 in every cell. D2 bias and coverage are reported.

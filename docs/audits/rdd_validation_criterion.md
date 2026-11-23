# Round 98 regression discontinuity: pre-set criterion

Frozen with `scripts/rdd_validation.py`, `census/rdd_core.py` and `census/pums_tests.py` (SDR factors) before the full
run (tag `criterion-r98`). Author self-review, not independent.

## Continuous running variable (cutoff 0)

| Shape | x | Outcome | Noise SD |
| :--- | :--- | :--- | ---: |
| Linear | U(−1, 1) | y = 0.5x + τ·1(x ≥ 0) + ε | 0.3 |
| Quadratic | U(−1, 1) | y = x + 2x² + τ·1(x ≥ 0) + ε | 0.3 |
| Lee | 2·Beta(2, 4) − 1 | The Imbens–Kalyanaraman / Calonico–Cattaneo–Titiunik "Lee" quintic design | 0.1295 |

- **Jumps:** τ ∈ {0, 0.2} for the linear and quadratic shapes. The Lee design has its own jump of 0.04 (it is the
  τ = 0.2 cell) or 0 (the τ = 0 cell, with the right-hand intercept moved to remove the jump).
- **Cells and draws:** n ∈ {2,000, 10,000, 50,000}, so 18 cells; 2,000 draws each.
- **Estimators:**
  - R1: robust bias-corrected 90% interval (local quadratic at the IK bandwidth; HC);
  - R0: conventional interval (reported);
  - D1: density test at the cutoff (no manipulation, so its rejection rate is its size).

## Discrete running variable (PUMS-like)

- **Persons:** 30,000, with ages 45–84 drawn uniformly and cutoff 65.
- **Weights:** lognormal with CV 1. SDR replicate weights from `pums_tests.sdr_factors` in random person order.
- **Outcome:** y ~ Bernoulli(0.80 + 0.003(age − 65) [+ 0.0002(age − 65)² in the quadratic cells] + τ·1(age ≥ 65)),
  with τ ∈ {0, 0.05}.
- **Fuzzy cell:** treatment d ~ Bernoulli(0.05 + 0.85·1(age ≥ 65)); y ~ Bernoulli(0.80 + 0.003(age − 65) + 0.15d).
  The target is 0.15.
- **Cells and draws:** 5 cells; 2,000 draws each.
- **Estimators:** R1 with replicate SEs (R1-rep), with clustering by age (R1-cluster, reported), and with HC (reported).

## Acceptance

- R1 passes if its coverage is ≥ .86 in every continuous cell.
- R1-rep passes if its coverage is ≥ .86 in every discrete cell (sharp and fuzzy).
- D1 passes if its rejection rate at .10 is ≤ .10 in every continuous cell.
- Failing estimators stay exploratory.

Seeds: [20282981, cell, draw] (continuous); [20282982, cell, draw] (discrete).

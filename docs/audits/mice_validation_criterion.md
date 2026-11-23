# Round 100 multiple imputation by fully conditional specification: pre-set criterion

Frozen with `scripts/mice_validation.py` and `census/mice_core.py` before the full run (tag `criterion-r100`). Author
self-review, not independent.

## Design

- **Areas:** N ∈ {145, 600}.
- **Variables:**
  - x3 ~ N(0, 1), always observed;
  - x1 = 0.5·x3 + N(0, 1);
  - x2 = 100·Beta(2, 5) + 5·x3, a skewed, rate-like variable;
  - y = 1 + 0.5·x1 + 0.02·x2 − 0.3·x3 + N(0, 1).
- **Missingness (MAR):** y, x1 and x2 are each missing independently with probability expit(c + x3).
  - c = −2.6 gives about 10% missing per variable ("low");
  - c = −0.5 gives about 40% ("high").
- **Analysis model:** OLS of y on x1, x2 and x3. The targets are 0.5, 0.02 and −0.3.
- **Cells and draws:** 4 cells (N × missingness); 1,000 draws each; seed [20283001, cell, draw].

## Estimators

- **I1-pmm:** FCS with predictive mean matching for all three incomplete variables.
- **I1-norm:** FCS with Bayesian linear regression.
- **Both:** m = 20 and 10 cycles; Rubin's rules with Barnard–Rubin df; 90% intervals.
- **CC:** complete-case analysis (reported).

## Acceptance

- **Pass (each of I1-pmm and I1-norm):** coverage of all three slopes ≥ .86 in every cell.
- **Reported:** complete-case bias and coverage; the mean FMI.
- **Exact check (tests):** with δ = 0 the δ-adjusted imputation equals the unadjusted one for the same seed.

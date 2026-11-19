# Round 47: pre-set criterion (causal and missing-data robustness)

Frozen together with `scripts/causal_robustness_validation.py`, `census/causal_robustness_core.py` and
`census/causal_core.py` (Round 41) before the full run. N = 145 independent areas in every cell. Error
SDs are lognormal (log-SD .5) and rescaled in each draw so that mean(s²) matches the stated reliability.
Procedures receive the true per-area error variances, so the validation does not include noise in
published MOEs. 2,000 draws per cell, run in chunks of 250. Draw d of cell c uses
`default_rng([20270501 + c, d])`.

- **T (6 cells): treatment effect with noisy confounders that push the same way.**
  - Design: reliability .9/.8/.7 × confounder correlation 0/.3; T ~ Bernoulli(expit(.5z₁ + .5z₂));
    y = 1 + .5T + .5z₁ + .5z₂ + ε.
  - T0: Round 41 AIPW on the observed W (comparison).
  - T1: AIPW on confounders calibrated within each treatment group, E[Z | W, T]. The interval is a 90%
    percentile bootstrap from 200 row resamples that re-estimate the calibration.
  - Target: .5.
- **W (10 cells): weak instruments.**
  - Design: expected first-stage F of 2/5/10/20/30 × reliability of x of .9/.7; instrument z; x* = πz + v;
    y = 1 + .5x* + ε.
  - W1: Round 41 2SLS with the Wald interval.
  - W2: the Anderson–Rubin set at level .90, homoskedastic F(1, N − 2).
  - Target: .5.
  - Draws are pooled within each reliability and binned by **observed** first-stage F: [0, 5), [5, 10),
    [10, 20), [20, ∞).
- **S (6 cells): error-prone mediator.**
  - Design: reliability of M (relative to Var M = 1.16) of .9/.8/.7 × b = .5/.25; M = .4X + e;
    y = .3X + bM + ε.
  - S0: naive percentile bootstrap with 400 resamples (comparison).
  - S1: a from W ~ X; b from y ~ X + E[M | W, X]; percentile bootstrap with 400 resamples.
  - Target: .4b.
- **D (4 cells): two incomplete covariates.**
  - Design: MCAR or MAR (missingness depends on y, logistic slope 1 on standardised y, independent for the
    two covariates) × missing fraction .2/.4 for each covariate; x₁, x₂ correlation .5;
    y = 1 + .5x₁ + .5x₂ + ε, Var ε = .75.
  - D1: chained equations with m = 20 imputations and 10 cycles, proper Bayesian linear draws, HC3
    within-imputation variances, and Rubin's rules with the Barnard–Rubin df.
  - D0: complete case with HC3 and t(n − 3) (comparison).
  - Targets: both slopes, .5.

**Acceptance.** Failed fits count as non-coverage.

| Procedure | Passes if 90% coverage ≥ .86 in |
| :--- | :--- |
| T1 | every T cell |
| S1 | every S cell |
| D1 | every D cell, for both slopes |
| W2 | every observed-F bin of both reliabilities; a bin with fewer than 200 draws fails |

The W1 cut-off F₀ is the smallest bin lower edge with W1 ≥ .86 (and at least 200 draws) in that bin and in
every higher bin, in both reliabilities. If no bin edge qualifies, there is no cut-off.

**Departures from the plan, fixed before the run.**
- The AR set is inverted exactly. With one instrument it is a quadratic inequality, so no grid is used.
  The tests check it against a grid.
- MAR missingness depends on the fully observed outcome only. Making it depend on the other covariate
  would not be MAR when that covariate is itself missing.

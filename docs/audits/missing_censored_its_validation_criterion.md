# Round 42 procedures: pre-set criterion

Frozen with `scripts/missing_censored_its_validation.py` and `census/mci_core.py` before the full run.

- Missing (145 areas; target 0.5): x, w ~ N(0, 1), corr 0.5; y = 1 + 0.5x + 0.5w + N(0, 1); w missing with
  probability expit(−1.6 + 0.9(y − ȳ)) (MAR on the observed outcome; ≈ 20%) or 0.2 (MCAR). D0 complete case
  (HC3); D1 multiple imputation (20 proper Bayesian regression draws of w on x and y; HC3 fits; Rubin's
  rules, Barnard–Rubin-free t df). With one incomplete variable, chained equations (MICE) reduce to this
  imputation; it is implemented directly for speed. Before freezing, missingness was moved from x to y,
  because x-dependent missingness leaves complete-case regression unbiased.
- Censored (145 counties; target 0.3): expected counts lognormal (median 10 or 30); λ = E·exp(0.3x)·Gamma(4,
  1/4); counts of 1–9 hidden. C0 complete-case Poisson (HC3); C1 interval-censored Poisson likelihood
  (hidden counts in [1, 9]) with a numerical sandwich.
- ITS (targets: level change 1, slope change 0.2): 20 annual points, interruption at year 11, AR(1)
  errors φ = 0.3 or 0.6, innovation SD 1. A0 OLS; A1 Newey–West HAC (lag 2); A2 iterated AR(1) GLS (GLSAR).
- 6 cells, 2,000 draws, seed 20270304 + cell.
- **Acceptance:** 90% coverage ≥ .86 in every cell of the problem (ITS: level and slope); failures count as
  non-coverage; D0, C0, A0 are comparisons.

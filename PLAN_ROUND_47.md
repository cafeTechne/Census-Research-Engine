# Round 47 plan: causal and missing-data robustness

**Goal.** `ROADMAP_BACKLOG.md` issues N5–N8. The Round 41 causal validation had four limits. Its
confounding effects pulled in opposite directions, so the error in noisy confounders cancelled out. Every
instrument was strong, so the corr < .3 weak-instrument cut-off was never tested. Mediation with an
error-prone mediator failed (.69–.72). Multiple imputation was validated with one incomplete covariate
only. Each of these gets a fixed simulation, and only procedures that pass enter the engine.

Version 0.44.0. Baseline: the Round 46 suite. Branch `phase47/causal-robustness`. Validation first.
Multiple imputation combined with ACS replicate error stays in the backlog (no agreed design).

## 1. Validation (`scripts/causal_robustness_validation.py` → `docs/audits/causal_robustness_validation.md`/`.json`)

New frozen core: `census/causal_robustness_core.py`. Frozen files: that core, the script, the criterion doc,
and the existing `census/causal_core.py`. N = 145 independent areas in every cell. Error SEs are lognormal
(log-SD .5), scaled to the stated reliability; the analyst sees W and its SE, as in practice.
2,000 draws per cell; seed `20270501 + cell`.

**T: treatment effects with noisy, same-sign confounders (6 cells).**
- Confounders z₁, z₂ ~ N(0, 1) with correlation ρ ∈ {0, .3}.
- Treatment T ~ Bernoulli(expit(.5z₁ + .5z₂)).
- Outcome y = 1 + .5T + .5z₁ + .5z₂ + ε.
- Both confounders are observed with error at reliability ∈ {.9, .8, .7}.
- Target: the true ATE .5.

Procedures:
- **T0:** AIPW on the observed W (engine `estimate_effect`; comparison).
- **T1:** AIPW on regression-calibrated confounders Ẑ = E[Z | W, T]. The calibration is estimated within
  the sample using the known per-area error variances, with Var(Z | T) by moments within each treatment
  group. The 90% interval is a percentile bootstrap from 200 row resamples that re-estimate the
  calibration.

**W: weak instruments (10 cells).**
- Error-free x* ~ N(0, 1); observed x = x* + u at reliability ∈ {.9, .7}.
- Instrument z ~ N(0, 1), with x* = πz + v, Var(x*) = 1.
- π is set so the expected first-stage F is ∈ {2, 5, 10, 20, 30}.
- Outcome y = 1 + .5x* + ε. The exclusion restriction holds.
- Target: .5.

Procedures:
- **W1:** 2SLS with the Wald interval (engine `causal_core.iv_2sls`).
- **W2:** the Anderson–Rubin interval, obtained by test inversion over a grid of β (the AR statistic
  regresses y − βx on z with an F(1, N−2) reference). It can be unbounded or disjoint. An interval that
  covers .5 counts as covering, and the share of unbounded intervals is reported.

Draws are pooled across W cells within each reliability and binned by **observed** first-stage F:
[0, 5), [5, 10), [10, 20), [20, ∞).

**S: mediation with an error-prone mediator (6 cells).**
- X ~ N(0, 1), error-free; M = .4X + e.
- y = .3X + bM + ε, with b ∈ {.5, .25}.
- M is observed with error at reliability ∈ {.9, .8, .7}.
- Target: the indirect effect .4b.

Procedures:
- **S0:** naive product of coefficients with the percentile bootstrap (engine `mediation`; comparison).
- **S1:** calibrated:
  - The a-path comes from W ~ X. Error in a dependent variable does not bias this slope.
  - The b-path comes from y ~ X + M̂, with M̂ = E[M | W, X] estimated using the known error variances.
  - The interval is a percentile bootstrap of the product, from 400 resamples that re-estimate the
    calibration.

**D: two incomplete covariates (4 cells).**
- x₁, x₂ ~ N(0, 1) with correlation .5; y = 1 + .5x₁ + .5x₂ + ε (R² ≈ .5).
- Each covariate is missing in fraction ∈ {.2, .4} of areas, under MCAR or MAR. Under MAR, missingness
  of x₁ depends on y and x₂, and missingness of x₂ on y and x₁ (logistic, scaled to the fraction).
  Rows with both missing are allowed.
- Targets: the true slopes on x₁ and x₂.

Procedures:
- **D1:** chained equations (fully conditional specification). There are m = 20 imputations with 10
  cycles each. Each conditional model is Bayesian linear regression with proper draws, as in Round 42, on
  the outcome and the other covariate. The imputations are combined with Rubin's rules and the
  Barnard–Rubin df.
- **D0:** complete case (comparison).

**Acceptance.** 90% coverage must be ≥ .86, and failed fits count as non-coverage.

| Problem | Procedure | Passes if coverage ≥ .86 in |
| :--- | :--- | :--- |
| T | T1 | every cell |
| S | S1 | every cell |
| D | D1 | every cell, for both slopes |
| W | W2 (Anderson–Rubin) | every F bin, in both reliabilities |
| W | W1 (2SLS Wald) | the bins at and above the cut-off (see below) |

The W1 cut-off is the smallest bin lower edge F₀ such that W1 covers ≥ .86 in that bin and in every
higher bin, in both reliabilities. If even the [20, ∞) bin fails, W1 is not validated for any F.

## 2. Engine (only what passes)

- **T1:** `estimate_effect(..., calibrate=True)` when confounders carry `_se` columns. It reports
  `validated` per the audit. Without calibration, noisy confounders keep their warning and the T0 results
  are quoted.
- **W:** `iv_slope` reports `first_stage_f` and sets `validated = F ≥ F₀`, replacing the corr < .3
  convention.
  - If W2 passes, it also returns `ar_interval` (with `unbounded`), which is validated at any F.
  - The MCP `estimate_effect(kind="iv")` reports both intervals, and names the AR interval as the one to
    use when F < F₀.
- **S1:** `mediation(..., calibrate=True)` when the mediator has an SE column.
- **D1:** `impute_and_fit(incomplete=[a, b])` accepts one or two covariates. One covariate keeps the
  Round 42 algorithm byte for byte.
- **Shared steps:**
  - Mirror the rule text in `agent_protocol.md`, the recipes, `mcp_profiles` and the docstrings.
  - Update STATUS and the CHANGELOG.
  - Add tests that check the engine flags equal the audit.
  - Keep goldens unchanged (causal tools are not in manifests).
  - Run the full suite.
- **Exploratory MI/NY example** (`scripts/r47_causal_example.py`): the Round 41 IV design, with poverty
  2018–2022 instrumented by the non-overlapping 2013–2017 release, reporting F and both intervals. It also
  computes a calibrated AIPW of a binary county indicator, if T1 passes.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | | |
| T / W / S / D results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

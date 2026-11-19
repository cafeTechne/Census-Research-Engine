# Round 46 plan: measurement-error-corrected GLM slopes and EIV with more error-prone covariates

**Goal.** STATUS backlog 1 and 4 (`ROADMAP_BACKLOG.md` Round 46): no validated correction exists for
covariate sampling error in binomial, Poisson or NB2 models, and the spatial EIV (G1/G2) is validated only
with up to two error-prone covariates.

- **R (GLM correction):** validate the existing `census.models.regression_calibration` (RC: E[X | W] with
  per-area error variances, Var(X) by moments, row-bootstrap SE with 200 resamples; already validated for
  linear models, "approximate" for GLMs) against the **true** slope for binomial, Poisson and NB2 outcomes.
  SIMEX is not re-tested: it failed for linear models (coverage .81 at reliability .71) and costs ~1.5 s per
  fit.
- **M (more covariates):** re-run the Round 35 G1/G2 design with three and four error-prone covariates.

Version 0.43.0. Baseline: 2007 passed, 37 skipped. Branch `phase46/glm-correction`. Validation first.

## 1. Validation (`scripts/glm_correction_validation.py` → `docs/audits/glm_correction_validation.md`/`.json`)

**R cells (12):** model ∈ {binomial, Poisson, NB2} × covariate reliability ∈ {.9, .7} × error correlation
between the two covariates' errors ∈ {0, .3}. 145 independent areas; true x₁, x₂ ~ N(0, 1), corr .5;
per-area error SEs lognormal (log-SD .5) scaled to the reliability; observed W = X + U; 80 replicates
(`census.simulation.make_replicates`, with the error correlation) give the SE columns RC uses
(SE = √(4/80 Σ(W_r − W)²)), as in practice. Outcomes (slopes 0.3 on both x):
binomial: trials lognormal (median 3,900), logit −2.6 + 0.3x₁ + 0.3x₂ + 0.15ε; Poisson: E lognormal
(median 30), log-rate 0.3x₁ + 0.3x₂ + 0.15ε; NB2: as Poisson with Gamma(4) multiplicative noise instead of ε.
Procedures: **R1** RC (engine, `n_boot` 200, seed = draw), **R0** naive GLM with HC3 (engine
`fit_replicate`, scale robust, population target; comparison). Target: the true slope 0.3 on x₁.

**M cells (8):** p ∈ {3, 4} error-prone covariates × reliability {.9, .7} × field range {0, 100} km;
MI/NY geometry and fixed clusters; the Round 35 generator extended: x₁ from the Round 22 field, xₖ = .5x₁ +
√.75·(field); y = 1 + 0.5Σxₖ + 0.3·NY + error + outcome sampling error (SD .45). Procedures G1, G2 (frozen
`census.spatial_eiv_core`). Target: the true slope 0.5 on x₁.

2,000 draws per cell; seed `20270401 + cell`. **Acceptance:** 90% coverage ≥ .86 in every cell of the
problem, per procedure (R1 per model; G1, G2 per p); failed fits count as non-coverage.

## 2. Engine (only what passes)

R: GLM `regression_calibration` gets a validated flag per model (and drops "approximate" from its note
where validated); MCP `fit_model(method="regression_calibration", model=...)` already exists. M:
`spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES` raised to the largest p that passes. Rule text, recipes,
STATUS, tests (flags equal the audit), exploratory MI/NY example (county child poverty rate on median
household income and unemployment rate, both error-prone, binomial with RC vs naive), goldens unchanged,
full suite, version 0.43.0.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `4aceb22`, pushed before the full run | script, criterion doc frozen |
| R / M results | R1 Poisson .869–.893 and NB2 .887–.918 pass; binomial fails (.851); G1/G2 pass with p = 3 and 4 (.876–.927) | unstable point estimates at reliability .7, 100 km (mean bias up to +.17, up to 5.7% failed fits) |
| Engine, tests | `RC_VALIDATED`, manifest refusal of binomial RC, `VALIDATED_MAX_ERROR_COVARIATES = 4`; 8 tests | rule text mirrored |
| Example | Round 29 H1–H3 with poverty calibrated (NB2): slopes rise 4–10% | `docs/studies/r46_rc_example.md` |
| Goldens, final suite | both byte-identical; 2015 passed, 37 skipped | |
| Exceptions | example swapped from binomial child poverty (binomial RC failed) to the Round 29 NB2 models | |

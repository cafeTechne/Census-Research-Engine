# Round 49 plan: survey-weighted PUMS models

**Goal.** `ROADMAP_BACKLOG.md` issue N14. The PUMS tools (Round 32) test tables, means, medians and
proportions. They cannot fit models: no ordinal or multinomial logit, no weighted quantile regression,
and no regression with design-based variance.

The ACS publishes successive-difference replicate (SDR) weights for this purpose. The estimate is
refitted with each of the 80 replicate weights, and Var = 4/80 · Σ(θ_r − θ)². Round 32 validated this
for simple statistics. This round validates it for models.

Version 0.46.0. Baseline: the Round 48 suite. Branch `phase49/pums-models`. Validation first.

## 1. Validation (`scripts/pums_models_validation.py` → `docs/audits/pums_models_validation.md`/`.json`)

**Generator.** The Round 32 generator is reused unchanged: households sampled with unequal
probabilities along a geography g, household-correlated person attributes, and SDR replicate weights
built exactly as the ACS builds them. The cells are ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0} × m ∈ {800,
3000} households (8 cells). 2,000 draws per cell; seed `20270701 + cell`.

Frozen files:
- New `census/pums_models_core.py`.
- The script and the criterion doc.
- A targets file computed before the run (see below).
- `scripts/pums_tests_validation.py` and `census/pums_tests.py`, which are reused.

**Models and targets.** These follow from the Round 32 latent structure. Here s = sin(2πg) and
c = cos(2πg).

| Model | Outcome on covariates | Target | Kind of target |
| :--- | :--- | :--- | :--- |
| O: ordered logit | A (3 levels) on s | slope | pseudo-true value from a reference population of 400,000 households (the latent model is probit) |
| P: ordered probit | A on s | .8 | exact, from the latent model |
| M: multinomial logit | A on s | both slopes, A = 1 and A = 2 vs A = 0 | reference population |
| Q: weighted median regression | log y₁ on A (as numeric) and g | .15 and .3 | exact (the latent error is symmetric) |
| G: probit regression | C on A and c | .4 and .5 | exact; household clustering through ρ |

**Variance procedures.**
- **V1 (candidate):** the weighted fit plus the SDR replicate variance. All 80 replicate weights are
  refitted, warm-started at the full-sample estimate, with a normal interval.
- **V0 (comparison):** the weighted fit with the model-based SE, treating the weights as frequency
  weights normalised to n.

**Fitting.**
- The fits use Newton solvers in the frozen core (ordered logit and probit, multinomial logit,
  probit).
- Median regression uses iteratively reweighted least squares, the statsmodels QuantReg algorithm
  with weights.
- The tests check that each solver agrees with statsmodels on the full sample.

**Acceptance.** V1's 90% coverage must be ≥ .86 in every cell, for every target of the model. Each
model (O, P, M, Q, G) is judged separately, and failed fits count as non-coverage.

## 2. Engine (only what passes)

- **Library:** new `census.pums_models.fit_pums_model(df, outcome, covariates, model=..., weight="person")`
  for the models that pass. It reports the SDR interval, the replicate count used, and Rao–Scott-style
  small-cell flags (Round 32 `min_n`).
- **MCP:** new full-profile tool `fit_pums_model`. The `fit_model` docstring points to it for microdata.
- **Failing models:** exploratory.
- **Shared steps:**
  - Mirror the rule text in `agent_protocol.md`, the PUMS recipe and `mcp_profiles`, with tool counts
    refreshed in README and STATUS.
  - Add tests that check the engine flags equal the audit, plus solver equality tests.
  - Keep goldens unchanged.
  - Run the full suite.
- **Exploratory Michigan PUMS example:** the cached Round 32 extract, if present. It fits an ordered
  model of a household-income category on disability and age, and a median regression of earnings.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Targets, criterion commit | | |
| O / P / M / Q / G results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

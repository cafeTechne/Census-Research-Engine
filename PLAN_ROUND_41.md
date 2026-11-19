# Round 41 plan: treatment effects, instrumental variables and mediation

**Goal.** Public-health questions are often causal ("what does a policy or exposure do?"). With ACS
data the confounders, mediators and covariates themselves carry sampling error, which can bias causal
estimates. This round validates standard tools **and measures how ACS error breaks them**:

- **(A)** treatment effects (IPW, AIPW, regression adjustment) with confounders measured exactly or with
  ACS-type error; 2SLS with an independent second measurement as the instrument (a remedy for
  attenuation, STATUS backlog: measurement error in covariates); mediation (Sobel and percentile
  bootstrap) with an exact or error-prone mediator;
- **(B)** ships `census/causal.py` and an MCP tool `estimate_effect` (full profile, the seventh roadmap tool);
- **(C)** no real-data example: causal claims need a registered design; a synthetic worked example
  in the recipe instead.

Version 0.38.0. Baseline: 1967 passed, 37 skipped. Ground rules as Round 31 (branch `phase41/causal`;
validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures (90% intervals)

| ID | Estimand | Procedure |
| :--- | :--- | :--- |
| T1 / T2 / T3 | average treatment effect of a binary area exposure | IPW / AIPW / regression adjustment (statsmodels `TreatmentEffect`, logit propensity, GMM SEs) |
| I0 / I1 | slope of an error-prone covariate | OLS (naive, comparison) / 2SLS with an independent second measurement as instrument, HC0 sandwich |
| S1 / S2 | indirect effect a·b | Sobel delta method / percentile bootstrap (1,000 resamples) |

## 2. Validation (`scripts/causal_validation.py` → `docs/audits/causal_validation.md`/`.json`)

- 145 independent areas; 2,000 draws per cell; seed `20270225 + cell`.
- Treatment: two confounders Z (corr 0.3); T ~ Bernoulli(expit(0.5Z₁ − 0.5Z₂)); y = 1 + 0.5T + 0.5Z₁ + 0.5Z₂ + e.
  Confounders observed with reliability {1.0, 0.9, 0.7}. Target: ATE 0.5.
- IV: x ~ N(0, 1); x₁ = x + u₁ (reliability {0.9, 0.7}), instrument x₂ = x + u₂ (reliability {0.9, 0.7}),
  independent errors; y = 1 + 0.5x + e. Target 0.5.
- Mediation: X ~ N(0, 1); M = 0.4X + e_M; y = 0.3X + 0.5M + e; M observed with reliability {1.0, 0.8}.
  Target a·b = 0.2.
- **Acceptance:** coverage ≥ .86 — T1–T3 in the reliability 1.0 and 0.9 cells (0.7 reported); I1 in all
  four IV cells; S1/S2 in the exact-mediator cell (0.8 reported). Failures count as non-coverage.

## 3. Engine and docs

`estimate_effect(frame, outcome, treatment, confounders, method)`, `iv_slope(frame, outcome, x,
instrument, controls)`, `mediation(frame, x, mediator, outcome, controls)`; validated flags; notes on
the assumptions (no unmeasured confounding, overlap, exclusion restriction, sequential ignorability)
and on ACS error. MCP tool `estimate_effect` (kind = "treatment" | "iv" | "mediation"); recipe
`causal`; mirrored rule text. Tests against statsmodels and by hand; flags against the audit. Goldens
unchanged; full suite; STATUS, CHANGELOG, version 0.38.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | | |
| T / I / S results | | |
| Engine, tool, tests | | |
| Goldens, final suite | | |
| Exceptions | | |

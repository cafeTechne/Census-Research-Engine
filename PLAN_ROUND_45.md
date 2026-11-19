# Round 45 plan: count-model repairs

**Goal.** Repair the count-model gaps found in Rounds 39–44 (`ROADMAP_BACKLOG.md` N9, N17, N19; STATUS
backlog 1 "fixed Poisson-offset uncertainty"):

- **K1** hidden WONDER counts: the Round 42 interval-censored *Poisson* failed narrowly because of
  overdispersion; validate an interval-censored **NB2** likelihood.
- **K2** count slopes under spatial dependence: NB2-HC3 assumes independent areas; validate IM-8 with
  per-cluster count fits.
- **K3** uncertain exposure: expected counts built from ACS populations carry sampling error but are held
  fixed; check that NB2 with a fixed observed offset still covers.
- **L1** (library, no new statistic) state-respecting cluster assignment for adjacent states (N17), the
  assignment Round 44 used on OH/PA.

Version 0.42.0. Baseline: 1999 passed, 37 skipped. Branch `phase45/count-repairs`. Validation first.

## 1. Procedures (`census/count_repairs_core.py`, frozen with the criterion; 90% intervals)

| ID | Problem | Procedure |
| :--- | :--- | :--- |
| K1a | hidden counts in [1, 9] | interval-censored NB2 (parameters β, log α; ML by BFGS from the complete-case NB2 fit), numerical sandwich SE |
| K1b | | Round 42 interval-censored Poisson (comparison) |
| K1c | | complete-case NB2-HC3 (comparison) |
| K2a | spatial dependence | IM-8: α from the full-sample NB2 ML, per-cluster NB GLM with that α, mean of eight slopes, t(7) |
| K2b | | IM-8 with per-cluster Poisson GLM (consistent under overdispersion), t(7) |
| K2c | | pooled NB2-HC3 (independent areas; comparison) |
| K3a | noisy exposure | NB2-HC3 with the observed (noisy) exposure held fixed |
| K3b | | Poisson HC3 with the observed exposure (comparison) |

## 2. Validation (`scripts/count_repairs_validation.py` → `docs/audits/count_repairs_validation.md`/`.json`)

All cells: 145 areas, slope 0.3 on x ~ N(0, 1), target the true slope 0.3; 2,000 draws per cell; seed
`20270320 + cell`; failed fits count as non-coverage.

- K1 (4 cells): expected counts E lognormal (median 10 or 30, log-SD 1), λ = E·exp(0.3x)·Gamma(shape s,
  1/s) with s = 4 or 1.5; counts 1–9 hidden.
- K2 (4 cells): MI/NY geometry and fixed eight-cluster assignment (`docs/audits/im_acs_beta_star.json`);
  x and a log-rate residual (SD 0.3) are Gaussian fields with range 0 or 100 km (the Round 22 generator);
  NY indicator effect 0.2; E median 10 or 30; Gamma(4) overdispersion.
- K3 (2 cells): true E lognormal (median 30); observed E = E·exp(c·ε/√(E/30)) with ε ~ N(0, 1) and c =
  0.05 or 0.15 (smaller areas noisier); Gamma(4) overdispersion; the target is the slope with the true E.
- **Acceptance:** coverage ≥ .86 in every cell of the problem, per procedure; the comparisons are reported.

## 3. Engine (only what passes)

`census.missing_censored_its.fit_censored_negbin` (library; WONDER rule: no hidden value output);
`count_models.fit_count_model(..., spatial="clusters")` and MCP `fit_model(model="negbin",
spatial="clusters")`; offset notes; `spatial_clusters` `within_states` assignment option (k split across
states in proportion to their units, ≥ 5 units per cluster; validated only as G1/G2 on OH/PA in Round 44,
two states × four clusters). Rule text mirrored; recipe updates; exploratory MI/NY example (MI/NY county
child-poverty counts by metro class are not counts with exposure, so the example uses the R29 H2 hidden
counts under K1a, coefficients only). Tests; flags against the audit; goldens unchanged; full suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `0c368dd` | Pushed before the full run. |
| K1 / K2 / K3 results | Passed | K1a, K2a, K2b, K3a pass; comparisons as expected. |
| Engine, L1, tests | Done | 8 tests. |
| Example | Done | R29 counts; coefficients only; WONDER audit passed. |
| Goldens, final suite | Done | Identical; 2007 passed, 0 failures. |
| Exceptions | None | |

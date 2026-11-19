# Round 35 plan: corrected (EIV) slope inference under spatial dependence

**Goal.** Close STATUS backlog item 1. Round 30 made spatially robust inference available for the
naive target (coefficients on the ACS estimates as observed), but its corrected candidate (C2:
Fuller's estimator inside each of the eight clusters) failed: the per-cluster corrected moment
matrices were unstable. Registered EIV studies (R21b) therefore still have no spatial check. This
round validates two corrected procedures that pool the correction over all areas:

| ID | Procedure |
| :--- | :--- |
| G1 | IM-8 with a pooled within-cluster reliability correction: each cluster's naive slopes b_g are corrected by A = (Q − S_w)⁻¹Q and c = (Q − S_w)⁻¹ s_w, where Q = Σ_g X_gᶜᵀX_gᶜ (within-cluster centred slope columns), S_w = Σᵢ (1 − 1/n_g) Sᵢ and s_w = Σᵢ (1 − 1/n_g) sᵢ from the replicates; b_gᶜ = A b_g − c; t(7) on the eight corrected estimates |
| G2 | SAR-whitened Fuller EIV: λ̂ by maximum likelihood of a spatial-error model on the observed data (k = 6 nearest-neighbour row-standardised W from area coordinates); B = I − λ̂W applied to y, X and every replicate deviation; then the engine's Fuller estimator and sandwich (`fit_eiv`'s formulas) on the whitened rows; t(n − p) intervals |

Version 0.32.0. Baseline: 1935 passed, 37 skipped. Ground rules as Round 31 (branch
`phase35/spatial-eiv`; validation first; the maintainer agent implements and merges; releases wait).

**Non-goals.** No Bayesian or Poisson spatial models this round (Poisson naive inference is covered by
Round 30 C1). If both candidates fail, record it, keep EIV spatial inference refused and stop.

## 1. Validation (`scripts/spatial_eiv_validation.py` → `docs/audits/spatial_eiv_validation.md`/`.json`)

- Round 30's linear design exactly: 145 MI/NY counties, the frozen k = 8 assignment, x1 and x2
  spatial fields (correlation 0.5), y = 1 + 0.5·x1 + 0.5·x2 + 0.3·NY + error (spatial field),
  covariate reliability ∈ {0.9, 0.7} with lognormal per-area SEs and replicate cross-correlation 0.3.
- Added: outcome sampling error (reliability 0.9) whose correlation with x1's error is ∈ {0, 0.3}.
- Fields: independent or range 100 km. Cells: reliability × range × error correlation = 8 cells;
  2,000 draws; seed `20270114 + cell`.
- Target: the true coefficient of x1 (0.5). **Acceptance:** 90% coverage ≥ .86 in every cell
  (spatial and independent), per candidate; failed fits count as non-coverage. Informational:
  bias, interval width, λ̂, the naive C1 coverage of the true value, and fit failures.

## 2. Engine (only for a passing candidate)

`census/spatial_eiv.py`: `fit_spatial_eiv(formula, frame, replicates, coords, method="g1"|"g2")`,
linear formulas with numeric covariates and an optional state factor (absorbed under G1);
`fit_eiv(..., spatial_clusters={"k": 8, "method": "im"})` routes to G1 if G1 passed (replacing the
C2 refusal); G2 as `fit_eiv(..., spatial_error={"k_neighbors": 6})` if G2 passed. Manifest checks
follow the audit flags; docs mirrored.

## 3. Post hoc and example

R21b H1–H4 re-checked with the passing candidate(s), cached inputs only (as Round 30's post hoc,
author self-review, not independent), reported in `docs/studies/r35_posthoc_spatial_eiv.md`. If
nothing passes, that report states "unavailable".

## 4. Tests, acceptance, commits

Whitening and Fuller formulas against `fit_eiv` (G2 with λ = 0 equals `fit_eiv`); G1's correction
by hand; λ̂ against a grid search of the exact likelihood; flags equal the audit; refusals.
Goldens unchanged except intended EIV spatial routing (listed). Full suite; STATUS (backlog item 1);
CHANGELOG; version 0.32.0; section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `46fab40` | Pushed before the full run. |
| G1 / G2 results | Passed | G1 .879–.899; G2 .863–.918. |
| Engine, tests | Done | fit_spatial_eiv, MCP fit_model spatial option; 5 tests. |
| Post hoc R21b | Done | H1, H4 hold under both; m2 outside validated design. |
| Goldens, final suite | Done | Goldens identical; 1940 passed, 37 skipped, 0 failures. |
| Exceptions | Recorded | Manifest routing of fit_eiv spatial options deferred (backlog). |

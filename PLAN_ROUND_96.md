# Round 96 plan: spatial disease mapping with BYM2 and exceedance probabilities (Moraga)

**Goal.** Backlog N73 (Moraga, *Spatial Statistics for Data Science*, chapters 9–10; mapping in
`docs/literature/moraga_spatial_statistics.md`).
- Moraga maps relative risk from counts with a Poisson model: log θ_i = β + spatial (Besag ICAR) + unstructured
  effects (BYM/BYM2). She reports exceedance probabilities P(θ_i > c).
- The engine smooths counts only with an aspatial Poisson–gamma empirical Bayes model (Round 27). Its spatial
  Fay–Herriot model is Gaussian.

No INLA in Python, so the model is fitted with an own Laplace approximation (empirical Bayes: hyperparameters by
Laplace-approximate marginal likelihood). Version 0.92.0. Branch `phase96/disease-mapping`. Validation first.

## 1. Methods (frozen core `census/disease_mapping_core.py`)

- **B1: BYM2 Poisson model** (Riebler et al. 2016 parameterisation; scaled ICAR):
  - Y_i ~ Poisson(E_i θ_i), log θ_i = x_i'β + b_i, b = σ(√(1−φ) v + √φ u*).
  - Hyperparameters (σ, φ) by maximizing the Laplace-approximate marginal likelihood (grid then local optimisation).
  - The latent field comes from a Gaussian approximation at the mode (sparse Newton).
  - Relative risks with 90% intervals; exceedance probabilities P(θ_i > c) from the Gaussian approximation on the
    log scale.
- **B2: B1 with hyperparameter uncertainty** integrated over a small grid (INLA-style weights), for comparison.
- **Comparison:** Round 27 Poisson–gamma EB (aspatial) and raw SMRs.

## 2. Validation (`scripts/disease_mapping_validation.py`)

- **Geometries:** MI counties (83) and Wayne County tracts (Round 93 geometry).
- **Truth:** log relative risks from BYM2 with φ ∈ {0.2, 0.8} and σ ∈ {0.2, 0.5}.
- **Expected counts:** small (median E = 5) or moderate (median E = 30).
- **Draws:** 500 per cell.
- **Pass:**
  - area-level 90% coverage of θ_i ≥ .86 on average, and ≥ .80 for 90% of areas;
  - exceedance calibration: among areas with P(θ > 1.2) ≥ .8, the share truly above 1.2 is ≥ .75 in every cell;
    reported as a calibration curve.
- **Reported:** RMSE against Poisson–gamma EB and SMRs.

## 3. Engine

- **`small_area_estimates(kind="counts", spatial=True)`** or a new option of the existing smoothing path, taking
  observed and expected counts (from `expected_counts`, Round 73) and boundaries.
- **Outputs:** relative risks, intervals and exceedance probabilities for a declared threshold. Maps via `make_map`.
- **WONDER county counts 1–9** stay suppressed. Suppressed areas enter as censored counts (interval likelihood), or
  are refused if that path fails validation.
- **Recipe** `small_area` section; protocol rule; sources (Besag, York and Mollié 1991; Riebler et al. 2016; Moraga
  2023).

## 4. Example and acceptance

- **Example (exploratory):** MI county drug-overdose relative risks from the owner's county WONDER export, with
  exceedance maps for θ > 1.2. Only allowed outputs are written: smoothed relative risks and probabilities, never
  counts 1–9.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r96` |
| Results | intervals fail in 1 of 16 cells; exceedance calibrated | `disease_mapping_validation.md` |
| Engine, recipe | done | `spatial_model(kind="disease_map")`; recipe `small_area`; protocol |
| Example | done | `r96_disease_mapping_example.md` |
| Goldens, suite | pass | goldens byte-identical; 2362 passed, 42 skipped |
| Exceptions | 3 | see audit |

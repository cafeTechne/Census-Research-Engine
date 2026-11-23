# Round 96 BYM2 disease mapping: pre-set criterion

Frozen with `scripts/disease_mapping_validation.py`, `census/disease_mapping_core.py`,
`docs/audits/mi_county_geometry.json` and the Round 93 geometry before the full run (tag `criterion-r96`). Author
self-review, not independent.

## Geometry

- **MI counties:** 83 counties; queen contiguity from 2020 cartographic boundaries, plus one Mackinac–Emmet bridge
  edge so the graph is connected.
- **Wayne County tracts:** 625 tracts; Delaunay edges under 5 km (`scripts/spatial_models_validation.py`).

## Design

- **Truth.** log θ = b with b drawn from BYM2 (`simulate_field`), redrawn each draw. φ ∈ {0.2, 0.8} and
  σ ∈ {0.2, 0.5}.
- **Expected counts.** Fixed per cell: E_i = m·exp(0.5·Z_i)/median(exp(0.5·Z)) with m ∈ {5, 30}, seed
  [20282961, cell].
- **Counts.** y ~ Poisson(E θ).
- **Cells and draws.** 16 cells (geometry × φ × σ × m); 500 draws per cell; seed [20282962, cell, draw].

## Estimators

- **B1:** BYM2 with Laplace and empirical-Bayes hyperparameters.
- **B2:** the same with the hyperparameters integrated over the grid.
- **Comparison only:** the Round 27 Poisson–gamma EB (`eb_poisson_gamma`, its posterior interval) and raw SMRs
  (log((y + 0.5)/E)).

## Acceptance (each of B1 and B2)

- **Coverage:** in every cell, the mean over areas of each area's 90% coverage of θ_i (across draws) is ≥ .86, and
  at least 90% of areas have coverage ≥ .80.
- **Exceedance calibration:** in every cell where at least 50 area-draws have P(θ_i > 1.2) ≥ .8, the share of those
  with true θ_i > 1.2 is ≥ .75. A calibration table by probability decile is reported.

Reported: the RMSE of log θ for B1, Poisson–gamma EB and SMR. Failing estimators stay exploratory.

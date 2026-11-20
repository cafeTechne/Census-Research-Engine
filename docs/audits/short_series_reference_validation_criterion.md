# Round 55 criterion: short interrupted series and estimated reference populations

Committed before the full run. Frozen (`validate_pins`): `scripts/short_series_reference_validation.py`, the new
`census/its_small_core.py`, `census/small_spatial_core.py` (Round 48), `census/mci_core.py`,
`census/standardize.py` (new `reference_population_se`) and this file. 2,000 draws per cell; per-draw seeds
`[20280101 + cell, draw]`.

## I: interrupted series below 30 points (6 cells)

- Round 48's generator: `mci_core.its_design(n, n//2 + 1)`; stationary AR(1) errors with unit innovations; level
  change 1 and slope change .2; n ∈ {15, 20, 25} × φ ∈ {.3, .6}.
- **I2** Round 48 bootstrap-t (comparison, same seeds); **I3** bootstrap-t with the bootstrap series at
  φ_bc = min(.95, φ̂ + (1 + 3φ̂)/n); **I4** OLS with the EWC long-run variance (ν = max(2, round(0.4 n^{2/3}))
  cosine terms) and a t(ν) reference.
- **Acceptance:** a procedure is validated down to the smallest n at which both changes cover ≥ .86 for both φ,
  and at every larger tested n. Failed fits count as non-coverage.

## R: SMR with an estimated reference population (8 cells)

- Round 24 rates as truth. Reference person-years P_b are chosen so each band expects D/5 reference deaths, with
  D ∈ {50, 500}; D_b ~ Poisson(rate_b P_b). The observed reference population is P_b(1 + c z_b), with c ∈ {.02, .08}
  and SE c × observed. Estimated rates are D_b / observed P_b. Study bands are equal, scaled to a true expected
  count E ∈ {10, 100}; O ~ Poisson(1.2 E).
- **R1** `indirect_standardize(reference_counts=D, reference_population_se=SE)`; **R0** the same without the
  population SE (Round 25 behaviour; comparison).
- **Acceptance:** R1 covers the true SMR 1.2 at ≥ .86 in all eight cells. Refused draws and O = 0 count as
  non-coverage.

## Smoke run (not the audit)

One smoke run (40 draws per cell) checked that every cell runs. No design value changed after it.

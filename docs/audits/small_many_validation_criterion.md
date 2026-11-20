# Round 63 criterion: small samples and many covariates

Committed before the full run. Frozen (`validate_pins`): `scripts/small_many_validation.py`,
`census/its_small_core.py` (new `its_bootstrap_t_cons`, `its_bootstrap_t_bb`; Round 55 functions unchanged), the
Round 48 REML core, `census/mci_core.py`, `census/spatial_eiv_core.py`, `census/simulation.py`, the Round 22 field
generator, Round 58's script (geometry helper), both geometry files and this file. 2,000 draws per cell; per-draw seeds
`[20280801 + cell, draw]`.

## I: interrupted series below 20 points (6 cells)

- Round 48/55 generator; n ∈ {15, 17, 19} × φ ∈ {.3, .6}.
- Procedures:
  - **I3** (Round 55 bias-corrected bootstrap-t, comparison);
  - **I6** (I3 with each critical value the larger of the bootstrap-t and the t(n − p − 1) quantile);
  - **I7** (bootstrap series generated at φ_bb = min(.95, 2φ̂ − mean φ̂*) from 199 first-level parametric
    bootstrap series; 499-resample bootstrap-t).
- **Acceptance:** validated down to the smallest n at which both changes cover ≥ .86 for both φ there and at every
  larger tested n. I6 is never narrower than I3, so I3's Round 55 validation at 20+ points carries over to it.

## G: spatial EIV with six to eight error-prone covariates (24 cells)

- G1 and G2 with p ∈ {6, 7, 8} × reliability {.8, .9} × {MI/NY, OH/PA} × range {0, 100} km.
- Round 58's G generator: state indicator, the geometry's fixed eight clusters, target .5.
- **Acceptance:** a method passes p with ≥ .86 in every cell for that p. The gated cap is the largest p with every
  smaller tested p passing (5 if p = 6 fails).

Failed fits count as non-coverage.

## Smoke run (not the audit)

One smoke run (10 draws per cell) checked that every cell runs. No design value changed after it.

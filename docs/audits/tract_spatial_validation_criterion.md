# Round 71 criterion: tract-level spatial intervals

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/tract_spatial_validation.py` and `census/tract_spatial_core.py` (new);
- `census/scpc_core.py` (unchanged since Round 61) and the Round 22 generator;
- both tract geometry files;
- this file.

**Seen before this commit:** one 3-draw smoke run, which only checked that the script runs.

## Design

- **Geometries:**
  - North Carolina 2018 tracts (Round 67's 2,192 representative points);
  - Michigan 2020 land tracts (2,971; `docs/audits/mi_tract_geometry.json`).
  
  Queen contiguity comes from the matching cartographic boundaries, and tracts without neighbours are dropped.
- **Generator:** Round 22's linear design. x and the error are exponential-covariance fields at the cell's range;
  y = 1 + .5x + error; the target is .5. Ranges {0, 20, 50, 100} km, giving 8 cells.
- **Draws:** 1,000 per cell; seeds `[20281201 + cell, draw]`.
- **Procedures** (90% intervals):
  - **T1:** spatial error ML (spreg `ML_Error`, method "full"), normal interval;
  - **T2:** SCPC with ρ̄ .20 and .30;
  - **T3:** SCPC with ρ̄ equal to the average pairwise correlation of a 100 km exponential field on that geometry
    (a distance benchmark);
  - **T4:** HC3 (comparison).
- A failed fit counts as non-coverage.

## Acceptance

- A procedure is **validated** for tract geometry when it covers ≥ .86 in every cell of both geometries.
- One that passes every cell with range ≤ 50 km but not 100 km is **validated with that scope**, and the engine
  says so.
- Among validated procedures, the engine's tract default is the one with the shortest median interval length,
  averaged over its validated cells. Lengths are reported for all procedures.
- If none passes even at ≤ 50 km, tract-level spatial inference stays exploratory (N49 becomes a recorded limit).
  The residual-dependence warning (plan section 3) ships either way, since it is a diagnostic.

The design deliberately has no binomial cell. The plan proposed one at 100 km, but the binomial generator's naive
target is a pseudo-true value that this geometry has no reference for, and T1 is a linear model. This is recorded
as a plan deviation.

# Round 54 criterion: OH/PA external validity, part 2, and IM with 4/6 within-state clusters

Committed before the full run, with the geometry file it uses. Frozen (`validate_pins`):
`scripts/ohpa_revalidation2.py`, the new `census/im_clusters_core.py` (IM with G clusters; identical to
`census.im_acs` for G = 8), `census/im_acs.py`, `census/rc_spatial_core.py`, `census/count_repairs_core.py`,
`census/models.py`, `census/spatial_eiv_core.py`, `census/simulation.py`, `scripts/spatial_hac_validation.py`,
`scripts/im_acs_validation.py`, `docs/audits/im_acs_beta_star.json`, `docs/audits/ohpa_geometry.json`, the new
`docs/audits/im_cluster_counts_geometry.json` and this file. 2,000 draws per cell; per-draw seeds
`[20271201 + cell, draw]`; cell constants as in the source rounds (Round 30 `setup`) or from `20271201 + cell`.

## Geometry

`im_cluster_counts_geometry.json` (from `--prepare`, no network) holds within-state `cluster_points` assignments
with two and three clusters per state: MI/NY G = 4 (24/59/30/32 counties), G = 6 (13–36); OH/PA G = 4 (30–49),
G = 6 (21–30). G = 8 uses the Round 30 (MI/NY) and Round 44 (OH/PA, state-respecting) assignments.

## Problems

- **C (24 cells):** the 12 Round 30 C1 cells (linear/binomial/Poisson × range {0, 100} km × reliability {.9, .7})
  on MI/NY and on OH/PA. Naive IM with G = 4, 6 and 8 on the same draw (the state term is absorbed by the
  within-state clusters). Target: the observed-estimate β* of each geometry (Rounds 30 and 44 reference files).
- **K (4 cells):** Round 45's K2 design on OH/PA (median E 10 or 30 × range 0 or 100 km); K2a NB2 and K2b Poisson
  IM-8 counts. Target .3.
- **S (8 cells):** Round 53's S design on OH/PA; S1 `rc_im` (S0 naive IM-8 comparison). Target .3.
- **M (12 cells):** G1/G2 with p ∈ {3, 4, 5} × reliability {.9, .7} × range {0, 100} on OH/PA. Target .5.

## Acceptance

Coverage of the nominal 90% interval ≥ .86 in every cell of the problem, per procedure: IM with G passes when
all 24 C cells (both geometries) pass; K2a and K2b over the 4 K cells; S1 per model; G1 and G2 per p. Failed
fits count as non-coverage. Engine consequences are fixed in `PLAN_ROUND_54.md` section 3. Per-geometry C
outcomes are reported for information.

## Smoke run (not the audit)

One smoke run (30 draws per cell) checked that every cell runs. No design value was changed after it.

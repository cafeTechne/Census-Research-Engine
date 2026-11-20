# Round 58 criterion: spatial inference outside MI/NY

Committed before the full run. Frozen (`validate_pins`): `scripts/spatial_outside_validation.py`, the new
`census/scpc_core.py`, `census/rc_spatial_core.py` (new `rc_im_binomial`), `census/im_clusters_core.py`,
`census/im_acs.py`, `census/models.py`, `census/spatial_eiv_core.py`, `census/simulation.py`,
`scripts/spatial_hac_validation.py`, `scripts/im_acs_validation.py`, the MI/NY and OH/PA geometry/target files and
this file. Per-draw seeds `[20280401 + cell, draw]`.

## SCPC (Müller and Watson 2022)

- Distances: great-circle km between representative points. Benchmark c̄ solves mean_{l≠k} exp(−c̄ d_lk) = ρ̄.
- W: the eigenvectors of M Σ(c̄) M with the q largest eigenvalues (unit norm).
- τ = (ι'e/√n)/√(q⁻¹ Σ_j (w_j'e)²). The critical value is the largest 1 − α quantile of |τ| over 30 log-spaced c from
  c̄ to an average correlation of 10⁻⁴, plus independence, computed with Imhof's formula. q ∈ 1..20 minimises
  cv·E√(χ²_q/q).
- Influence values: OLS n[(X'X)⁻¹x_l û_l]_j; binomial and Poisson n[I⁻¹x_l(y_l − μ̂_l)·w_l]_j (trials or exposure).
- **ρ̄ ∈ {.05, .10}.** The authors' default .02 implies a 38 km benchmark on MI/NY. A product of two fields with a
  100 km range behaves like a 50 km field, whose average pairwise correlation is .033 (MI/NY) and .046 (OH/PA).
- **Size check before freezing** (OH/PA, ρ̄ .05, q 5, cv 2.362, 40,000 Gaussian draws): rejection .1014 at the
  benchmark, and .071 and .064 at 2 and 8 times c̄.

## Problems

- **N (24 cells):** Round 30 C1 cells × {MI/NY, OH/PA}. SCPC .05, SCPC .10 and IM-8 on the same draw. Target:
  each geometry's β* (`im_acs_beta_star.json`, `ohpa_geometry.json`). 2,000 draws.
- **R (3 cells):** MI/NY linear, binomial and Poisson at 100 km, reliability .7. IM-8, SCPC .05, SCPC .10.
  10,000 draws.
- **G (12 cells):** G1, G2 with p ∈ {3, 4, 5} × {MI/NY, OH/PA} × range {0, 100} km at reliability .8. Round 53/54
  M generator with the state indicator; target .5; 2,000 draws.
- **B (4 cells):** `rc_im_binomial`, MI/NY, reliability {.9, .7} × range {0, 100}. Binomial outcome with trials
  lognormal (median 3,900, minimum 50) and logit −2.6 + .3x₁ + .3x₂ + .3·NY + .15·field. Target .3; 2,000 draws.

## Acceptance

Coverage of the nominal 90% interval ≥ .86 in every cell of the problem:
- SCPC per ρ̄ and model, over N (both geometries) and R together;
- G1 and G2 per p over G;
- B1 over B.

Failed fits count as non-coverage. IM-8's R-cell coverage is reported, and its consequence is fixed in the plan.

## Smoke run (not the audit)

One smoke run (40 draws per cell; R cells 200) checked that every cell runs. No design value changed after it.

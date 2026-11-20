# Round 53 criterion: corrected GLM slopes, part 2

Committed before the full run. Frozen (`validate_pins`): `scripts/glm_correction2_validation.py`,
`census/models.py` (new `regression_calibration(se_method="jackknife")`, t intervals with n − p df; jackknife
flags all False before the run), the new `census/rc_spatial_core.py`, `census/count_repairs_core.py` (Round 45),
`census/spatial_eiv_core.py`, `census/simulation.py`, `scripts/spatial_hac_validation.py`, the IM-8 geometry
`docs/audits/im_acs_beta_star.json` and this file. 2,000 draws per cell; per-draw seeds `[20271101 + cell, draw]`
(cell constants from `20271101 + cell`).

## Why the jackknife

Round 46's binomial RC failed on its standard error, not its estimate: RC bias was −.016 to −.001, but coverage
was .851–.889, lowest at reliability .9. The 200-resample row bootstrap behaves like an HC0 sandwich. HC0
under-covers with 145 areas and the extreme leverage of binomial weights (trials vary 50-fold; overdispersion is
on the logit scale). The delete-one-area jackknife re-estimates the calibration in every refit; its variance is
close to HC3.

## Problems, cells and procedures

- **J (12 cells):** binomial / Poisson / NB2 × reliability {.9, .7} × error correlation {0, .3}; Round 46's R
  generator, unchanged except that seeds are per draw. **J1** = engine `regression_calibration(...,
  se_method="jackknife")`. Target .3 on x₁. Round 46's bootstrap results are the comparison.
- **S (8 cells):** Poisson / NB2 × reliability {.9, .7} × field range {0, 100} km; MI/NY geometry and the fixed
  IM-8 assignment; x₁ = Lz₁, x₂ = .5x₁ + √.75·Lz₂; replicate-estimated error SEs; E lognormal (median 30);
  log-rate .3x₁ + .3x₂ + .3·NY + .15·Lz₃ (NB2: × Gamma(4) noise). **S1** = `rc_im` (pooled calibration, then the
  Round 45 IM-8 count estimator); **S0** = `im_counts` on the observed covariates (comparison). Target .3 on x₁.
- **M (8 cells):** p ∈ {5, 6} error-prone covariates × reliability {.9, .7} × range {0, 100} km; Round 46's M
  generator; **G1**, **G2** (frozen `spatial_eiv_core`). Target .5 on x₁.

## Acceptance

Coverage of the nominal 90% interval ≥ .86 in every cell of the problem, separately per procedure and model (J1
per model, S1 per model, G1 and G2 per p). Failed fits count as non-coverage. Mean bias and failed fits are
reported. Engine consequences are fixed in `PLAN_ROUND_53.md` section 3.

## Smoke run (not the audit)

One smoke run (30 draws per cell, `--smoke-draws`) checked that every cell runs. Afterwards only the JSON
type of the outcome flags was changed (NumPy booleans to Python booleans). No design value changed.

# Round 46: pre-set criterion (GLM regression calibration; EIV with 3–4 error-prone covariates)

Frozen with `scripts/glm_correction_validation.py` (and the engine modules it calls:
`census/models.py` `regression_calibration`/`fit_replicate`, `census/count_models.py`,
`census/spatial_eiv_core.py`) before the full run.

- R (12 cells): binomial / Poisson / NB2 × reliability .9/.7 × covariate-error correlation 0/.3; 145
  independent areas; x₁, x₂ ~ N(0, 1), corr .5; heteroscedastic error SEs (lognormal, log-SD .5) scaled
  to the reliability; SE columns from 80 replicates. Outcomes with slope 0.3 on both covariates: binomial
  (trials median 3,900; logit −2.6 + … + 0.15ε), Poisson (E median 30; + 0.15ε), NB2 (E median 30;
  Gamma(4)). R1 = engine `regression_calibration` (200 row-bootstrap resamples, seed = draw); R0 = naive
  GLM with HC3 (NB2-HC3 for NB2; comparison). Target: the true slope 0.3 on x₁.
- M (8 cells): p = 3 or 4 error-prone covariates × reliability .9/.7 × range 0/100 km, MI/NY geometry
  and fixed clusters; x₁ the Round 22 field, xₖ = .5x₁ + √.75·field; y = 1 + 0.5Σxₖ + 0.3·NY + field
  error + outcome sampling error; G1, G2 (frozen core). Target 0.5 on x₁.
- 2,000 draws per cell; seed 20270401 + cell.
- **Acceptance:** 90% coverage ≥ .86 in every cell, per procedure (R1 per model; G1 and G2 per p); failed
  fits count as non-coverage.
- SE columns equal the replicate SEs exactly (`make_replicates` rescales to the target SE), so the
  validation does not include noise in published MOEs.

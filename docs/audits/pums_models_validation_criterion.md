# Round 49: pre-set criterion (survey-weighted PUMS models)

**Frozen before the full run:**
- `scripts/pums_models_validation.py` and `census/pums_models_core.py`.
- The reference targets in `docs/audits/pums_models_targets.json`.
- The Round 32 generator: `scripts/pums_tests_validation.py` and `census/pums_tests.py`.

**Generator.** This is the Round 32 superpopulation:
- Households are sampled along a geography g with probability ∝ exp(σ·field(g)), with household
  clustering ρ.
- SDR replicate weights come from the order-80 Paley Hadamard matrix with households sorted by g.

The sampling step mirrors Round 32's `draw_sample` line for line, because the original does not
return each person's g.

**Cells.** ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0} × m ∈ {800, 3000} households. 2,000 draws per cell,
run in chunks of 250. Draw d of cell c uses `default_rng([20270701 + c, d])`.

**Models, with s = sin(2πg) and c = cos(2πg).**

| Model | Specification | Targets |
| :--- | :--- | :--- |
| O | ordered logit of A (3 levels) on s, no intercept | the slope's pseudo-true value from a 400,000-household reference population |
| P | ordered probit of A on s | slope .8, exact |
| M | multinomial logit of A on (1, s), baseline A = 0 | both s slopes, from the reference population |
| Q | weighted median regression of log y₁ on (1, A, g) | .15 and .3, exact |
| G | probit of C on (1, A, c) | .4 and .5, exact |

**Fitting.**
- The solvers are Newton (ordered models: Hessian by central differences of the analytic gradient;
  multinomial: analytic), Fisher scoring (probit), and IRLS with an exact-LP fallback (median).
- They agree with statsmodels and an exact LP to at least five digits on a test sample.
- Before freezing, two smoke-run fixes were made: a Newton-decrement stop for warm starts already at the
  optimum, and the LP fallback.

**Procedures.**
- **V1:** the weighted fit with the SDR variance, 4/80 · Σ(θ_r − θ)² over 80 replicate refits
  warm-started at θ, and a normal 90% interval.
- **V0 (comparison):** the model-based SE with weights normalised to n. There is no V0 for median
  regression.

**Acceptance.** V1's 90% coverage must be ≥ .86 in every cell, for every target of the model. Each
model is judged separately, and failed fits count as non-coverage.

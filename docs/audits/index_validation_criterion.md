# Round 36 composite-index procedures: pre-set criterion

Frozen with `scripts/index_validation.py`, `census/index_core.py` and the reference targets
(`docs/audits/index_targets.json`) before the full run.

- 145 MI/NY counties (Round 30 coordinates); independent or spatial (100 km) Gaussian fields. A
  latent field f and five indicators xⱼ = λⱼ f + √(1 − λⱼ²) εⱼ, λ = (.8, .7, .6, .7, .5); observed =
  true + error with per-area lognormal SEs at reliability 0.9 or 0.7 and error cross-correlation 0.2;
  replicates from `census.simulation.make_replicates` with that correlation.
- S1: score = z·l with full-sample means, SDs and loadings (first principal component, or equal
  weights) fixed; SE from the 80 replicate scores; normal 90% interval. Target: the same formula
  applied to the area's true indicators.
- A1: Feldt interval for Cronbach's α; A2: log(1 − α) scale with Feldt's variance plus the replicate
  variance. Target: population α of the observed standardised indicators (400,000-area reference).
- 8 cells (reliability × field × weights), 2,000 draws, seed 20270121 + cell.
- **Acceptance:** S1 mean per-area coverage ≥ .86 and every area ≥ .80, per weighting (all cells);
  A1/A2 coverage ≥ .86 in every independent cell (spatial cells informational). Failures count as
  non-coverage. Selection for α: A1 if it passes, else A2.

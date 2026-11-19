# Round 48: pre-set criterion (small samples and spatial dependence)

**Frozen before the full run:**
- `scripts/small_spatial_validation.py` and `census/small_spatial_core.py`.
- The modules they call: `evidence_core`, `rank_methods`, `mci_core`, `index_core`.
- The earlier generators they import: the Round 33, 36 and 37 scripts, the Round 22 setup, the three
  target files and the MI/NY geometry.

**Data generation.** Each problem reuses the earlier round's generator: its per-area SEs, its spatial
Cholesky factor and its truth and observation functions. Draws use new seeds:
`default_rng([20270601 + cell, draw])`, 2,000 draws per cell, run in chunks of 250.

**I (6 cells): interrupted series.**
- Design: the Round 42 design with n ∈ {15, 20, 30} × φ ∈ {.3, .6}; interruption at n/2 + 1; level
  change 1, slope change .2. The first error comes from the stationary distribution.
- I0: Round 42 GLSAR (comparison).
- I1: REML AR(1). Bounded scalar search on (−.95, .95), then Prais–Winsten GLS with a t(n − 4)
  reference.
- I2: bootstrap-t around I1. 499 resamples of the centred innovations, with φ re-estimated in each.

**C (8 cells): correlations.**
- Design: the Round 33 cells (ρ 0/.4 × reliability .9/.7 × range 0/100 km), using the Round 33
  observed-value targets.
- C1: the Round 33 interval (variant 1 for Spearman and Kendall; variant 2 with replicates for Pearson)
  with n replaced by the Clifford–Richardson–Hémon effective n.
  - Moran's I is computed in 13 equal-width distance classes, on ranks for Spearman and Kendall.
  - n_eff = 1 + n²/tr(R̂ₓR̂ᵧ), capped at n.
  - The plan named this Dutilleul's estimator. It is the approximation underlying Dutilleul's modified
    t test.
- C2: IM-8 on within-cluster Fisher z, with a t(7) interval.

**A (8 cells): Feldt α.**
- Design: the Round 36 cells, using the Round 36 α target.
- A3: Feldt's interval with n_eff of the total score with itself.
- A4: IM-8 on log(1 − α_g), with a t(7) interval.

**H (6 cells): random-effects pooling.**
- Design: the Round 38 generator (lognormal sᵢ fixed per cell; SEs estimated with 80 df) with
  k ∈ {5, 7, 10} × τ² = {.5, 2} × mean(sᵢ²). The target is μ = 0.
- H1: Paule–Mandel with Hartung–Knapp.
- H2: H1 with the variance factor truncated at 1.

**B (4 cells): Bland–Altman limits.**
- Design: the Round 37 independent cells, using the Round 37 targets.
- B1r (observed limits) and B2r (error-free limits): limits m ∓ 1.645s, with Var(s²) = (m₄ − s⁴)/n,
  Cov(m, s²) = m₃/n, the delta method for s and a t(n − 1) critical value.

**Acceptance.** 90% coverage must be ≥ .86, and failed fits count as non-coverage.

| Procedure | Passes if coverage ≥ .86 in |
| :--- | :--- |
| I1, I2 | every cell with n ≥ n₀, for both changes and both φ; n₀ is reported, or none if even n = 30 fails |
| C1, C2 | every cell, judged per method (Spearman, Kendall, Pearson) |
| A3, A4 | every cell |
| H1, H2 | every cell |
| B1r, B2r | every cell, both limits |

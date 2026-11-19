# Round 32 PUMS procedures: pre-set criterion

Frozen with `scripts/pums_tests_validation.py`, `census/pums_tests.py` and the reference targets
(`docs/audits/pums_tests_targets.json`) before the full run (PLAN_ROUND_32 sections 1–2).

## Design

- Each draw generates a sample of m households directly from a superpopulation: geography
  g sampled with probability ∝ π(g) = exp(σ·z(g)) for a fixed smooth field z, so the weights 1/π
  have the cell's coefficient of variation; household size 1 + Poisson(1.5).
- Person attributes share household effects with intra-class correlation ρ: A (3 levels, with a
  geography trend), B (4 levels) and D (binary, prevalence .3), both independent of A; C (binary,
  depends on A and geography); income y0 (independent of A) and y1 (depends on A and geography);
  a rare binary R (prevalence .03) and the domain g < .125.
- SDR replicate weights as the ACS: households sorted by g, rows (k mod 80, k+1 mod 80) of a
  Paley order-80 Hadamard matrix, factor 1 + 2^(−3/2)(H[r₁, r] − H[r₂, r]); persons inherit them.
- Targets: unweighted values in one 2,000,000-household reference population (uniform g).
- Cells: ρ ∈ {0.1, 0.4} × weight CV ∈ {0.3, 1.0} × m ∈ {800, 3000}; 2,000 draws each; seed
  20261225 + cell.

## Acceptance

- Tests (nominal-.10 size within [.07, .13] in every cell): T0–T3 for the 2 × 2 (A = 0 vs not × D)
  and 3 × 4 (A × B) tables; M3 for three-group means of y0; M1 and M2 for two-group means.
- Intervals (90% coverage ≥ .86 in every cell): I1 difference of proportions of C (A = 1 vs 0),
  I2 odds ratio, I3 relative risk, I4 difference of means of y1, I5 difference of medians of y1,
  P1 Wald and P2 Korn–Graubard for R within the domain.
- Failed computations count as rejections or non-coverage. T0 is a comparison row.
- Selection: independence: first passing of T1, T2, T3 per table size; means: M3; two groups:
  M1 then M2; proportions: P2 if it passes, else P1 if it passes.

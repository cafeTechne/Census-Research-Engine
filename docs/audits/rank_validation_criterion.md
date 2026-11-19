# Round 33 rank procedures: pre-set criterion

Frozen with `scripts/rank_validation.py`, `census/rank_methods.py` and the reference targets
(`docs/audits/rank_targets.json`) before the full run.

- 145 MI/NY counties (coordinates from `im_acs_beta_star.json`); fields independent or spatial
  (range 100 km). True (x, y, z, w) are Gaussian fields transformed by exp(0.5·); corr(x, y) ∈
  {0, 0.4}; corr(z, x) = 0.5. Observed = true + N(0, se²) with per-area lognormal SEs scaled to
  reliability 0.9 or 0.7; group 1 and 3 SEs for w are 1.5× those of groups 0 and 2. Replicates from
  `census.simulation.make_replicates`.
- Coefficient intervals (atanh scale, 90%): Pearson SE² = 1/(n−3); Spearman 1.06/(n−3); Kendall
  0.437/(n−4) (Fieller, Hartley and Pearson 1957); partial Pearson given z, 1/(n−4). Variant 2 adds
  the 4/80 replicate variance of atanh(coefficient).
- Targets: the coefficient of the observed estimates in a 400,000-area iid reference sample per
  cell (Kendall: a 40,000-area subsample). Error-free coefficients are reported, not judged.
- Superiority (groups 0 vs 1 of four fixed urbanicity groups; w identically distributed under the
  null, so p = 0.5): Brunner–Munzel interval (B1) and with replicate variance (B2). Power under a
  0.3-SD shift is informational. Kruskal–Wallis (four groups) size in ρ = 0 cells.
- 8 cells (ρ × reliability × field), 2,000 draws, seed 20261231 + cell.
- **Acceptance:** intervals: coverage ≥ .86 in every independent-field cell, per procedure and
  variant; KW: nominal-.10 size in [.07, .13] in the independent null cells. Failures count as
  non-coverage. Selection: variant 1 if it passes, else variant 2. Spatial cells informational.

# Round 35 corrected slope inference under spatial dependence: pre-set criterion

Frozen with `scripts/spatial_eiv_validation.py` and `census/spatial_eiv_core.py` before the full run.

- Round 30's linear design: 145 MI/NY counties, frozen k = 8 assignment (no cluster mixes states),
  x1 and x2 spatial fields (corr 0.5), y = 1 + 0.5x1 + 0.5x2 + 0.3NY + error field; covariate
  reliability 0.9 or 0.7 (lognormal per-area SEs, replicate cross-correlation 0.3); outcome sampling
  error with mean variance 0.2 whose correlation with x1's error is 0 or 0.3; fields independent or
  range 100 km. Replicates from `census.simulation.make_replicates` with that correlation.
- G1: within-cluster naive slopes corrected by the pooled within-cluster reliability matrix
  (Q − S_w)⁻¹Q and offset (Q − S_w)⁻¹s_w; IM mean and t(7). G2: spatial-error λ̂ by ML (k = 6 nearest
  neighbours, row-standardised), whitening by I − λ̂W of y, X and the replicate deviations, then
  `fit_eiv`'s Fuller estimator and sandwich; t(n − p).
- 8 cells (reliability × range × error correlation), 2,000 draws, seed 20270114 + cell.
- **Acceptance:** 90% coverage of the true x1 slope (0.5) ≥ .86 in every cell, per candidate;
  failed fits count as non-coverage. C1 naive coverage of the true slope is informational.

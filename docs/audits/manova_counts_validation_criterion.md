# Round 39 multivariate and count procedures: pre-set criterion

Frozen with `scripts/manova_counts_validation.py`, `census/manova_counts_core.py` and the reference
targets (`docs/audits/manova_counts_targets.json`) before the full run.

- Multivariate (145 MI/NY counties, independent areas): m ∈ {2, 3} outcomes with cross-outcome
  correlation 0.5 and sampling error (reliability 0.85, replicates with that correlation); four random
  groups (q = 3); one-way, or ANCOVA with a covariate with its own error (reliability 0.7, independent
  of the groups). Null: no group effect. V1 multivariate wild score bootstrap (one Rademacher sign per
  area for all outcomes, 399 draws; replicate covariance of the stacked coefficients added); V0
  Pillai's trace (iid; comparison).
- Counts: expected counts lognormal (median 100 or 10); log-rate 0.3·x + 0.15·noise; gamma
  overdispersion (none or shape 2); structural zeros (none or 20%); x observed with error
  (reliability 0.9). N0 Poisson HC3; N1 NB2 (α by ML) HC3; N2 zero-inflated Poisson (Newton; HC0).
  Targets: each family's slope on the observed x in a 400,000-area reference (ZIP: Nelder–Mead
  estimate). Before freezing, ZIP's judged cells were limited to median 10: statsmodels' ZIP Hessian
  is NaN at median 100.
- 4 + 8 cells, 2,000 draws, seeds 20270211 + cell (counts + 100).
- **Acceptance:** V1 nominal-.10 size in [.07, .13] in every multivariate cell; 90% coverage ≥ .86 for
  N0 and N1 in every count cell and for N2 in the low-count cells with structural zeros. Failures count
  as rejections / non-coverage.

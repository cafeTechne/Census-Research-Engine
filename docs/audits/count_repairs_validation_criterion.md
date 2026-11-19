# Round 45 count-model repairs: pre-set criterion

Frozen with `scripts/count_repairs_validation.py` and `census/count_repairs_core.py` before the full run.

- 145 areas; slope 0.3 on x; target the true slope 0.3; 2,000 draws per cell; seed 20270320 + cell.
- K1 (hidden counts; 4 cells): E lognormal (median 10 or 30, log-SD 1); λ = E·exp(0.3x)·Gamma(s, 1/s), s = 4
  or 1.5; counts 1–9 hidden. K1a interval-censored NB2 (β, log α; BFGS from the complete-case NB2 ML;
  numerical sandwich); K1b Round 42 censored Poisson; K1c complete-case NB2-HC3.
- K2 (spatial; 4 cells): MI/NY geometry and the fixed eight-cluster assignment (`im_acs_beta_star.json`);
  x and a log-rate residual (SD 0.3) from the Round 22 field generator, range 0 or 100 km; NY effect 0.2;
  E median 10 or 30; Gamma(4). K2a IM-8 with per-cluster NB GLMs at the full-sample α; K2b IM-8 with
  per-cluster Poisson GLMs; K2c pooled NB2-HC3. t(7) for IM.
- K3 (noisy exposure; 2 cells): true E median 30; observed E = E·exp(c·ε/√(E/30)), c = .05 or .15;
  Gamma(4). K3a NB2-HC3 and K3b Poisson HC3 with the observed E fixed; target uses the true E.
- **Acceptance:** 90% coverage ≥ .86 in every cell of the problem, per procedure (K1a, K2a, K2b, K3a);
  failed fits count as non-coverage; K1b, K1c, K2c, K3b are comparisons.

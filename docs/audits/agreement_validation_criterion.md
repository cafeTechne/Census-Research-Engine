# Round 37 agreement procedures: pre-set criterion

Frozen with `scripts/agreement_validation.py`, `census/agreement_core.py` and the reference targets
(`docs/audits/agreement_targets.json`) before the full run.

- 145 MI/NY counties; the true value t is a Gaussian field (independent or range 100 km). Source A =
  t + error (lognormal per-area SEs, reliability 0.9 or 0.7). Source B's error-free value is
  0.2 + 1.05 t + δ with δ ~ N(0, 0.5²) (the sources genuinely disagree); B is observed with error
  (reliability 0.8, known SEs) or without. Errors independent between sources. (Before freezing,
  δ was added after a smoke run showed that with δ = 0 the error-free limits are near zero width,
  which is unrealistic for two different sources.)
- B0 bias (t interval); B1 observed limits of agreement (±1.645 SD; Bland–Altman SE); B2 error-free
  limits (error variances subtracted; delta method); C1 Lin's CCC; C2 CCC with error variances removed
  (Lin's variance at the corrected values); K1 Cohen's kappa of quintile classes.
- Targets from a 400,000-area reference per cell (kappa on a 40,000-area subsample).
- 8 cells, 2,000 draws, seed 20270128 + cell.
- **Acceptance:** 90% coverage ≥ .86 in every independent cell, per procedure (both limits for B1/B2);
  failures count as non-coverage; spatial cells informational.

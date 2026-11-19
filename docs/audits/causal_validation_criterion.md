# Round 41 causal procedures: pre-set criterion

Frozen with `scripts/causal_validation.py` and `census/causal_core.py` before the full run.

- 145 independent areas; 2,000 draws per cell; seed 20270225 + cell.
- Treatment (target ATE 0.5): confounders Z₁, Z₂ ~ N(0, 1), corr 0.3; T ~ Bernoulli(expit(0.5Z₁ − 0.5Z₂));
  y = 1 + 0.5T + 0.5Z₁ + 0.5Z₂ + N(0, 1); confounders observed with reliability 1.0, 0.9 or 0.7. T1 IPW,
  T2 AIPW, T3 regression adjustment (statsmodels `TreatmentEffect`, logit propensity, its GMM SEs).
- IV (target 0.5): x ~ N(0, 1); x₁ = x + u₁ (reliability 0.9/0.7); instrument x₂ = x + u₂ (reliability
  0.9/0.7), independent errors; y = 1 + 0.5x + N(0, 1). I0 OLS (HC0, comparison); I1 2SLS (HC0 sandwich).
- Mediation (target a·b = 0.2): X ~ N(0, 1); M = 0.4X + N(0, 1); y = 0.3X + 0.5M + N(0, 1); M observed
  with reliability 1.0 or 0.8. S1 Sobel; S2 percentile bootstrap (1,000 resamples). HC0 path models.
- **Acceptance:** 90% coverage ≥ .86 — T1–T3 in the reliability 1.0 and 0.9 cells; I1 in all four IV cells;
  S1/S2 in the exact-mediator cell. Failures count as non-coverage; other cells informational.

# Round 38 combining-evidence procedures: pre-set criterion

Frozen with `scripts/evidence_validation.py` and `census/evidence_core.py` before the full run.

- Meta-analysis: k ∈ {2, 4, 8} studies; within-study SEs lognormal (log-SD 0.5), fixed per cell; true
  effects μ + u, u ~ N(0, τ²), τ² = 0 or mean(s²); estimates θ + N(0, s²); SEs estimated as
  s·√(χ²₈₀/80) (replicate-based SEs). M1 fixed effect (normal), M2 DerSimonian–Laird (normal), M3
  Paule–Mandel τ² with the Hartung–Knapp–Sidik–Jonkman variance and t(k − 1). 2,000 draws per cell;
  seed 20270204 + cell.
- TOST: two independent estimates, margin 3 (SEs 1 and 1, or 1 and 2), SEs estimated as above; size
  with the true difference at the margin; 20,000 draws per setting.
- Power: two-sided z test at α .10 and .05 with the effect set to the minimum detectable effect for
  predicted power .5 and .8; SE estimated as above; 20,000 draws per setting.
- **Acceptance:** pooled: 90% coverage ≥ .86 per k (M1 judged only without heterogeneity; M2 and M3
  in all cells); TOST: size ≤ .07 at nominal .05; power: |predicted − empirical| ≤ .03.

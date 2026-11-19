# Round 34 ranking procedures: pre-set criterion

Frozen with `scripts/ranking_validation.py` and `census/ranking_core.py` before the full run.

- K areas (40 or 145), independent normal errors with lognormal SEs (log-SD 0.6), true values
  Normal(0, τ²) with τ = SNR × median SE (SNR 0.5 or 2); ties: none, or half the areas in groups
  of five sharing a true value. Population weights lognormal (log-SD 1) for the reference.
- R1 individual and R2 joint Klein–Wright–Wieczorek rank intervals (Bonferroni over K − 1 or
  K(K − 1)/2 pairwise z tests); R3 parametric-bootstrap percentile ranks (2,000 draws; comparison).
  A tie group's interval is covered if it contains any rank the group occupies.
- V1 Holm and V2 simultaneous max-|z| (20,000 Monte Carlo draws) comparisons of each area with the
  weighted state value; covariance from the exact formula for independent area errors.
- 8 cells, 2,000 draws each, seed 20270107 + cell.
- **Acceptance (nominal 90%):** R1 mean per-area coverage ≥ .86 and every area ≥ .80; R2 joint
  coverage ≥ .86; V1/V2 familywise error ≤ .13 under the global null; V2 joint coverage ≥ .86 under
  the alternative. R3 is judged like R1 for comparison only.

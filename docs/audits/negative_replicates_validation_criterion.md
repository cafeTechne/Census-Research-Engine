# Round 51 criterion: negative replicate estimates

Committed before the full run (`scripts/negative_replicates_validation.py`, frozen with
`scripts/segregation_realistic_validation.py`, `census/segregation.py`, `census/standardize.py` and the
Round 50 counts file; `validate_pins` checks them against this commit). 2,000 draws per cell.

## A. Segregation: clipping negative replicate counts at zero

- Design: Round 50's (2024 MI/NY tract counts and published SEs; rounded Gamma-copula observed counts; group
  correlation ρ ∈ {0, −.3}; two groups (poverty) and three groups (income)), except that the 80 replicates are
  Gaussian: observed + (SE/2)·z, z from the same copula, rounded; zero observed counts keep zero replicates.
  This produces negative replicate counts at small counts (a stress test: about 4% of populated tract-group
  cells in the smoke run, far more than the real files). Seeds `20270901 + cell`.
- Procedure: replicate counts below zero are set to zero before the index refits; SE = √(4/80 Σ(I_r − I)²);
  bias correction I − 4(mean I_r − I). All eight Round 50 variants are judged.
- Acceptance: Round 50's bin rule, unchanged (noise bins [0, .15), [.15, .30), [.30, .50), [.50, ∞); a bin with
  ≥ 5 counties passes when, in both ρ cells, mean county coverage ≥ .86 and ≥ 90% of its counties cover ≥ .80;
  validated range from the lowest bin to the first failing judged bin). **Plus** an affected-draw check: pooled
  coverage over (county, draw) pairs inside that validated range with at least one clipped replicate cell must
  be ≥ .86 in both ρ cells (not judged below 500 pairs in either cell).
- Clipping is validated for a variant when it has a validated range and the affected-draw check passes (or is
  not judged). The engine's clipped range is the smaller of this range and the variant's Round 50 range.
- Failed draws (undefined index or refit) count as non-coverage.

## B. SMR: negative band replicates

- Design: five bands, rates .0005, .001, .003, .01, .04; equal true populations scaled to E ∈ {10, 100}; one
  high-CV band (band 1, about 1% of E, or band 4, about 18%) with CV c ∈ {.6, 1.0}, the others CV .05 (8 cells).
  Observed band populations Gamma (mean truth, SD CV × truth); replicates Gaussian around the observed with
  SD = SE/2, independent, not rescaled; O ~ Poisson(1.2 E). Seeds `20270911 + cell`.
- Procedures: `indirect_standardize(negative_replicates="accept")` and `"clip"`; combined 90% interval of the SMR.
- Acceptance: a policy passes when coverage of 1.2 is ≥ .86 in all eight cells. Refused draws (a nonpositive
  replicate expected count) and O = 0 count as non-coverage. The share of draws with a negative band replicate
  is reported per cell.

## Smoke-run notes (200 draws, `--smoke`, not the audit)

The smoke run was used only to check the script runs and that negative replicates occur (segregation about
4% of cells; SMR 33–73% of draws). No design value was changed after it.

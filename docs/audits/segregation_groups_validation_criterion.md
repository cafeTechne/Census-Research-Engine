# Round 52 criterion: segregation beyond poverty and income

Committed before the full run. Frozen (`validate_pins`): `scripts/segregation_groups_validation.py`,
`scripts/segregation_realistic_validation.py` (Round 50, unchanged; its observation model and constants are
imported), `scripts/segregation_groups_counts.py`, the truth file `docs/audits/segregation_groups_counts.csv.gz`
(sha256 `5e44442c…ea29bee1`; 15,028 tracts in 2024 MI/NY/OH/PA, 7,731 in 2015–2019 MI/NY), `census/segregation.py`
and this file. 2,000 draws per cell; seed `20271001 + cell`.

## Designs and cells

| Design | Release, states | Groups | Negative ρ |
| :--- | :--- | :--- | ---: |
| black2 | 2024 MI/NY | black, nonblack | −.3 |
| hisp2 | 2024 MI/NY | hisp, nonhisp | −.3 |
| race4 | 2024 MI/NY | white, black, hisp, other + asian | −.3 |
| race5 | 2024 MI/NY | white, black, asian, hisp, other | −.2 |
| pov_ohpa | 2024 OH/PA | below, above | −.3 |
| black2_ohpa | 2024 OH/PA | black, nonblack | −.3 |
| contrast | MI/NY poverty, 2024 minus 2015–2019 | below, above | −.3 |

Each design is run with ρ = 0 and its negative ρ (14 cells). Equicorrelation −.3 is not a valid correlation matrix
for five groups (1 + 4ρ < 0), so race5 uses −.2; this was found when the first smoke run failed and is the only
design change made after a smoke run.

## Observation model, procedures and acceptance

- Round 50's model: rounded Gamma-copula observed counts (SD = published SE) and 80 replicates (SD = SE/2); 4/80
  replicate SE; bias correction I − 4(mean I_r − I). Counties with fewer than five populated tracts excluded.
- Two groups: D, isolation, H, naive and bias-corrected. Four and five groups: H naive and bias-corrected.
  Contrast: estimate I₂₀₂₄ − I₂₀₁₉ (independent draws), SE = √(SE₂₀₂₄² + SE₂₀₁₉²), target the true difference;
  counties in both releases, binned by the larger noise level.
- Bins by noise level (largest group median tract CV): [0, .15), [.15, .30), [.30, .50), [.50, .75), [.75, 1),
  [1, ∞). A bin with ≥ 5 counties passes when, in both ρ cells, mean county coverage ≥ .86 and ≥ 90% of its
  counties cover ≥ .80. Failed draws count as non-coverage.

## Engine ranges (combination rule, fixed now)

Per (index, variant, group count) a bin is validated when every design with that group count that judges it
passes it, and at least one judges it. Two-group designs: Round 50's MI/NY poverty audit (its bins map onto the
first three bins; it had no county above .50), black2, hisp2, pov_ohpa, black2_ohpa. Four groups: race4. Five
groups: race5. Contrast: the contrast design. The range starts at the lowest bin (unjudged bins before the first
judged bin included) and ends at the first failing bin or the first unjudged bin after a judged one. The engine
keeps Round 50's lower bound .15 for variants that failed Round 28, keeps clipped-replicate ranges (Round 51) at
most .50, and leaves three groups at Round 50.

## Smoke runs (not the audit)

Two smoke runs with `--smoke` (200 draws): the first stopped on the five-group correlation; the second ran all
designs. A `--chunk` option (draws per task; seeds are per draw, so results do not depend on it) was added for
speed. No other design value changed.

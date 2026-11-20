# Round 57 criterion: segregation, remaining gaps

Committed before the full run. Frozen (`validate_pins`): `scripts/segregation_gaps_validation.py`, the Round 50, 51
and 52 scripts it imports (unchanged), `scripts/segregation_r57_counts.py` and its output
`docs/audits/segregation_r57_counts.csv.gz` (2024 MI/NY B03002, six groups; byte-reproducible), the Round 50 and 52
counts files, `census/segregation.py` and this file. 2,000 draws per cell; per-draw seeds `[20280301 + cell, draw]`.

## Problems (12 cells)

- **A (8 cells): clipped replicates on race designs.** black2, hisp2, race4 and race5 (Round 52 groups and
  negative ρ: −.3, or −.2 for five groups) × ρ ∈ {0, negative}. Round 50 observed counts; Round 51 Gaussian
  replicates (observed + (SE/2)·z, rounded, zero stays zero) clipped at zero before the refits. All Round 52
  variants judged.
- **B (2 cells): six groups.** White, Black, Asian, Hispanic, multiracial and other (non-Hispanic AIAN, NHPI,
  other) × ρ ∈ {0, −.15}; −.3 and −.2 are not valid equicorrelations for six groups. Round 50 Gamma model; H
  naive and bias-corrected.
- **C (2 cells): same-release county contrasts.** Round 50 MI/NY poverty counts × ρ ∈ {0, −.3}; Gamma model.
  Pairs are consecutive counties in GEOID order within each state (68 pairs). The estimate is I_a − I_b; the SE is
  √(4/80 Σ((I_ra − I_rb) − (I_a − I_b))²) (`segregation_test` for same-release contrasts). The target is the true
  difference. Pairs are binned by the larger of the two noise levels; all six two-group variants are judged.

## Acceptance

- Round 52's bins and Round 50's bin rule: a bin with ≥ 5 units passes when, in both ρ cells, mean coverage ≥ .86
  and ≥ 90% of units cover ≥ .80. Failed draws count as non-coverage.
- In A, a bin also needs pooled coverage ≥ .86 over its county-draws with a clipped cell, in each ρ cell with at
  least 500 such pairs.
- **Combined ranges:** a bin counts only if every design judging it passes (Round 52 rule). For two groups the
  designs are Round 51's MI/NY poverty audit (first three bins, counted as passing only where that variant also
  passed Round 51's affected-draw check), black2 and hisp2. Four groups use race4, five race5, six race6;
  same-release contrasts use the pairs.
- The engine caps each clipped range at the variant's unclipped range.

## Smoke run (not the audit)

One smoke run (60 draws per cell) checked that every cell runs. No design value changed after it.

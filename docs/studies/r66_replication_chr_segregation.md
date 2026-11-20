# Replication A: County Health Rankings 2025 county Black/White residential segregation

**Status: registered numeric replication (criterion `dd48bf6`, deviation 1 at `d30d7ed`). Author self-review,
not independent.** Audit: `docs/audits/r66_numeric_replication.md`; rule: `docs/audits/r66_replication_criterion.md`.

## Target

County Health Rankings & Roadmaps 2025, "Residential Segregation – Black/White" (measure v141): a county
dissimilarity index on a 0–100 scale. It uses ACS 2019–2023 tract counts and is reported for counties with at
least 100 Black residents. The published values come from CHR's own calculation repository (commit `a516395`,
`measure_datasets/v141_r2025.csv`, SHA-256 pinned).

CHR's code defines the measure as follows:
- tract counts are **population in households** (ACS B11002), not all persons;
- "Black" is Black alone (B11002B);
- "White" is White alone **including Hispanic** (B11002A), although a code comment says "not Hispanic".

## Result: replicated

| Rule (fixed in advance) | Result |
| :--- | :--- |
| Median absolute difference ≤ 0.5 points | 0.0000 |
| At least 90% of counties within 1 point | 100% |
| Counties reported by only one side | 0 |
| Largest difference | 0.0000 points |

All 2,055 comparable counties match to rounding. Connecticut was excluded, as pre-registered: the 2023 ACS uses
planning regions, and CHR's tract crosswalk is not public. Suffolk and Ulster (NY) are suppressed by CHR.

## What the published index does not show (descriptive)

CHR's index is the plain ("naive") dissimilarity, with no uncertainty. The engine's replicate method uses
B03002 non-Hispanic Black against non-Hispanic White, because B11002A/B have no Census replicate files. In 563
counties of GA, TX, AZ, MI and NY:
- **308 counties are validated** by the noise gates (GA 101 of 159, TX 104 of 244, MI 53 of 83, NY 48 of 62, AZ
  2 of 15);
- 10 small Texas counties had an undefined replicate refit and are listed in the audit.

Where both exist (433 counties), the bias-corrected index is a median **3.5 points lower** than CHR's published
value (interquartile range −9.0 to −0.5). Two causes mix here:
1. **Definition:** non-Hispanic persons rather than household population with Hispanic Whites included.
2. **Noise:** the naive index is pushed upward by sampling noise, most in counties with few Black residents.

Readers comparing small counties on the published index should expect it to overstate segregation.

## What this establishes

The engine reproduces a widely used published county health indicator exactly from public ACS data. That covers
every county nationally, including states with many small counties. The extraction, tract handling and index code
agree with an independent implementation (CHR's R code).

It does **not** test interval coverage. Simulation S does that: `docs/audits/r66_segregation_geometry_validation.md`.

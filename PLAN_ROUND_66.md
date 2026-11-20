# Round 66 plan: numeric replications A and B, with segregation coverage beyond MI/NY

**Goal.** The first two replication targets the owner chose on 2026-11-20 (`docs/studies/replication_shortlist.md`;
backlog N44). Both are computation checks against published Census-based values. Version 0.62.0. Branch
`phase66/numeric-replications`.

**Order.** Each criterion file is committed before any comparison is computed. The published values may be
downloaded beforehand, but no comparison is made before the commit.

## A. County Health Rankings 2025: residential segregation, Black/White

- **Published values.** CHR 2025 "Residential Segregation – Black/White" (dissimilarity, 0–100; ACS 2019–2023;
  counties with at least 100 Black residents). It comes from CHR's 2025 national data file (additional measures).
  Read CHR's technical notes first, and record the exact group definitions (non-Hispanic or not) and tract rules
  in the criterion. If the notes are ambiguous, use non-Hispanic Black alone and non-Hispanic White alone
  (B03002_004, B03002_003) and every tract with a positive total. If both readings stay plausible, compute both
  and pre-register which one is primary.
- **Our values.** ACS 2019–2023 tract counts for every state and DC from the API (one request per state,
  `tract:*`, cached). Compute naive D × 100 (CHR publishes the plain index) and, beside it, the bias-corrected D.
- **Replicated if** (fixed in the criterion):
  1. the median absolute difference over counties with a CHR value is ≤ 0.5 points;
  2. at least 90% of counties are within 1.0 point.
  
  Differences greater than 2 points are listed with their tract and population counts.
- **Interval part.** In GA, TX and AZ (many small counties; large Western counties), plus MI and NY, compute VRE
  replicates. Report how many counties the noise gates validate, and how far the bias-corrected D sits from the
  published naive D.

## B. Census Bureau state Gini index (B19083)

- **Published values.** B19083_001E/M, ACS 2019–2023 five-year, for a pre-set sample of 12 states spanning size
  and region: WY, VT, DE, NM, MS, AZ, GA, MI, NY, TX, CA, NC.
- **Our values.** 2019–2023 PUMS household files for those states; HINCP for households (no group quarters, no
  vacant units); WGTP and the 80 WGTP replicates; `pums_inequality` Gini with its validated interval. Record how
  zero and negative incomes are treated, following the Census definition where it is documented.
- **Replicated if** (fixed in the criterion):
  1. the median |difference| is ≤ .005;
  2. our 90% interval contains the published value in at least 10 of 12 states.
  
  PUMS income is top-coded and drawn from a subsample, and the published value uses the full internal sample, so a
  small negative bias is expected. The criterion states it in advance.

## S. Segregation coverage on new geometries (simulation)

- Round 52/57's realistic-error design (bias-corrected D, isolation and two-group H at the validated noise gates),
  run on GA, TX and AZ tract geometry from the ACS 2019–2023 counts.
- 2,000 draws per cell, with cells by state and noise bin; per-draw seeds `[20280901 + cell, draw]`.
- Pass: coverage ≥ .86 in every cell, as in Round 52.
- A failure narrows the validated scope; it does not change earlier results.

## Engine and docs

- No method changes are expected. If S fails, the gate tables gain a geometry note.
- Replication reports:
  - `docs/studies/r66_replication_chr_segregation.md`;
  - `docs/studies/r66_replication_state_gini.md`.
  
  Each states the pre-set rule, the result (replicated / partly / not), the differences and their explanation.
- STATUS (studies and methods rows), CHANGELOG, version, compatibility audit; tests (outcome flags equal the
  audit); goldens byte-identical.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| A spec and criterion | | |
| B spec and criterion | | |
| S criterion and run | | |
| A / B results | | |
| Reports, tests | | |
| Goldens, final suite | | |
| Exceptions | | |

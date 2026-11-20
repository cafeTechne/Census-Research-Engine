# Round 57 plan: segregation, remaining gaps

**Goal.** Backlog issues N30 and N33 (`ROADMAP_BACKLOG.md` Round 57).

Four gaps remain after Rounds 50–52:
- **Clipped counties above noise .50.** Clipped replicates (Round 51) are validated only below .50, so counties
  with a negative replicate stay exploratory above it, although Round 52 validated their unclipped counterparts.
  Race designs lose 11–32 of 145 MI/NY counties this way.
- **Six groups.** Six or more groups are exploratory.
- **Same-release county contrasts.** Contrasts between two counties of the same release (per-replicate
  differences) have no coverage experiment.
- **Group quarters.** Tracts dominated by group quarters (prisons, dormitories) drive the highest rural values.
  The engine has no way to leave them out.

Version 0.54.0. Baseline: v0.53.0 (2100 passed, 37 skipped). Branch `phase57/segregation-gaps`. Validation first.

## 1. Truth file (`scripts/segregation_r57_counts.py` → `docs/audits/segregation_r57_counts.csv.gz`)

From the cached 2024 B03002 MI/NY tract responses (read-only), byte-reproducible:
- white (003), black (004), asian (006), hisp (012);
- multi (009, two or more races) and other3 (005, 007, 008);
- nonblack (all components except 004) and nonhisp (002).

SEs are MOE/1.645, combined in quadrature for sums. Poverty contrasts use the frozen Round 50 counts file.

## 2. Validation (`scripts/segregation_gaps_validation.py` → `docs/audits/segregation_gaps_validation.md`/`.json`)

Round 52's bins: [0, .15), [.15, .30), [.30, .50), [.50, .75), [.75, 1), [1, ∞). Round 50's bin rule: a bin with
≥ 5 counties passes when, in both ρ cells, mean county coverage ≥ .86 and ≥ 90% of counties cover ≥ .80. Failed
draws count as non-coverage. 2,000 draws per cell; per-draw seeds `[20280301 + cell, draw]`.

**A. Clipped replicates (8 cells):** black2, hisp2, race4, race5 (Round 52 groups) × ρ ∈ {0, negative} (−.3;
−.2 for five groups).
- Round 50 observed counts. Gaussian replicates as in Round 51 (observed + (SE/2)·z, rounded, zero stays zero),
  clipped at zero before the refits.
- All Round 52 variants are judged.
- A bin also needs pooled affected-draw coverage ≥ .86 (county-draws in the bin with a clipped cell) when it has
  at least 500 such pairs.
- **Combination:** for two groups, a bin is clip-validated when every design judging it passes (Round 51's MI/NY
  poverty audit for the first three bins, black2, hisp2). Four and five groups use race4 and race5. Each clipped
  range is capped at the variant's unclipped range.

**B. Six groups (2 cells):** race6 = white, black, asian, hisp, multi, other3 × ρ ∈ {0, −.15} (−.3 and −.2 are
not positive definite for six groups). Round 50 Gamma model; H naive and bias-corrected.

**C. Same-release county contrasts (2 cells):** Round 50 MI/NY poverty counts × ρ ∈ {0, −.3}; Gamma model. Pairs
are consecutive counties in GEOID order within a state (68 pairs). The estimate is I_a − I_b; the SE comes from
per-replicate differences, √(4/80 Σ((I_ra − I_rb) − (I_a − I_b))²), as `segregation_test` computes it. The target
is the true difference. Pairs are binned by the larger noise level; all six two-group variants are judged.

## 3. Engine (only what passes)

- `CLIP_RANGES` extended by the combination outcome; new keys for four and five groups.
- `REALISTIC_RANGES` gains ("theil_h", variant, 6) if race6 passes.
- `SAME_RELEASE_CONTRAST_RANGES`: a same-release county contrast is validated only when both rows are validated and
  the larger noise level is inside the range.
- **Group quarters (a definitional option, no coverage claim of its own):**
  - `segregation_replicate(..., exclude_tracts=...)` drops the listed tracts before every refit and notes how
    many were dropped.
  - `census.segregation.group_quarters_tracts(frame, gq, total, max_share=.5)` lists tracts whose group-quarters
    share (B26001_001 / B01003_001) is at or above `max_share`.
  - Manifests use `args.group_quarters: {"gq": var, "total": var, "max_share": number}`; registered manifests are
    unchanged.
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit); goldens identical.
- **Exploratory MI/NY example:**
  - Round 52's Black–non-Black and four-group designs with the new clipped ranges (how many more counties are
    validated);
  - the same with group-quarters tracts (share ≥ .5) excluded, showing Wyoming, Greene and Chippewa;
  - six-group H;
  - one same-release contrast (Wayne vs Oakland).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Truth file, script, criterion commit | | |
| A / B / C results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

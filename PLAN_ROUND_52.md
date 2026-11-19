# Round 52 plan: segregation beyond poverty and income

**Goal.** Backlog issue N21 (`ROADMAP_BACKLOG.md` Round 52).

Rounds 50–51 validated the segregation indices with poverty (two groups) and household income (three
groups) in MI/NY. Not tested:
- race and ethnicity groups, which are much sparser (most MI/NY counties have a noise level above .50 for
  Black or Hispanic residents, outside every validated range);
- four and five groups (Theil H; exploratory today);
- contrasts between two non-overlapping five-year periods (`segregation_test` with `release`/`compare_release`);
- counties outside MI/NY.

Version 0.49.0. Baseline: the Round 51 suite (2066 passed, 37 skipped). Branch `phase52/segregation-groups`.
Validation first.

## 1. Truth file (`scripts/segregation_groups_counts.py` → `docs/audits/segregation_groups_counts.csv.gz`)

Built from the cached API responses (read-only, no network; fetched with the owner's key before the plan), gzip
with mtime 0, byte-reproducible. One row per (release, tract); per group the published count and SE (MOE/1.645;
sums of lines combine SEs in quadrature):
- **2024, MI/NY/OH/PA, B03002:** white (003), black (004), asian (006), hisp (012), other (005, 007, 008, 009:
  non-Hispanic AIAN, NHPI, other, two or more), nonblack (every component except 004), nonhisp (002); **B17001:**
  below (002), above (031).
- **2019 (2015–2019), MI/NY, B17001:** below, above (2010 tract geography; the county index is compared, not tracts).

## 2. Validation (`scripts/segregation_groups_validation.py` → `docs/audits/segregation_groups_validation.md`/`.json`)

Round 50's machinery, imported from the frozen `scripts/segregation_realistic_validation.py`: Gamma-copula
observed counts and replicates (SD = SE and SE/2), rounding, `_indices`, SE and bias correction; counties with
fewer than five populated tracts excluded.

**Designs** (pre-run counties per noise bin [0, .15), [.15, .30), [.30, .50), ≥ .50):

| Design | Release, states | Groups | Counties | Pre-run bins |
| :--- | :--- | :--- | ---: | :--- |
| black2 | 2024 MI/NY | black, nonblack | 137 | 0 / 2 / 20 / 115 |
| hisp2 | 2024 MI/NY | hisp, nonhisp | 137 | 0 / 14 / 83 / 40 |
| race4 | 2024 MI/NY | white, black, hisp, other + asian | 137 | 0 / 0 / 17 / 120 |
| race5 | 2024 MI/NY | white, black, asian, hisp, other | 137 | 0 / 0 / 4 / 133 |
| pov_ohpa | 2024 OH/PA | below, above | 146 | 0 / 79 / 67 / 0 |
| black2_ohpa | 2024 OH/PA | black, nonblack | 146 | 0 / 3 / 14 / 129 |
| contrast | 2024 minus 2019, MI/NY | below, above | counties in both | binned by the larger of the two noise levels |

**Bins.** Round 50's three bins plus finer bins above .50: [0, .15), [.15, .30), [.30, .50), [.50, .75),
[.75, 1.0), [1.0, ∞) (a zero median count gives an infinite CV).

**Cells (14).** 7 designs × ρ ∈ {0, −.3}; 2,000 draws per cell; seed `20271001 + cell`.

**Procedures.** Two groups: D, isolation and H, each naive and bias-corrected (all six judged, as in Round 50).
Four and five groups: H naive and bias-corrected. Contrast: the three two-group indices in both variants;
estimate = I₂₀₂₄ − I₂₀₁₉ (each with its own draws and replicates), SE = √(SE₂₀₂₄² + SE₂₀₁₉²) (independent
samples, as `segregation_test` does), target = the difference of the true indices.

**Acceptance per design.** Round 50's rule unchanged on the new bins: a bin with ≥ 5 counties passes when, in both
ρ cells, mean county coverage ≥ .86 and ≥ 90% of its counties cover ≥ .80. Failed draws count as non-coverage.

**Engine range (pre-set combination rule, group-type blind).** The engine cannot tell race groups from poverty
groups, so for each (index, variant, number of groups) a bin is validated when **every** design with that group
count that judges the bin passes it, and at least one does. For two groups the designs are Round 50's poverty
(MI/NY, its bins and outcomes as audited), black2, hisp2, pov_ohpa and black2_ohpa; four groups race4; five groups
race5; three groups stay at Round 50. The validated range runs from the lowest validated bin up to the first bin
that fails or that no design judges. Round 50's engine lower bound .15 for variants that failed Round 28 is kept.
The contrast range is set the same way from the contrast design alone (bins by the larger noise level).

## 3. Engine (only what passes)

- `REALISTIC_RANGES` updated by the combination rule (may narrow or widen two-group ranges); new keys for four and
  five groups if their H passes; `MAX_VALIDATED_MEDIAN_CV` follows. Six or more groups stay exploratory.
- `CLIP_RANGES` (Round 51) keep their upper end of .50 (clipping was not tested above .50) but are narrowed if the
  new two-group range is narrower.
- `segregation_test` across releases: validated only when both rows are validated and the larger noise level is
  inside `CONTRAST_RANGES`; otherwise the confirmatory test is refused. Same-release county contrasts unchanged
  (not in this design).
- Rule text mirrored (agent protocol, segregation recipe, MCP core item 13 and full text); STATUS, CHANGELOG,
  version, compatibility audit; tests that engine flags equal the audit; goldens byte-identical.
- **Exploratory MI/NY example:** 2024 Black–non-Black and Hispanic–non-Hispanic segregation and four-group H by
  county from the B03002 VRE files (downloaded to the cache), showing how many counties fall in the validated
  range, plus the 2019–2024 poverty-segregation change for the counties where the contrast is validated (B17001
  2019 VRE from the cache).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Truth file, script, criterion commit | | |
| Results by design and bin | | |
| Combined ranges | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

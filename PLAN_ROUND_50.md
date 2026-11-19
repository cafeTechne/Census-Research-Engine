# Round 50 plan: segregation with realistic sampling error

**Goal.** STATUS backlog item 6 (`ROADMAP_BACKLOG.md` Round 50).

Round 28 validated county segregation indices only when every tract group count had a CV of .15. With
a CV of .30 every index failed (.39–.45, with many invalid draws from negative counts). The engine
therefore refuses any county whose largest tract CV exceeds .15, and no real MI/NY county meets that.
Multigroup Theil H was never tested.

This round validates the indices under realistic error:
- the published tract MOEs (heterogeneous CVs);
- non-negative counts and replicates;
- correlated group errors.

It also sets a CV gate that real counties can meet, if any range passes.

Version 0.47.0. Baseline: the Round 49 suite. Branch `phase50/segregation-realistic`. Validation first.

## 1. Validation (`scripts/segregation_realistic_validation.py` → `docs/audits/segregation_realistic_validation.md`/`.json`)

**Truth.** The real 2024 five-year tract counts of MI/NY are treated as the truth. They are read from
the cached API responses (read-only, no network) and frozen as a compact counts file before the run:
- **Two groups:** below poverty (B17001_002) vs at or above (B17001_031, equal to 001 − 002, with its own
  published MOE).
- **Three income groups:** B19001 bands <$35k, $35k–99k, $100k+ (summed bands; their SEs combined in
  quadrature).

Per-tract, per-group error SDs are the published MOE/1.645.

Counties with fewer than five tracts are excluded and reported. The target is each county's index on
the true counts.

**Observation model.**
- Each observed count is a Gamma draw with mean = truth and SD = the published SE, generated through a
  Gaussian copula with correlation ρ between the groups of a tract. Counts are therefore non-negative.
  A true zero stays zero, a documented simplification.
- The 80 replicates are Gamma draws with mean = the observed count and SD = SE/2 (so that the
  4/80 replicate formula estimates SE²; corrected from "SD = the SE" after the smoke run), from the
  same copula. Draws are rounded to whole counts, as ACS estimates are. They are non-negative, and their 4/80 variance has ACS-like noise.

**Cells (4).** {two groups, three groups} × ρ ∈ {0, −.3}. 2,000 draws per cell; seed `20270801 + cell`.

**Procedures.** These are the engine's estimators, called on the arrays through `census.segregation`'s
index function (frozen) and the same SE and bias-correction formulas as `segregation_replicate`:
- D naive.
- Isolation bias-corrected.
- Two-group H bias-corrected, plus H naive for comparison.
- Multigroup H bias-corrected and naive (three-group cells).

**Acceptance.**
- Each county's **noise level** is the largest, over groups, of the median tract CV of that group (from
  the published SEs; a zero estimate has CV ∞). A pooled median would be dominated by the large group
  (below .30 in every MI/NY county). Counties are binned by noise level: [0, .15), [.15, .30), [.30,
  .50), [.50, ∞). Pre-run tally (MI/NY, ≥ 5 tracts): two groups 0 / 88 / 49 / 0; three groups
  9 / 117 / 11 / 0.
- An index passes a bin if mean county coverage ≥ .86 **and** at least 90% of the bin's counties
  cover ≥ .80, in both ρ cells. Bins with fewer than five counties are not judged.
- The validated range runs from the lowest bin up to the first failing judged bin.
- Failed draws (undefined indices) count as non-coverage.

## 2. Engine (only what passes)

- **Gate:** `segregation_replicate` gains a noise-level gate (`MAX_VALIDATED_MEDIAN_CV`, the same
  definition computed from the replicate SEs) per index,
  replacing the Round 28 max-CV gate where the new validation passes. The old gate stays for indices
  that do not pass. Multigroup H becomes validated in the passing range.
- **Manifests:** registered manifests keep their behaviour. The run golden must stay byte-identical.
  If a golden case uses segregation, its validation flag may change; that change is documented as the
  only allowed difference.
- **Shared steps:**
  - Mirror the rule text in the agent protocol, the recipe and the MCP text.
  - Update STATUS and the CHANGELOG.
  - Add tests that check the engine flags equal the audit.
  - Run the full suite.
- **Exploratory MI/NY example:** county poverty segregation with the new gate, showing how many
  counties are now in the validated range.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Counts file, criterion commit | | |
| Results by CV bin | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

# Round 51 plan: negative replicate estimates (segregation and SMR)

**Goal.** Backlog issues N20 and N28 (`ROADMAP_BACKLOG.md` Round 51).

The 2024 tract VRE files contain negative replicate estimates for small cells (B17001: 7 NY rows; B19001:
175 MI and 481 NY rows). Two engine paths refuse them outright:
- `segregation_replicate` refuses any county with a negative group-count replicate (Round 50 example: five
  counties per design, including the Bronx, Kings and Wayne).
- `indirect_standardize` (SMR) refuses any negative band replicate, although the expected count is linear in
  the band populations, so a negative band replicate is harmless when every replicate expected count is
  positive.

This round validates two policies and adopts the ones that pass:
- **Segregation, `clip`:** replicate group counts below zero are set to zero before the index refits. The
  count SEs and noise level still use the unclipped replicates.
- **SMR, `accept`:** negative band replicates are used as published; every replicate expected count must be
  positive (else refused, as now). **SMR, `clip`** is judged for comparison.

Version 0.48.0. Baseline: the Round 50 suite (2058 passed, 37 skipped). Branch `phase51/negative-replicates`.
Validation first.

## 1. Frozen core

`census/standardize.py`: `indirect_standardize(..., negative_replicates="refuse")` with `"refuse"` (today's
behaviour, the default during the run), `"accept"` and `"clip"`. `census/segregation.py` is unchanged before
the run (the simulation clips with `np.maximum(cube, 0)` around the frozen `_indices`). Both files and the
script and criterion are pinned (`validate_pins`).

## 2. Validation A: segregation (`scripts/negative_replicates_validation.py` → `docs/audits/negative_replicates_validation.md`/`.json`)

**Truth and observed counts.** As Round 50: the frozen `docs/audits/segregation_realistic_counts.csv.gz`
(2024 MI/NY tracts; counties with ≥ 5 populated tracts), observed counts are rounded Gamma-copula draws with
mean = truth, SD = published SE, group correlation ρ.

**Replicates (the change).** Gaussian, not Gamma: replicate = observed + (SE/2)·z with z from the same
Gaussian copula (correlation ρ between the groups of a tract), rounded to whole counts. A zero observed count
keeps zero replicates (as in the ACS). Gaussian deviations produce negative replicates at small counts, far
more often than the real files do (a stress test). The run reports the share of tract-group cells with at least
one negative replicate.

**Cells (4).** {two groups (poverty), three groups (income)} × ρ ∈ {0, −.3}; 2,000 draws per cell; seed
`20270901 + cell`.

**Procedures (all clipped).** The eight Round 50 variants: two groups D, isolation and H, each naive and
bias-corrected; three groups H naive and bias-corrected. SE = √(4/80 Σ(I_r − I)²) from clipped refits; bias
correction I − 4(mean I_r − I).

**Acceptance.** Round 50's rule unchanged: counties binned by noise level [0, .15), [.15, .30), [.30, .50),
[.50, ∞); a judged bin (≥ 5 counties) passes when, in both ρ cells, mean county coverage ≥ .86 and ≥ 90% of its
counties cover ≥ .80; validated range from the lowest bin to the first failing judged bin. **Plus** an
affected-draw check per variant: over all (county, draw) pairs in the validated range where at least one
replicate cell was clipped, pooled coverage ≥ .86 in both ρ cells (not judged if fewer than 500 such pairs).
Failed draws count as non-coverage. Clipping is validated for a variant when it has a validated range and the
affected-draw check passes (or is not judged); the engine uses the smaller of that range and its Round 50 range.

## 3. Validation B: SMR (same script, separate section)

Five age bands with the Round 24 reference rates (.0005, .001, .003, .01, .04 per person-year) and equal true
populations scaled to expected count E. One **high-CV band** has CV c; the others have CVs .05.

**Cells (8).** E ∈ {10, 100} × high-CV band ∈ {band 1 (≈1% of E), band 4 (≈18% of E)} × c ∈ {.6, 1.0};
2,000 draws per cell; seed `20270911 + cell`.

**Per draw.** Observed band populations are Gamma (mean = truth, SD = CV × truth); replicates Gaussian with
SD = SE/2 around the observed (independent bands; not rescaled, so the 4/80 variance has ACS-like noise);
deaths O ~ Poisson(1.2 E_true). Target: SMR 1.2.

**Procedures.** `indirect_standardize(..., negative_replicates="accept")` and `"clip"`; combined 90% interval.
Refused draws (nonpositive replicate expected count) and O = 0 count as non-coverage.

**Acceptance.** A policy passes when coverage ≥ .86 in all eight cells. The report also gives the share of
draws with a negative band replicate per cell (must be > 0 in the c = 1.0 cells for the test to be informative).

## 4. Engine (only what passes)

- **Segregation:** `segregation_replicate(..., negative_replicates=None)`; `None` means the validated policy
  (`"clip"` if validation A passes, else `"refuse"`). Notes give the number of clipped replicate cells.
  `NEGATIVE_REPLICATE_RANGES` per variant (the clipped ranges); a county with clipped cells is validated only
  inside them. Strict refusal stays available (`"refuse"`).
- **SMR:** `indirect_standardize(..., negative_replicates=None)`; `None` means `"accept"` if validation B
  passes for `accept`, else `"refuse"`. A note gives the count of negative band replicates.
- **Manifests:** registered manifests keep their behaviour: the manifest methods pass `"refuse"` unless the
  manifest opts in with `args.negative_replicates` (`segregation`, `smr`). Run golden byte-identical; schema
  golden changes only by the new optional argument if it is in the schema (documented).
- **MCP:** segregation and SMR tools accept `negative_replicates`; core text one line.
- **Shared steps:** mirror the rule in `docs/agent_protocol.md`, the segregation and SMR recipes and the MCP
  text; STATUS, CHANGELOG, version, compatibility audit; tests that the engine flags equal the audit.
- **Exploratory MI/NY example:** Round 50's poverty and income segregation on the real VRE files with the
  validated policy: how many of the ten refused counties are now estimated and validated, and how much their
  SEs change compared with dropping the affected tracts.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | SMR policy argument frozen; `2837bfb` (`.venv` symlink untracked in `e236fee`) |
| Results A (segregation) | done | clip passes for bias-corrected D/I/H and 3-group H to .50 (affected .902–.990); naive I/H fail affected draws (`5d1f0f6`) |
| Results B (SMR) | done | accept .903–.922, clip .891–.917; both pass |
| Engine, manifests, MCP, tests | done | defaults clip / accept; manifests opt in; 8 new tests, 2 older tests pass `"refuse"` |
| Example | done | all ten refused county-designs validated; `/tmp/r51_example_outputs.tar.gz` |
| Goldens, final suite | done | identical; 2066 passed, 37 skipped |
| Exceptions | see notes | clip-validated rule reworded before freezing (smaller of clipped and Round 50 range); stale Round 28 text in `mcp_server.py` corrected |

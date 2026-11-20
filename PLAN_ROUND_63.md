# Round 63 plan: small samples and many covariates

**Goal.** Backlog issues N35 and N36 (`ROADMAP_BACKLOG.md` Round 63). Both are recorded limits; this round attempts
them and records the outcome either way.

- **N35.** No interrupted-series method is validated below 20 annual points. Round 55's bias-corrected bootstrap-t
  covered .857 at 15 points (slope change, φ .6).
- **N36.** Spatial EIV (G1/G2) with six error-prone covariates failed at reliability .7 with correlated fields
  (.804–.811). Round 58 showed that a reliability gate (every covariate ≥ .8) restores three to five covariates on
  both geometries.

Version 0.60.0. Baseline: the Round 62 suite (2132 passed, 37 skipped). Branch `phase63/small-samples-covariates`.
Validation first.

## 1. Frozen core (`census/its_small_core.py`, new functions)

- **I6: `its_bootstrap_t_cons`.** Round 55's I3 (bias-corrected bootstrap-t), with each critical value the larger of
  the bootstrap-t quantile and the t(n − p − 1) quantile, side by side. This is a conservative floor for very short
  series.
- **I7: `its_bootstrap_t_bb`.** Like I3, but the AR coefficient used to generate the bootstrap series is
  bias-corrected by a first-level parametric bootstrap instead of Kendall's formula:
  - 199 series at φ̂ give φ_bb = min(.95, 2φ̂ − mean φ̂*);
  - the 499-resample bootstrap-t then runs at φ_bb.

## 2. Validation (`scripts/small_many_validation.py` → `docs/audits/small_many_validation.md`/`.json`)

2,000 draws per cell; per-draw seeds `[20280801 + cell, draw]`.

**I (6 cells).** Round 48/55's generator (level change 1, slope change .2, AR(1) errors) with n ∈ {15, 17, 19} × φ ∈
{.3, .6}. Procedures: I3 (Round 55, comparison), I6, I7. A procedure is validated down to the smallest n at which
both changes cover ≥ .86 for both φ, and at every larger tested n. Its validation at 20+ points rests on I3's Round 55
result for I6 (which is never narrower than I3). I7 counts only below 20 points.

**G (24 cells).** G1 and G2 with p ∈ {6, 7, 8} error-prone covariates × reliability {.8, .9} × geometry {MI/NY,
OH/PA} × range {0, 100} km. Round 58's G generator: state indicator, the geometry's fixed eight clusters, target
.5. G1 or G2 is validated for p under the reliability gate when it covers ≥ .86 in every cell for that p. The gated
cap is the largest p with every smaller tested p also passing. Failed fits count as non-coverage.

## 3. Engine (only what passes)

- **N35:** `interrupted_series(method="bootstrap_t_cons" | "bootstrap_t_bb")` with `ITS_*_MIN_N` from the audit.
  Below the validated n, results stay exploratory with a note. If nothing passes, N35 is confirmed as a limit.
- **N36:** `spatial_eiv.GATED_MAX_ERROR_COVARIATES`: with more than five error-prone covariates, a fit is validated
  only when every estimated reliability is ≥ .8 and p is at most the gated cap. Otherwise the note stays.
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit); goldens identical.
- **Demonstration:** a simulated 17-point series with each method, labelled a demonstration, as in Round 55.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | | |
| I / G results | | |
| Engine, tests | | |
| Demonstration | | |
| Goldens, final suite | | |
| Exceptions | | |

# Round 59 plan: correlations under spatial dependence

**Goal.** Backlog issues N29 (partial correlations) and N31 (Round 48's designs on OH/PA) (`ROADMAP_BACKLOG.md`
Round 59).

Round 48 validated effective-sample-size intervals for Spearman, Kendall and Pearson correlations and Feldt's α
under spatial dependence, on the MI/NY geometry only. Two gaps remain:
- **Partial correlations** were left exploratory: the engine refuses a spatial correction for them.
- **OH/PA** was never checked. The Round 33 and 36 reference targets were computed on MI/NY, so the designs could not
  simply be re-run there (Round 54 left this open).

This round adds a partial-correlation version and recomputes the targets for OH/PA.

Version 0.56.0. Baseline: the Round 58 suite (2112 passed, 37 skipped). Branch `phase59/spatial-correlations`.
Validation first.

## 1. Frozen core and targets

- New `census/partial_neff_core.py`: `partial_neff(x, y, z, cls, reps_x, reps_y, reps_z, level)`.
  - Residualise x and y on [1, z].
  - n_eff is the Clifford–Richardson–Hemon effective size of the two residual series (`small_spatial_core.effective_n`).
  - var(atanh r) = 1/(n_eff − 3 − k) plus the Round 33 replicate variance term (variant 2); k is the number of
    controls.
  - Normal interval on the atanh scale.
- `scripts/spatial_correlation_validation.py --prepare` writes `docs/audits/ohpa_correlation_targets.json` before
  the run (no network). It holds Round 33's observed-value coefficient targets and Round 36's α targets, recomputed
  for the OH/PA cells:
  - the same procedures, seeds and 400,000-area reference;
  - the cell constants (area SEs, groups) drawn on the 155 OH/PA areas exactly as the Round 33 and 36 `setup`
    functions do on MI/NY.

## 2. Validation (`scripts/spatial_correlation_validation.py` → `docs/audits/spatial_correlation_validation.md`/`.json`)

2,000 draws per cell; per-draw seeds `[20280501 + cell, draw]`.
- **P (8 cells): partial correlations on MI/NY.** Round 33 cells (ρ ∈ {0, .4} × reliability {.9, .7} × range
  {0, 100} km), Round 48's draw (lognormal fields, ACS error, replicates).
  - P1 = `partial_neff` with the replicate term.
  - P0 = Round 33's independent-area partial interval (comparison).
  - Target: Round 33's observed partial coefficient.
- **O (8 cells): Round 48 correlations on OH/PA.** The same cells on the OH/PA geometry:
  - C1 for Spearman, Kendall (no replicates) and Pearson (with replicates);
  - P1 for the partial correlation.
  - Targets from the new file.
- **A (8 cells): Round 48 α on OH/PA.** Round 36 cells (reliability {.9, .7} × range {0, 100} × PCA/equal
  weights). A3 is Feldt's interval with the effective n of the total score. Targets from the new file.

**Acceptance.** Coverage ≥ .86 in every cell of the problem: P1 over P and O together (both geometries); C1 per
method over O; A3 over A. Failed fits count as non-coverage.

## 3. Engine (only what passes)

- If P1 passes, `NEFF_CORRELATION_VALIDATED["partial"]` becomes true, and
  `correlation.validated_correlations(method="partial", coords=...)` uses `partial_neff` (one control, with
  replicates, as Round 33 validated). MCP `correlation_matrix(spatial=True)` covers partial correlations.
- C1/A3 on OH/PA: a procedure that passes is "replicated on OH/PA (Round 59)" in notes and docs. One that fails
  keeps its MI/NY validation and gets a note for areas outside MI/NY.
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit, `partial_neff` by
  hand); goldens identical.
- **Exploratory example:** OH/PA county child poverty and unemployment, partial on log income, with and without
  the spatial correction (Round 54's frame).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, targets, script, criterion commit | | |
| P / O / A results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

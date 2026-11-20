# Round 53 plan: corrected GLM slopes, part 2

**Goal.** Backlog issues N22 and N23 (`ROADMAP_BACKLOG.md` Round 53).

Round 46 validated regression calibration (RC) for Poisson and NB2 slopes, not binomial, and only for
independent areas. Its audit shows the binomial failure is in the **standard error, not the point estimate**:
RC bias was −.016 to −.001, but coverage was .851–.889, lowest at reliability .9, where the correction is small.
The RC SE comes from a 200-resample row bootstrap, which behaves like an HC0 sandwich. HC0 under-covers with
145 areas and the extreme leverage of binomial weights, because trials vary 50-fold and overdispersion is on the
logit scale. The naive comparison used HC3. So this round changes the variance estimator before trying a new
estimator; the roadmap's likelihood-based correction is not needed while bias is negligible.

Three problems:
- **J (independent areas):** RC with a delete-one-area jackknife SE (each of the n refits re-estimates the
  calibration; the jackknife variance ≈ HC3), t reference with n − p df, for binomial, Poisson and NB2. Round
  46's audit is the bootstrap comparison (same generator).
- **S (spatial dependence):** RC with IM-8 clusters for Poisson and NB2 under spatially correlated fields. The
  calibration E[X | W] is pooled over all areas, the GLM is fitted per cluster on the calibrated covariates, and
  the eight cluster slopes are combined with a t(7) reference (as Round 35's G1 for linear EIV).
- **M (more covariates):** spatial EIV G1/G2 with five and six error-prone covariates (Round 46's M design).

Version 0.50.0. Baseline: the Round 52 suite. Branch `phase53/glm-correction-2`. Validation first.

## 1. Frozen core

`census/models.py`: `regression_calibration(..., se_method="bootstrap")` gains `"jackknife"` (delete-one-area
refits including calibration; variance (n−1)/n Σ(b₍ᵢ₎ − b̄)²; t(n − p) intervals). New
`census/rc_spatial_core.py`: `rc_im(y, W, se, Z, exposure, labels, family)` for problem S: pooled calibration
with the engine's `_calibrate`, then the frozen Round 45 `count_repairs_core.im_counts` on the calibrated
covariates (per-cluster Poisson/NB2, IM t(G − 1)). Pinned with `census/models.py` and the Round 45 core.

## 2. Validation (`scripts/glm_correction2_validation.py` → `docs/audits/glm_correction2_validation.md`/`.json`)

**J cells (12):** Round 46's R design unchanged (`scripts/glm_correction_validation.py` `r_cell` generator:
binomial/Poisson/NB2 × reliability {.9, .7} × error correlation {0, .3}; 145 areas, replicate-estimated SEs;
target the true slope .3). Procedure: **J1** RC jackknife (engine). The bootstrap comparison is Round 46's audit.

**S cells (8):** {Poisson, NB2} × reliability {.9, .7} × field range {0, 100} km; MI/NY geometry and the fixed
IM-8 assignment (`docs/audits/im_acs_beta_star.json`); x₁, x₂ from the Round 22 spatial field generator (corr .5),
per-area error SEs lognormal scaled to the reliability, replicate-estimated SEs; E lognormal (median 30);
log-rate .3x₁ + .3x₂ + .3·NY + .15 × spatial error field, times Gamma(4) noise for NB2. Procedures: **S1**
`rc_im`; **S0** naive IM-8 on the observed covariates (`im_counts`; comparison). Target .3 on x₁.

**M cells (8):** Round 46's M design with p ∈ {5, 6} × reliability {.9, .7} × range {0, 100} km; G1, G2 (frozen
`census.spatial_eiv_core`). Target .5 on x₁.

2,000 draws per cell; seed `20271101 + cell`. **Acceptance:** coverage ≥ .86 in every cell of the problem, per
procedure and model (J1 per model; S1 per model; G1, G2 per p). Failed fits count as non-coverage. Mean bias
and failed fits are reported.

## 3. Engine (only what passes)

- J: if J1 passes for binomial, `RC_VALIDATED["binomial"]` becomes true **for `se_method="jackknife"` only**
  (`RC_VALIDATED_SE`); manifests and MCP accept `se_method`; binomial RC with the bootstrap stays refused. If J1
  passes for Poisson/NB2 it is offered as an alternative (default unchanged).
- S: `regression_calibration(..., spatial="clusters", labels=...)` (or the count-model route) for Poisson/NB2 if
  S1 passes; otherwise exploratory with a note.
- M: `spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES` raised to the largest p that passes.
- Mirror rule text; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit); goldens identical.
- **Exploratory MI/NY example:** county child poverty rate (binomial) on median household income and
  unemployment rate (both error-prone), naive vs RC jackknife (the example Round 46 dropped).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | `8d48956` |
| J / S / M results | done | J1 passes all three GLMs; S1 passes Poisson/NB2; G1/G2 pass p = 5, fail p = 6 (`11e526b`) |
| Engine, tests | done | `RC_VALIDATED_SE`, `calibrate=`, cap 5, MCP `se_method`; 7 new tests, Round 46 tests updated |
| Example | done | child poverty; jackknife SEs ~40–50% wider than bootstrap; `/tmp/r53_example_outputs.tar.gz` |
| Goldens, final suite | done | identical; 2082 passed, 37 skipped |
| Exceptions | see notes | J0 dropped (Round 46 audit is the comparison); `fit_eiv` method text left at "four" (goldens) |

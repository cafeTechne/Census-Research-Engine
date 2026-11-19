# Round 44 plan: post hoc sensitivity of Round 29 and an OH/PA re-check of the spatial validations

**Goal.** Two checks found necessary in Rounds 31–42 (`ROADMAP_BACKLOG.md` N11, N15; STATUS backlog 2):

- **A.** Round 29's registered mortality models used Poisson with HC3, which under-covered with strong
  overdispersion in Round 39. Refit H1–H3 with the validated NB2-HC3 model (MI/NY and the OH/PA
  replication), plus an exploratory interval-censored check of H2's hidden counts.
- **B.** Every spatial validation used the 145 MI/NY counties. Re-run the Round 30 (IM-8, observed-estimate
  target) and Round 35 (corrected slopes G1/G2) designs on the 155 OH/PA counties.

Post hoc, author self-review, not independent. **Registered results are unchanged** and are reported
alongside. Version 0.41.0. Baseline: 1993 passed, 37 skipped. Branch `phase44/posthoc-replication`.

## A. Round 29 post hoc (`scripts/r44_posthoc_r29.py` → `docs/studies/r44_posthoc_r29.md`)

Inputs: the released `r29_study_outputs.tar.gz` (SHA-256 recorded), loaded with the Round 30 verifier
(`scripts/r30_posthoc_im_acs.load_verified`: manifest hash and every file checksum); network blocked.

| ID | Model for each of H1–H3 (`<h>_numerator ~ poverty + C(GEOID.str[:2])`, offset log E_h) | Status |
| :--- | :--- | :--- |
| P0 | Poisson HC3, population target (the registered family without replicate variance: a like-for-like baseline for P1) | comparison |
| P1 | NB2-HC3, population target (validated, Round 39) | sensitivity |
| P2 | H2 only: interval-censored Poisson, suppressed counties as counts in [1, 9] (Round 42, failed narrowly) | exploratory |

- One-sided ("greater") p-values, Holm across H1–H3 within P0 and within P1, as registered; "holds" means
  Holm p < .10.
- **Pre-set reading.** If every hypothesis that held as registered also holds under P1, the Round 39
  caveat does not change Round 29's conclusions. A hypothesis that held as registered but not under P1 is
  reported as "sensitive to overdispersion" in STATUS and the Round 29 study note (registered result kept).
- Outputs: coefficients, SEs, p-values and NB2 alpha only. `census.wonder_outputs.audit_outputs` must pass
  on every output; no county values, no hidden-count estimates.

## B. OH/PA re-check (`scripts/ohpa_spatial_revalidation.py`; frozen with the criterion)

- **Geometry** (`docs/audits/ohpa_geometry.json`, prepared and committed before the run): the 155 OH (39)
  and PA (42) counties from cached 2020 cartographic boundaries, representative points via
  `unit_coordinates` (network blocked). **State-respecting assignment:** `cluster_points` (seed 20261126)
  within each state, 4 clusters each, so no cluster mixes states (MI/NY clusters never did: the states are
  far apart; OH and PA share a border, where a pooled k-means could mix them and leave the state term
  partially constant). The state indicator is PA.
- **C1 (Round 30):** the 12 cells (linear/binomial/Poisson × range 0/100 km × reliability .9/.7) with the
  frozen `census.im_acs` functions; the observed-estimate targets (beta*) are recomputed for this geometry
  by the Round 30 reference procedure (400,000 areas) and stored in the geometry file.
- **G1/G2 (Round 35):** the 8 cells (reliability .9/.7 × range 0/100 km × error correlation 0/.3) with the
  frozen `census.spatial_eiv_core`; target: the true slope 0.5.
- Seeds and draws as the originals (2,000 per cell; `SEED + cell`).
- **Criterion (unchanged):** 90% coverage ≥ .86 in every cell, per candidate (C1 per model); failed fits
  count as non-coverage. A method passing here "replicates on OH/PA"; one failing keeps its MI/NY
  validation but gets an engine note naming the OH/PA failure.
- Not re-run: Round 33 (only its independent-area cells passed, and those do not depend on geography) and
  Round 39 (independent areas).

## C. Engine and docs

Notes in `census/spatial_eiv.py` and the IM-8 notes recording the OH/PA result; STATUS validation rows,
studies table, backlog (N17: pooled k-means clusters can straddle adjacent states, leaving state terms
partially constant, which the engine refuses: use state-respecting clusters for adjacent-state studies;
a library option is backlog). Tests: geometry file checks (155 counties, 8 single-state clusters), outcome
flags equal the audit, post hoc output passes the WONDER audit. Recipe `external_health_outcome` notes
the P1 result. CHANGELOG, version 0.41.0, goldens unchanged, full suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `09ecd91` | Pushed before both runs. |
| A. R29 P0/P1/P2 | Done | H1–H3 hold under NB2 in both regions; P2 as complete case. |
| B. C1 / G1 / G2 on OH/PA | Done | G1/G2 replicate; C1 fails in spatial cells. |
| Engine notes, tests | Done | geography_notes; NB2 fallback; 6 tests. |
| Goldens, final suite | Done | Identical; 1999 passed, 0 failures. |
| Exceptions | Recorded | NB2 BFGS non-convergence stopped the first post hoc run before output; optimizer fallback. |

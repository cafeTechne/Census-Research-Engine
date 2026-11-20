# Round 54 plan: OH/PA external validity, part 2, and an IM-8 repair outside MI/NY

**Goal.** Backlog issues N19 and N24 (`ROADMAP_BACKLOG.md` Round 54).

Rounds 45–53 validated several spatial procedures on the MI/NY county geometry only:
- IM-8 count slopes (Round 45);
- G1/G2 with three to five error-prone covariates (Rounds 46 and 53);
- calibrated IM-8 count slopes (Round 53).

Round 44 found that naive IM-8 (Round 30 C1) fails on OH/PA when the fields are spatially correlated
(.70–.85). It replicates in MI/NY, whose states are far apart; OH and PA share a long border, so neighbouring
clusters are correlated. No repair was tried.

This round:
- re-runs the geography-dependent designs on the 155 OH/PA counties (Round 44 geometry and state-respecting
  clusters);
- tests IM with fewer, larger within-state clusters (G = 4 and 6) as a repair for naive IM-8, on **both**
  geometries.

Not covered: Round 48's effective-n correlations and α. Their reference targets were computed on the MI/NY
geometry and would have to be recomputed for OH/PA; recorded as a remaining gap. Independent-area designs
(censored NB2, noisy offsets, regression calibration J, causal tools) do not depend on geography.

Version 0.51.0. Baseline: the Round 53 suite (2082 passed, 37 skipped). Branch `phase54/ohpa-revalidation-2`.
Validation first.

## 1. Geometry file (prepared and committed before the run)

`docs/audits/im_cluster_counts_geometry.json`, from `scripts/ohpa_revalidation2.py --prepare`, no network:
within-state `census.spatial_clusters.cluster_points` assignments with 2 and 3 clusters per state (G = 4, 6) for
MI/NY (coordinates of `docs/audits/im_acs_beta_star.json`) and OH/PA (`docs/audits/ohpa_geometry.json`). Every
cluster must have at least five counties. The G = 8 assignments are the existing ones (MI/NY Round 30; OH/PA
Round 44).

## 2. Validation (`scripts/ohpa_revalidation2.py` → `docs/audits/ohpa_revalidation2.md`/`.json`)

2,000 draws per cell; per-draw seeds `[20271201 + cell, draw]`; cell constants from `20271201 + cell`.

- **C (24 cells): naive IM repair.** The Round 30 C1 cells (linear/binomial/Poisson × range {0, 100} km ×
  reliability {.9, .7}; generator `scripts/im_acs_validation.py` `setup`/`outcome`, imported) on MI/NY and
  OH/PA. Procedures: IM with G = 4, 6 and 8 (`census.im_acs` `cluster_coefficients`/`summarize`, t(G − 1))
  on the same draw. Target: the observed-estimate β* (MI/NY `im_acs_beta_star.json`, OH/PA
  `ohpa_geometry.json`).
- **K (4 cells): Round 45 IM-8 counts on OH/PA.** median E {10, 30} × range {0, 100}; Round 45's K2
  generator (x = Lz, spatial error .3·Lz, Gamma(4) noise, .2·PA); K2a NB2 and K2b Poisson `im_counts` with the
  OH/PA G = 8 assignment. Target .3.
- **S (8 cells): Round 53 calibrated counts on OH/PA.** Round 53's S design (Poisson/NB2 × reliability
  {.9, .7} × range {0, 100}); S1 `rc_im`, S0 naive `im_counts`. Target .3.
- **M (12 cells): G1/G2 with p ∈ {3, 4, 5}** × reliability {.9, .7} × range {0, 100} on OH/PA; Round 53's M
  generator with the PA indicator. Target .5.

**Acceptance.** Coverage ≥ .86 in every cell of the problem, per procedure and model (C per G across all 24
cells, i.e. both geometries; K2a, K2b; S1 per model; G1, G2 per p). Failed fits count as non-coverage.

## 3. Engine (only what passes)

- **C:** if IM with G = 4 or 6 passes, add it to `VALIDATED_CLUSTER_COUNTS["im"]`, requiring within-state
  assignment (`within_states=True`; manifests `spatial_clusters: {"k": 4|6, "method": "im"}`). The note for
  IM-8 outside MI/NY then names the validated alternative. If neither passes, the note says so.
- **K, S, M:** a procedure that passes gets "replicated on OH/PA (Round 54)" in its notes and docs. One that
  fails keeps its MI/NY validation, with an engine note that it failed on OH/PA (as Round 44 did for C1).
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit; geometry file
  checks); goldens identical.
- **Exploratory example:** OH/PA county child poverty rate on log median income and unemployment (2024 ACS,
  cached county responses), naive OLS slopes with IM using G = 4, 6 and 8 clusters, next to HC3. ACS only;
  no WONDER data.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Geometry file, script, criterion commit | | |
| C / K / S / M results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

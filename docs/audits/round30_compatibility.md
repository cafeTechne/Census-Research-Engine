# Round 30 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round30`, branch
`phase30/im-acs`, based on defaultBranch `5258c0a` (descends from the plan's
minimum `89edb41`). No owner-checkout edits, private WONDER-checkout access,
WONDER requests, GitHub CI, rebase, force-push, merge, tag or release.

## Frozen validation

Criterion/script/numerical candidates and all twelve beta-star values were
committed and pushed at `2774140a3bdfe0dd5d4f9727a7cdc99631255c01` before
the full run. Each beta-star reference uses 400,000 independent areas; linear
values passed their closed-form check. One smoke run used two draws per cell,
writing no audit files. The full run used exactly 2,000 draws in each of twelve
fixed cells and retained all failures in the coverage denominator. No target,
criterion, seed, cluster count or frozen source changed; the byte guard was
checked again after engine and post hoc work.

| Candidate/model | Coverage range | Outcome |
| :--- | :--- | :--- |
| C1 linear | .8790–.9130 | Passed all four cells |
| C1 binomial | .8690–.9060 | Passed all four cells |
| C1 Poisson | .8695–.9235 | Passed all four cells |
| C2 Fuller EIV | .0695–.9035 | Failed; corrected-matrix failures up to 92.6% |

Each candidate/model independently needed coverage >=.86 in every required
cell. The nominal one-sided size, true-beta coverage and finite-fit interval
widths are informational, fully reported in `im_acs_validation.md`/`.json`.
C1 covers the observed-ACS probability-limit coefficient, not a corrected
true slope. C2 remains refused, including exploratory manifests; no fallback.

## Engine and regression coverage

Round 30 adds 26 offline tests, including independent per-cluster statsmodels
OLS/binomial/Poisson comparisons, fixed offsets, exact per-cluster Fuller
comparison to fit_eiv, failure of one corrected matrix, hand-calculated IM
means/SEs/t(7) limits/p-values, supplied ACS replicates, constant state terms,
globally constant nuisance terms before rank checks, partial-constancy refusal,
non-estimable hypotheses, audit-controlled C1 gates,
failed EIV/incompatible-argument refusals, and a failed-EIV offline manifest run.
The planned positive EIV end-to-end run is intentionally unavailable because
C2 failed; enabling it would violate the acceptance rule. Existing C1 offline
manifest/bundle coverage remains in `test_round26.py`.

Tests also verify criterion-byte guards, smoke/no-audit and no-full-rerun rules,
cached input AND reference-result hashes, archive traversal and symlink refusal.
Round 26 refusal tests explicitly patch C1 gates false to retain coverage of
the historical restrictions; their positive IM assertions now use the updated
sampling-error semantics. No old numerical reference checks were removed.

## Every golden change

**None.** `scripts/refactor_golden.py`: all 640 snapshots of 14 manifests are
byte-identical before/after. `scripts/run_golden.py`: all 29 execution scenarios
and 20 deviation kinds are byte-identical. This includes all existing numbers,
status labels, methods text and dependent hashes. Neither harness nor its
normalization changed. New IM diagnostics apply only to newly eligible runs:
cluster terms/estimates, absorbed terms, full-sample reference coefficients,
naive estimand, non-additive sampling-error handling and a rank-deficiency
label for the full-sample reference when a globally constant nuisance was absorbed. No legacy result or
registered manifest was edited.

## Cache-only post hoc checks

HTTP was blocked; source hashes and registered manifest hashes were verified
before fitting and again afterwards. R21b/R22 inputs came from existing caches.
R29 came from the local v0.26.0 attachment, never the private export checkout.
Assignments use all 145 frozen MI/NY points before complete-case filtering.
All reference fits have residual Moran I summaries; OH/PA was not re-checked.

- R21b H1–H4: unavailable because C2 failed; no IM p-values invented.
- R22: H1/H2 retained, H3 unsupported; IM Holm p .01763/.05750/.22306.
  Registered X2 values remain reference values, not an endorsement of X2.
- R29 MI/NY: H1/H3 retained; H2 not retained, Holm p .16902
  (H1 .001520; H3 .005692). H2 excludes 13 suppressed counties after assignment.
  Fixed E still excludes offset/reference-rate uncertainty from slope inference.

An independent check recomputed all five available IM coefficient vectors,
cluster-mean SEs, t(7) limits/p-values and both Holm families from the saved
per-cluster estimates. C2 unavailable rows have null p-values. The R29 part
contains coefficient/diagnostic outputs only, with no county counts, residual
vectors or suppressed-derived county values, and passes
`census.wonder_outputs.audit_outputs`. Its scanner has no county-valued frames
to check; this is deliberate coefficient-only output, not a claim of scanning
county tables. The original attachment and registered sources were unchanged.

The local `r30_study_outputs.tar.gz` contains 11 files, no raw exports, input
parquets or symlinks. Both uncompressed files and archived member bytes passed
the owner-key scan. SHA-256:
`104e00b8656ddac854470dd505771bc3222afecf126ed7b8eae4ac30659814e3`.
No artifact was published. Report: `docs/studies/r30_posthoc_im_acs.md`.

## Exceptions and final suite

The requested initial `tests/test_round30.py` invocation found no such file at
the starting commit; it was then created and run before the full simulation.
A final engine edge-case commit followed the post hoc commit: globally constant
nuisance terms must be absorbed before checking rank. It changes none of the
full-rank post hoc fits, and was added without rewriting history.
Baseline supplied by v0.26.0: 1,860 passed, 37 skipped. Final suite acceptance
is **1,886 passed, 37 skipped, 4 warnings, 50 subtests passed; zero failures**,
in 335.27 seconds (baseline plus 26 tests). Warnings match the baseline. Also
recorded in PLAN_ROUND_30.md section 8 and STATUS.md. C2's failed validation
is the reason its engine path and R21b post hoc re-check remain unavailable;
spatial random effects for corrected EIV inference are next, not implemented here.

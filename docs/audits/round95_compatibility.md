# Round 95 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round95`, branch `phase95/ypll-surveillance`. The
criterion commit (tag `criterion-r95`) is an ancestor of the branch. Version 0.91.0.

## Behaviour changes

- **`joinpoint`** gains `aberration`. Without it, results are unchanged.
- **New modules** `census/surveillance.py` and the frozen core `census/surveillance_core.py`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan's example (state YPLL and latest-year flags for MI/NY/OH/PA) needs annual state WONDER exports, which
   are not on file.** The owner's exports are five-year pooled national age×sex and county totals. The example uses
   national YPLL by cause for both periods and flags on 2023 ACS 1-year state uninsured rates instead. Annual state
   exports could be added as a later manual WONDER part.
2. **Some national exports have suppressed age-by-sex cells.** The shared reference reader refuses them. The YPLL
   reader reports bounds (each cell at 1 and at 9) instead of failing, and never imputes a value.
3. **`ears_c2` uses a sample-SD threshold with no floor.** A perfectly flat baseline flags any increase (z = ∞), as
   in EARS.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 94.
- Full suite: 2357 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

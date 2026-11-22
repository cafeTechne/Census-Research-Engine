# Round 73 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round73`, branch `phase73/methods`.
- The criterion `e97e9fc` was committed before the full run and verified in git.
- The branch was rebased onto defaultBranch `dd4cbd4` (Round 71) after the run. The criterion commit was re-hashed
  with identical frozen files, and `e97e9fc` is kept at tag `criterion-r73`.
- Version 0.69.0.

## Results (`methods73_validation.md`)

- **M1 passed** in all four cells (.904–.913), so `FIXED_VALIDATED = True`.
- **LI passed** in all four cells (mean .897–.899, lowest area .878), so `LOADINGS_VALIDATED = True`.
- **M3 screening** gave .88–.98 on 100 draws. `SHARES_VALIDATED` stays `False`, as the criterion fixed in advance.

## Behaviour changes

- `multilevel_model(groups=...)` accepts a list `[top, middle]`. A string keeps the two-level model unchanged.
- `build_index` gains `method="loadings"`, `loadings` and `standardize`. Existing PCA/equal-weight calls are
  unchanged, because `standardize` defaults to False.
- `wonder_reference` gains two helpers; nothing existing changes.

## Plan deviations and exceptions

1. **M2 (parametric bootstrap) dropped** before the run (time; recorded in the criterion).
2. **M3 is screening only** (100 draws).
3. **The expected-count person-years rule is library-only.** Manifests join external data after their derivations,
   so a manifest cannot yet scale by WONDER person-years. The manifest `expected_count` rule (period years) is
   unchanged.
4. **`share_intervals` was added to `multilevel_model`** (not in the plan). A national fit needs one refit per state
   for the jackknife.

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round73.py` (8). Related files were rerun: 167 passed.
- Example: `r73_three_level_example.md`.
- Full suite: SUITE_LINE_73.

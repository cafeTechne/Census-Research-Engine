# Round 75 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round75`, branch `phase75/manifest-methods`, based on
defaultBranch after the v0.70.0 release. No new statistics. Version 0.71.0.

## Behaviour changes

- **New manifest method `multilevel`.**
  - `validate_manifest` lists it among the supported methods, so the "unsupported method" error message changed.
    This is the only difference in the schema golden.
- **New run stages.**
  - `_build_indices` runs after `_derive_replicates`, and `_apply_person_years` after `_join_external`. Both do
    nothing unless a manifest declares `indices` or `person_years`, so the run golden is byte-identical.
- **New manifest names.**
  - `state_fips` and `county_fips` are accepted manifest names. They are added to the frame only for an analysis
    that names them, so existing frames and analysed-data outputs are unchanged.
- **Groups given as a string.**
  - `_run_analyses` reads a string `groups` as one name; before, it was split into characters. No existing method
    used a string here.
- **Tract coordinates.**
  - `frame_coordinates` on a tract frame without `Year` now tries 2022, then 2019 boundaries. Before, it used 2022
    and failed on 2010-vintage tracts.
  - With a `Year` column the behaviour is unchanged.

## Checks

- **Indices.** A manifest index reproduces `build_index(method="loadings", standardize=True)` scores and replicate
  SEs to 1e-10 on the synthetic tract frame.
- **Three levels.** A three-level `multilevel` analysis reproduces `fit_three_level` estimates and intervals.
- **Person-years.** `person_years` expected counts equal `wonder_reference.expected_counts(person_years=...)`.

## Exceptions

1. **Two-level `sampling_se` is boolean.** True uses `<outcome>_se`, which is `fit_multilevel`'s `sampling_se=True`.
2. **Three-level manifests ignore replicates**, as validated, and say so in a note.
3. **Index indicators must be ACS variables or derivations.** Context and external indicators have no replicates,
   so the index interval would be incomplete.
4. **Methods text describes indices and person-years.** The `multilevel` method text is fixed and has no
   placeholders.

## Acceptance

- Goldens: run byte-identical; schema differs only in the method list.
- New tests: `tests/test_round75.py` (10).
- Full suite: SUITE_LINE_75.

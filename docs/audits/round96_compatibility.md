# Round 96 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round96`, branch `phase96/disease-mapping`. The criterion
commit (tag `criterion-r96`) is an ancestor of the branch. Version 0.92.0.

## Behaviour changes

- **`spatial_model`** gains `kind="disease_map"`, `expected` and `threshold`. Other kinds are unchanged.
- **New modules** `census/disease_mapping.py` and the frozen core `census/disease_mapping_core.py`, plus a frozen
  geometry file `docs/audits/mi_county_geometry.json`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan suggested a `small_area_estimates` option.** Disease mapping went into `spatial_model` instead, which
   already handles boundaries and contiguity.
2. **The core was restructured before the criterion was frozen,** with the model unchanged: one grid pass serves both
   B1 and B2, Newton uses Cholesky solves, and B2 drops grid points with weight below 1e-4. This took tract fits from
   20 s to 5 s.
3. **The plan named an interval-censored likelihood for suppressed counts.** Missing counts contribute no likelihood
   instead. Their areas are predicted from neighbours, labelled, and not validated.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 95.
- Full suite: 2362 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

# Round 93 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round93`, branch `phase93/spatial-models`. The criterion
commit (tag `criterion-r93`) is an ancestor of the branch. Version 0.89.0.

## Behaviour changes

- **New full-profile MCP tool `spatial_model`** (78 → 79 tools). README, STATUS, CLI tool list and attribution
  registry are updated. Core profiles are unchanged.
- **New modules** `census/spatial_models.py` and the frozen core `census/spatial_models_core.py`.
- **Manifests are unchanged**, so goldens are expected byte-identical.

## Exceptions

1. **Everything ships exploratory or descriptive.**
   - GWR failed: .71 local coverage with varying slopes, and test size .12–.17.
   - Diversity failed narrowly: .847 at 50 respondents per tract.
   - Classification and regionalization had no pass rule.

   Walker (2023) already treats GWR as exploratory.
2. **Validation used a proxy for contiguity.** It ran on Delaunay edges under 5 km; the engine uses queen contiguity
   from cartographic boundaries. Water-separated islands are dropped, with a note, and a disconnected graph is
   refused.
3. **Classification stability uses parametric replicates** (features + N(0, SE²) from the MOEs), not the Census VRE
   replicate tables. That matches the validation design.
4. **Diversity is library-only** (`census.spatial_models.diversity_index`), not a tool option. Its inputs are
   replicate share tables.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 92.
- Full suite: 2343 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

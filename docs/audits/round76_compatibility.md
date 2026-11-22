# Round 76 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round76`, branch `phase76/disparities`, based on
defaultBranch after the v0.71.0 release. Version 0.72.0.

## Behaviour changes

- **New manifest methods `disparity` and `kitagawa`** (statistics `rd`, `log_rr`, `idisp`, `bgv`, `theil`, `mld`;
  `crude_difference`, `rate_effect`, `composition_effect`). `validate_manifest` lists them among the supported
  methods, so the "unsupported method" message changed. This is the only difference in the schema golden (Round 75
  baseline: 148 added list entries, nothing removed).
- **Run golden byte-identical.** No existing method, stage or output changed.
- **New full-profile tool `disparity_measures`** (72 tools; core and core_spatial unchanged). The CLI runs it as
  `python -m census tool disparity_measures`.
- **Core routing text**: `get_recipe` lists `health_inequality (also disparities between groups)`, and core rule 8
  points to the between-groups section (`disparity_measures [full]`).
- **Citations**: `harper_lynch`, `pearcy_keppel`, `kitagawa`.

## Checks

- Hand-computed measures (two groups) and the Kitagawa identity rate effect + composition effect = crude difference.
- The replicate SE of a rate difference equals sqrt(4/80 Σ (d_r − d)²) computed directly from the replicate rows.
- Flags equal the audit JSON (`tests/test_round76.py::test_flags_equal_the_audit`).

## Exceptions

1. **Plan deviation: example table.** The plan named B17020A–I (child poverty by race). B17020 has no VRE file in
   2020–2024, so the example uses B17010 (families below poverty) with H, I and a derived "other non-Hispanic"
   group, which also makes the groups mutually exclusive.
2. **Plan deviation: simulated CVs.** The criterion set group CVs at the plan's three levels rather than drawing them
   from real MOE files (stated in the criterion before the run). Engine gates use the observed largest group-rate CV.
3. **Count-based manifests are not offered.** Manifest `disparity`/`kitagawa` take ACS rates with replicates; event
   counts (`counts=True`) are library and tool only, since manifest external counts would need the WONDER rules for
   each group.
4. **Missing replicates** give an undefined interval for that area (validated=False), never a filled value.
5. **Index measures are tested against a pre-registered positive `null_value` on the log scale**; rd/log_rr against zero.

# Round 78 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round78`, branch `phase78/policy`; defaultBranch (Rounds
76–77) merged in so the criterion commit `baf934b` (tag `criterion-r78`) stays an ancestor. Version 0.74.0.

## Behaviour changes

- `difference_in_differences` gains `design="staggered"` with `first_treated`, `method` and `unit`.
  `treatment_period` is now optional: two-group and event designs still require it (a clear error replaces the
  missing-argument TypeError). Existing calls are unchanged.
- New library module `census/staggered.py` (`staggered_did`, `synthetic_control`). No new MCP tool (73), no
  manifest change; goldens expected byte-identical.

## Exceptions

1. **No `synthetic_control` tool.** The plan added one only if C1/C2 passed; both failed, so synthetic control is a
   library function flagged exploratory.
2. **No manifest methods** (`did` staggered, `synthetic_control`): manifests have no DiD method and no annual
   (1-year) panels.
3. **Plan deviations stated in the criterion:** simulated state CVs (log-uniform .01–.08) rather than real
   2010–2023 files; never-treated controls only; no covariates.
4. **Conformal intervals covered with 15 pre-periods** (.87–.95) but not with 9; a pre-period gate was not pre-set,
   so they stay exploratory. A later round could validate such a gate.
5. **Example:** the S2701 percent-uninsured column moved (C03 through 2014, C05 from 2015); the script asserts the
   range so a wrong mapping fails loudly.

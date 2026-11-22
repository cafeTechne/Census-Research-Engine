# Round 77 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round77`, branch `phase77/joinpoint`; the criterion
commit `01ad5a4` (tag `criterion-r77`) stays an ancestor because defaultBranch (Round 76) was merged in rather than
rebased. Version 0.73.0.

## Behaviour changes

- **New full-profile tool `joinpoint`** (73 tools; core and core_spatial unchanged); CLI `python -m census tool
  joinpoint`.
- **No manifest change.** Run and schema goldens are expected byte-identical to Round 76.
- Protocol rule text and the `policy_change` recipe gain the joinpoint step.

## Results that set the engine

- Number of joinpoints (J1): validated; false-joinpoint rate .012–.023.
- APC and AAPC intervals (J2, J3, J2b, J3b): failed in many cells, worst where joinpoints are hard to place (small
  slope changes, few events). The engine reports the t intervals conditional on the selected joinpoints and flags
  them exploratory.
- Ratio of age-adjusted rates: Tiwari (default) and log-delta intervals validated.

## Exceptions

1. **No manifest methods** (`joinpoint`, `rate_ratio`). The plan listed them, but manifests are built on ACS
   five-year area frames; annual surveillance series are external data with no manifest route. Tool and library
   only.
2. **Example skipped**, as the plan allows: the owner's WONDER exports are pooled five-year periods (no annual
   national series), and WONDER is never queried automatically.
3. **Validation used 999 permutations** (engine default 4,999), stated in the criterion.
4. **Gaps in years** (for example a skipped 2020) are allowed with a note; slopes are per calendar year.

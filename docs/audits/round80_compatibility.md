# Round 80 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round80`, branch `phase80/sae`; defaultBranch (Rounds
76–79) merged in so the criterion commit `251dc9d` (tag `criterion-r80`) stays an ancestor. Version 0.76.0.

## Behaviour changes

- `small_area_estimates` gains `transform`, `n_col`, `temporal` and `release_column`; with none of them it behaves
  as before. No new tool (74), no manifest change; goldens expected byte-identical.

## Exceptions

1. **No manifest `fay_herriot` args.** Manifest Fay–Herriot hypotheses test regression coefficients; Round 80
   validated area estimates, so the new options are tool and library only.
2. **Bootstrap MSE for Rao–Yu** instead of a Prasad–Rao-type analytic MSE, and **a 300-tract sample** for the
   temporal tract cells (both stated in the criterion).
3. **Example without a map** (summary only), and the temporal part on counties: tract IDs changed between the
   2014–2018 and 2019–2023 releases.
4. The bias-corrected back-transform had a slightly larger small-p relative bias than the naive one (.078 vs .044 at
   most) but better coverage; both are within the criterion.

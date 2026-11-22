# Round 90 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round90`, branch `phase90/positivity`. The criterion
commit (tag `criterion-r90`) is an ancestor of the branch. Version 0.86.0.

## Behaviour changes

- **`estimate_effect(kind="treatment")`:**
  - results gain `positivity`;
  - `weights=` is new;
  - with 5% or more of propensities outside [.05, .95], `method="ipw"` results become `validated: false`, with a note;
  - the summary names the estimand and says when overlap is limited.
- **The library function `causal.estimate_effect`** gains `weights` and returns `positivity`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan's "Round 41 example" could not be re-run.** Its archived inputs in `/tmp` are gone. The example uses
   current ACS county data instead (metro status, uninsured rates, MI/NY/OH/PA).
2. **`method="ipw"` is downgraded although P0 was "reported only".** P0 gives exactly the same estimate as W1
   (tested to 1e-10), and W1 failed the pre-set criterion, so the downgrade follows from the criterion.
3. **AIPW was not part of this validation.** Its Round 41 status stands; under limited overlap a note says it was
   not tested there.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 89.
- Full suite: 2324 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

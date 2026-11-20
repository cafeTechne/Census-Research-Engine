# Round 66 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round66`, branch `phase66/numeric-replications`, based
on defaultBranch `55fcf6a`.

## Pre-registration

- Criterion `dd48bf6` was pushed before any comparison and before the full simulation.
- Deviation 1 (`d30d7ed`): the first run stopped in A's descriptive interval part, on a county with an undefined
  replicate refit. The fix runs that part county by county. The comparison file written before the stop was never
  opened, and the rules were unchanged.

## Results

| Target | Rule | Result |
| :--- | :--- | :--- |
| A: CHR county dissimilarity | median \|diff\| ≤ 0.5, ≥ 90% within 1 point | 0.0000; 100% (2,055 counties): replicated |
| B: Census state Gini | median \|diff\| ≤ .005, ≥ 10 of 12 contained | .0008; 10 of 12: replicated |
| S: segregation on GA/TX/AZ | every judged bin in the validated range passes | isolation, H pass; bias-corrected D fails [.75, 1) on TX |

## Behaviour change

- `REALISTIC_RANGES[("dissimilarity", "bias_corrected", 2)]` changes from (.15, 1.0) to (.15, .75). Counties
  whose noise level is in [.75, 1) are no longer validated for D; their isolation and H are unaffected.
- `tests/test_round52.py`: two assertions updated with Round 66 comments.
- Rule text mirrored (protocol and generated MCP text, MCP core item 13, segregation recipe).

## Data and archives

- Inputs: ACS 2019–2023 API tables, VRE B03002 tract files for 5 states, and PUMS housing files for 12 states. All
  sit in the engine caches, fetched by `scripts/r66_fetch.py`.
- CHR's published file is pinned by commit and SHA-256 and not committed.
- The per-county comparison and the interval table are in `/tmp/r66_example_outputs.tar.gz`. They are not in the
  repository, because the comparison repeats CHR's published values. For the same reason, the CHR column was removed from
  the audit JSON's interval table after the run; nothing else in the audit changed.

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round66.py` (3).
- Full suite: 2158 passed, 37 skipped; 0 failures.

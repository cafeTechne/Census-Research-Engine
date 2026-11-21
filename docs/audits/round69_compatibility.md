# Round 69 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round69`, branch `phase69/monnat`, based on
defaultBranch `a8f7ff6`.

## Pre-registration

- Criterion `20a4c13` was committed after a counts-only build and before any association or the full simulation.
  The committed text was checked in git, a guard against Round 67's placeholder slip.
- The first run of the replication was stopped by a 50-minute `timeout` in the shell command, not by the script:
  the descriptive censored-NB2 part refits once per covariate. That run wrote nothing. The same frozen script was
  rerun with no time limit. Nothing changed.

## Results

- **D: replicated.** Economic distress 9.95 (7.77–12.12) against 9.62; ratio 1.03.
- **S: passes.** .908 and .881 on 3,103 national counties.

## Behaviour

- No engine change. Data: the owner's WONDER Part G exports (private backup repository), ACS, CBP 2012 and the ERS
  2015 extract (pinned by SHA-256, in the cache only).
- Goldens byte-identical. New tests: `tests/test_round69.py` (1). Full suite: 2163 passed, 37 skipped; 0 failures.

# Round 52 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round52`, branch `phase52/segregation-groups`, based on defaultBranch `578e049`.

## Data

`scripts/segregation_groups_counts.py` builds the truth file from cached API responses:
- 2024 B03002 for MI/NY/OH/PA;
- 2024 B17001 for OH/PA;
- 2015–2019 B17001 for MI/NY.

These were fetched with the owner's key before the plan was written; the key is not stored. The file is
byte-reproducible (sha256 `5e44442c…ea29bee1`).

## Frozen validation (criterion `b19696b`, pushed before the full run; 2,000 draws per cell, 14 cells)

Combined engine ranges (a bin counts only if every design judging it passed):

| Variant | Before (Round 50) | After (Round 52) | Deciding evidence |
| :--- | :--- | :--- | :--- |
| D bias-corrected | [.15, .50) | [.15, 1.0) | Black designs fail [1, ∞) (MI/NY .845, OH/PA .838) |
| Isolation bias-corrected | [0, .50) | [0, ∞) | every judged bin passes (lowest bin mean .867) |
| H bias-corrected, two groups | [0, .50) | [0, 1.0) | OH/PA Black fails [1, ∞) (.874 mean, share ≥ .80 below .90) |
| Isolation and H naive | [.15, .30) | none | Black and Hispanic designs fail [.15, .50) |
| D naive | none | none | fails everywhere |
| H bias-corrected, three groups | [0, .50) | unchanged | no three-group design in Round 52 |
| H bias-corrected, four / five groups | exploratory | [0, ∞) | bin means .953–.997 / .969–.989 |
| H naive, four / five groups | exploratory | none | .672–.864 |
| Release contrasts (all two-group variants) | not tested | larger noise < .50 | bin means .869–.971 |

Pre-run deviation: equicorrelation −.3 is not positive definite for five groups; race5 uses −.2. This is
recorded in the criterion and was found by the first smoke run.

**Note on infinite noise.** A county whose median tract has a zero count for some group has an infinite noise
level. Such counties fall outside every simulation bin; the engine never validates them. The per-design bin
tallies in the audit header count them in the last bin; the judged rows do not.

## Engine

- `census/segregation.py`: `REALISTIC_RANGES` as above (new keys for four and five groups; `INF`),
  `MAX_VALIDATED_MEDIAN_CV = inf`, new `CONTRAST_RANGES`. `segregation_test` validates a cross-release contrast
  only with two groups and the larger noise level inside the range. `CLIP_RANGES` unchanged (≤ .50).
- Registered manifests: unchanged bytes. A manifest that overrides to naive isolation/H is now refused unless
  exploratory (as for any failed variant). The manifest method text still describes the Round 28 gate
  (unchanged to keep the goldens byte-identical, as in Round 50).
- Rule text mirrored: `docs/agent_protocol.md`, `docs/recipes/segregation.md`, MCP core item 13 and
  `mcp_server.py`.

## Behaviour changes

- Naive isolation/H rows that Round 50 validated (noise .15–.30) are now exploratory.
- Bias-corrected rows with noise .50–1.0 (D, H) or any finite level (isolation, four- or five-group H) are now
  validated.
- Older tests updated with comments: `tests/test_round28.py` (2), `tests/test_round50.py` (4),
  `tests/test_round51.py` (1).

## Acceptance

- Schema and run goldens: byte-identical to the Round 50/51 snapshots.
- New tests: `tests/test_round52.py` (8).
- Full suite: 2074 passed, 37 skipped; 0 failures (a first run during doc edits had one transient failure; the rerun on the final tree is clean).

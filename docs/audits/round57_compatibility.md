# Round 57 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round57`, branch `phase57/segregation-gaps`, based on defaultBranch `998474d`.

## Frozen validation (criterion `8bcad0b`, pushed before the full run; 2,000 draws per cell, 12 cells)

| Problem | Outcome |
| :--- | :--- |
| A: clipped replicates, two groups (Round 51 poverty + black2 + hisp2 combined) | bias-corrected I to .75, H to 1.0; D stays at .50; naive variants none |
| A: clipped replicates, four / five groups | bias-corrected H at every finite level; naive none |
| B: six groups | bias-corrected H at every finite level; naive failed |
| C: same-release county contrasts (68 MI/NY poverty pairs) | every two-group variant to .50 except corrected D (bin means .855–.856) |

Six-group cells use ρ = −.15, because −.3 and −.2 are not valid equicorrelations for six groups (stated in the
criterion before the run).

## Engine

- `census/segregation.py`:
  - `CLIP_RANGES` extended, with four- and five-group keys;
  - `REALISTIC_RANGES` gains six groups;
  - new `SAME_RELEASE_CONTRAST_RANGES`, enforced in `segregation_test`;
  - new `group_quarters_tracts`;
  - `segregation_replicate(..., exclude_tracts=...)`.
- Manifests: `segregation` `args.group_quarters: {gq, total, max_share}` (validated against manifest variable names;
  method text describes the exclusion). Registered manifests unchanged.
- Rule text mirrored: `docs/agent_protocol.md`, `docs/recipes/segregation.md` (new step 9), MCP core item 13,
  `mcp_server.py`.

## Behaviour changes

- Clipped counties above .50 are now validated for bias-corrected isolation (to .75), two-group H (to 1.0) and four-
  or five-group H.
- Six-group bias-corrected H is validated.
- Same-release county contrasts are now gated: corrected D is refused, and a larger noise level of .50 or more is
  refused.
- Older tests updated with comments: `tests/test_round50.py`, `tests/test_round51.py`, `tests/test_round52.py` (2).

## Acceptance

- Schema and run goldens: byte-identical to the Round 50–56 snapshots.
- New tests: `tests/test_round57.py` (5).
- Full suite: 2105 passed, 37 skipped; 0 failures (a first run failed one older rule-text test; core text fixed and rerun).

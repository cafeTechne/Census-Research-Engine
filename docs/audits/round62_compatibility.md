# Round 62 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round62`, branch `phase62/leftover-failures`, based on defaultBranch `559af7d`.

## Frozen validation (criterion `8f14e39`, pushed before the full run; 15 cells)

| Problem | Result | Outcome |
| :--- | :--- | :--- |
| A: binomial SCPC, Round 58 cells (8 × 2,000 draws + 10,000-draw R cell) | ρ̄ .15: .886–.954; ρ̄ .20: .909–.966 | both pass; default .15 |
| B: Theil T, 8,000 households, log interval | I1 .873–.898; I2 .858–.888 (T0 .858–.896) | fails: exploratory at every sample size tested |
| C: clipped six-group H (bias-corrected) | judged bins [.75, 1) and [1, ∞) pass (means .955–.973; affected-draw coverage .955–.973) | validated to any finite level |
| C: clipped six-group H (naive) | .61–.79 | fails |

## Engine

- `census/scpc.py`: `VALIDATED_RHO["binomial"] = (.15, .20)`, `DEFAULT_RHO["binomial"] = .15`. The manifest check
  (`fit_replicate` `args.spatial_scpc`) and the MCP route follow.
- `census/segregation.py`: `CLIP_RANGES` six-group keys.
- `census/pums_inequality.py`: the Theil note records the Round 62 failure.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 9,
  `docs/recipes/regression_sampling_error.md`, `docs/recipes/external_health_outcome.md`,
  `docs/recipes/segregation.md`, `docs/recipes/pums_tests.md`.

## Behaviour changes

- Binomial SCPC is validated with its default (`rho_bar` .15).
- Clipped six-group counties can be validated.
- Older tests updated: `tests/test_round58.py` (2), `tests/test_round61.py` (2), `tests/test_round51.py` (1).

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round62.py` (5).
- Full suite: 2132 passed, 37 skipped; 0 failures (a first run failed one older rule-text test; recipe wording fixed and rerun).

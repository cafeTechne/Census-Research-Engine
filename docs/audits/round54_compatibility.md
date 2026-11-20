# Round 54 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round54`, branch `phase54/ohpa-revalidation-2`, based on defaultBranch `7da6c68`.

## Frozen validation (criterion `e42840d`, pushed with the geometry file before the full run; 2,000 draws per cell, 48 cells)

| Problem | Procedure | Result |
| :--- | :--- | :--- |
| C, MI/NY | naive IM, G = 4 / 6 / 8 | .885–.931 / .869–.932 / .848–.914; G = 8 below .86 in one cell (linear, 100 km, reliability .7: .8485; Round 30 had .885) |
| C, OH/PA | naive IM, G = 4 / 6 / 8 | worst cells .827 / .753 / .720 (binomial, 100 km, reliability .7); repair **failed** |
| K, OH/PA | IM-8 counts NB2 / Poisson | .891–.911 / .899–.905: **replicated** |
| S, OH/PA | calibrated IM-8 counts Poisson / NB2 | .875–.905 / .887–.912: **replicated** (naive IM-8 .332–.887) |
| M, OH/PA | G1 p = 3, 4, 5 | .859 / .859 / .850 at reliability .7 with 100 km fields: **failed** (other cells .887–.910) |
| M, OH/PA | G2 p = 3, 4 / 5 | .861–.920 **replicated** / .807 **failed** (363 failed fits of 2,000 in that cell) |

The G1 failures are narrow (.8595 against .86) but follow the pre-set rule. The same cells had many failed fits
(12–93 for G1, 82–363 for G2).

## Engine

- `census/im_clusters_core.py` (new, frozen): IM with G clusters; identical to `census.im_acs` for G = 8
  (tested). Not routed into the engine because neither repair passed.
- `census/spatial_clusters.py`: `IM_CLUSTER_COUNT_REPAIR_VALIDATED = {4: False, 6: False}`;
  `VALIDATED_CLUSTER_COUNTS["im"]` stays `(8,)`. `geography_notes(..., kind=)`: the naive-IM note outside MI/NY
  now reports the failed repair; count models (`kind="counts"`) report the OH/PA replication instead.
- `census/spatial_eiv.py`: an "EXPLORATORY OUTSIDE MI/NY" note for G1 with three or more and G2 with five or more
  error-prone covariates outside MI/NY. The validated flag is unchanged, as in Round 44.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 9,
  `docs/recipes/regression_sampling_error.md`, `docs/recipes/external_health_outcome.md`.

## Not covered

Round 48's effective-n correlation and α intervals: their reference targets were computed on MI/NY geometry;
an OH/PA re-check needs new targets (backlog N31).

## Behaviour changes

- Notes only: count models outside MI/NY now say "replicated on OH/PA"; spatial EIV with many error-prone
  covariates outside MI/NY carries an exploratory note. `tests/test_round45.py` (1 assertion) updated.

## Acceptance

- Schema and run goldens: byte-identical to the Round 50–53 snapshots.
- New tests: `tests/test_round54.py` (6).
- Full suite: 2088 passed, 37 skipped; 0 failures.

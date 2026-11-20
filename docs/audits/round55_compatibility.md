# Round 55 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round55`, branch `phase55/short-series-reference`, based on defaultBranch `30365a1`.

## Frozen validation (criterion `dd6d6b7`, pushed before the full run; 2,000 draws per cell, 14 cells)

| Problem | Procedure | Result |
| :--- | :--- | :--- |
| I, n = 20 and 25 | I3 bootstrap-t at a bias-corrected AR coefficient | .867–.889 (both changes, φ .3 and .6): **validated from 20 points** |
| I, n = 15 | I3 | .857 (slope change, φ .6): fails |
| I | I2 Round 48 bootstrap-t (comparison) | .846–.893; ≥ .872 at 25 points (engine threshold kept at 30: comparison arm) |
| I | I4 EWC HAR t test | .616–.720: **failed** |
| R | R1 with the reference-population SE | .892–.908: **passed** |
| R | R0 without it (comparison) | .863–.907 |

No failed fits. The R refusals (2, 2, 1 draws of 2,000) were draws with a zero reference death in a band.

## Engine

- `census/its_small_core.py` (new, frozen): `its_bootstrap_t_bc`, `its_ewc`.
- `census/small_spatial.py`: `ITS_BOOTSTRAP_BC_MIN_N = 20`, `ITS_EWC_VALIDATED = False`, `SHORT_SERIES_AUDIT`.
- `census/missing_censored_its.py`: `interrupted_series(method="bootstrap_t_bc" | "ewc")`; the result carries
  `phi_bias_corrected`; notes point to the validated method.
- `census/standardize.py`: `indirect_standardize(reference_population_se=...)` (needs `reference_counts`);
  `SMR_REFERENCE_POPULATION_VALIDATED`. The "person-years fixed" note appears only when no SE is given.
- Manifests: `smr` `args.reference_population_se` (list, one per band; literal `reference_counts` required);
  registered manifests unchanged.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 11,
  `docs/recipes/health_inequality.md`.

## Exception

The round ends with a labelled demonstration on simulated inputs (`docs/studies/r55_demonstration.md`), not an
MI/NY data example, because no suitable real input is available offline.

## Acceptance

- Schema and run goldens: byte-identical to the Round 50–54 snapshots.
- New tests: `tests/test_round55.py` (6).
- Full suite: 2094 passed, 37 skipped; 0 failures.

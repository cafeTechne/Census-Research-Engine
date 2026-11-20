# Round 58 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round58`, branch `phase58/spatial-outside-miny`, based on defaultBranch `15223fa` (the plan
commit).

## Frozen validation (criterion `e8c6c8c`, pushed before the full run; 43 cells)

| Problem | Procedure | Coverage (lowest–highest cell) | Outcome |
| :--- | :--- | :--- | :--- |
| N + R, OLS | SCPC ρ̄ .05 / .10 | .861–.930 / .897–.947 | both pass |
| N + R, Poisson | SCPC ρ̄ .05 / .10 | .830–.917 / .863–.934 | .10 passes |
| N + R, binomial | SCPC ρ̄ .05 / .10 | .793–.914 / .846–.936 | fail (MI/NY and OH/PA, 100 km, reliability .9) |
| N + R | IM-8 (comparison) | OLS .825–.915, binomial .716–.915, Poisson .756–.911 | OH/PA failures as in Round 54 |
| R (10,000 draws), MI/NY 100 km, reliability .7 | IM-8 | OLS .8583, binomial .8857, Poisson .8756 | OLS confirmed below .86 |
| G (reliability .8) | G1 / G2, p 3–5, both geometries | .886–.907 / .887–.934 | pass |
| B | calibrated binomial IM-8 | .877–.907 | pass |

The SCPC benchmark ranges are 65 / 107 km (MI/NY, ρ̄ .05 / .10) and 52 / 81 km (OH/PA). Before freezing, the
critical value was checked by simulation: rejection .1014 at the benchmark correlation.

## Engine

- New `census/scpc_core.py` (frozen) and `census/scpc.py`: `fit_scpc(formula, frame, model, trials, exposure,
  coords, rho_bar)`, with `VALIDATED_RHO` (OLS .05/.10, Poisson .10, binomial none) and `DEFAULT_RHO`.
- MCP: `fit_model(method="replicate", spatial="scpc")`.
- `census/models.py`: IM-8 OLS results get a Round 58 note recommending SCPC. New
  `regression_calibration_clusters` (binomial; `RC_CLUSTERS_BINOMIAL_VALIDATED`). MCP:
  `fit_model(method="regression_calibration", model="binomial", spatial="clusters")`.
- `census/spatial_eiv.py`: per-covariate reliability is reported (`reliability`). Outside MI/NY with three or more
  error-prone covariates (G1) or five (G2), the note depends on the gate (`RELIABILITY_GATE = .8`).
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 9,
  `docs/recipes/regression_sampling_error.md`, `docs/recipes/external_health_outcome.md`.

## Exception

Manifests do not get an SCPC option in this round. The plan proposed `args.spatial_scpc` for `fit_replicate`, but
`fit_replicate`'s manifest checks and registered outputs are intricate, and SCPC needs no change to
`fit_replicate` to be used. Library and MCP only; recorded for a later round.

## Behaviour changes

- Notes only for existing paths (IM-8 OLS; spatial EIV outside MI/NY).
- `tests/test_round54.py`: the outside-MI/NY note now depends on the estimated reliability (assertion updated).

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round58.py` (7).
- Full suite: 2112 passed, 37 skipped; 0 failures (a first run failed one older rule-text test; core text restored and rerun).

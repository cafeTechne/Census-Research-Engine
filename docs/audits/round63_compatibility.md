# Round 63 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round63`, branch `phase63/small-samples-covariates`, based on defaultBranch `5a215de`.

## Frozen validation (criterion `ac2f34c`, pushed before the full run; 30 cells, 2,000 draws each)

| Problem | Result | Outcome |
| :--- | :--- | :--- |
| I: interrupted series, 15/17/19 points × φ .3/.6 | worst cell: I3 .855/.861/.869; I6 (conservative) .855/.865/.871; I7 (bootstrap bias correction) .849/.853/.861 | I6 validated from 17 points; I7 from 19; 15 points fail for all |
| G: G1, 6–8 error-prone covariates, reliability .8/.9, both geometries | .873–.918 | passes to 8 under the gate |
| G: G2, 6–8 error-prone covariates | 6–7: .876–.940; 8: .856 (OH/PA, 100 km, reliability .8) | passes to 7 under the gate |

## Engine

- `census/its_small_core.py`: `its_bootstrap_t_cons`, `its_bootstrap_t_bb` (frozen with the criterion).
- `interrupted_series(method="bootstrap_t_cons" | "bootstrap_t_bb")`:
  - `small_spatial.ITS_BOOTSTRAP_CONS_MIN_N = 17` and `ITS_BOOTSTRAP_BB_MIN_N = 19`;
  - the REML note now points to `bootstrap_t_cons`.
- `spatial_eiv.GATED_MAX_ERROR_COVARIATES = {"g1": 8, "g2": 7}`. A fit with six or more error-prone covariates is
  validated only when every estimated reliability is ≥ .8. The ungated cap stays 5.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core items 9 and 11,
  `docs/recipes/regression_sampling_error.md`; the manifest refusal message.

## Behaviour changes

- New interrupted-series methods.
- Spatial EIV fits with 6–8 (G1) or 6–7 (G2) error-prone covariates and every reliability ≥ .8 are now validated.
- `tests/test_round46.py`: the "not validated" case moved from 6 to 9 covariates.

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round63.py` (5).
- Full suite: 2137 passed, 37 skipped; 0 failures.

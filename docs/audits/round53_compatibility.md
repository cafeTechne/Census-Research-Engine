# Round 53 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round53`, branch `phase53/glm-correction-2`, based on defaultBranch `27a5dbd`.

## Frozen validation (criterion `8d48956`, pushed before the full run; 2,000 draws per cell, 28 cells)

| Problem | Procedure | Coverage | Outcome |
| :--- | :--- | :--- | :--- |
| J binomial | RC, jackknife SE | .882–.904 | pass (bootstrap, Round 46: .851–.889) |
| J Poisson | RC, jackknife SE | .886–.904 | pass |
| J NB2 | RC, jackknife SE | .897–.908 | pass |
| S Poisson | calibration + IM-8 (`rc_im`) | .877–.904 | pass (naive IM-8 .349–.853) |
| S NB2 | calibration + IM-8 | .894–.909 | pass (naive IM-8 .578–.890) |
| M p = 5 | G1 / G2 | .864–.908 / .884–.925 | pass, but at reliability .7 with 100 km fields: 68 / 200 failed fits, mean bias −.21 / +1.24 |
| M p = 6 | G1 / G2 | .811–.909 / .804–.933 | fail (reliability .7, 100 km: .811 / .804) |

No failed fits in J or S. Mean bias in J and S: −.022 to +.003.

## Engine

- `census/models.py`: `regression_calibration(..., se_method="jackknife")`: delete-one-area refits that
  re-estimate the calibration, with t intervals and n − p df. New `RC_VALIDATED_SE` (jackknife validated for
  binomial, Poisson and NB2; not re-tested for linear models). `_corrected_result` takes an optional df. Binomial
  bootstrap notes now point to the jackknife.
- `census/rc_spatial_core.py` (new, frozen): `rc_im`.
- `census/count_models.py`: `fit_count_model(..., spatial="clusters", calibrate=[...])` (pooled calibration,
  then IM-8); `SPATIAL_RC_VALIDATED`. `calibrate` without `spatial` is refused (use `regression_calibration`).
- `census/spatial_eiv.py`: `VALIDATED_MAX_ERROR_COVARIATES = 5`, with a five-covariate instability note.
- MCP `fit_model`: new `se_method`; `method="regression_calibration", spatial="clusters"` routes to the
  calibrated IM-8 count model (poisson or negbin, with exposure).
- Manifests: `regression_calibration` args are passed through, so `args.se_method: "jackknife"` works. Its
  method text describes the jackknife when it is chosen (new `format_text`). The binomial confirmatory refusal
  now applies only to the bootstrap. Refusal text for spatial EIV now says "at most 5". The registered
  `fit_eiv` method text ("up to four error-prone covariates") is unchanged, to keep both goldens
  byte-identical; it understates the range.
- Rule text mirrored: `docs/agent_protocol.md`, `docs/recipes/regression_sampling_error.md`, MCP core item 10
  and `mcp_server.py`.

## Behaviour changes

- Binomial RC with `se_method="jackknife"` is validated, and confirmatory in manifests that set it.
- Spatial EIV with five error-prone covariates is validated (previously exploratory).
- Older tests updated: `tests/test_round46.py` (the cap is now 5; the five-covariate case is validated).

## Acceptance

- Schema and run goldens: byte-identical to the Round 50–52 snapshots.
- New tests: `tests/test_round53.py` (7).
- Full suite: 2082 passed, 37 skipped; 0 failures.

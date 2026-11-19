# Round 46 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round46`, branch `phase46/glm-correction`, based on defaultBranch `0dbe0de`.

## Frozen validation (criterion `4aceb22`, pushed before the full run; 2,000 draws per cell)

| Procedure | Coverage (min–max over cells) | Outcome |
| :--- | :--- | :--- |
| R1 regression calibration, binomial | .8505–.8885 | **Failed** (.8505 at reliability .9, error correlation .3) |
| R1 regression calibration, Poisson | .8690–.8925 | Passed |
| R1 regression calibration, NB2 | .8875–.9175 | Passed |
| R0 naive GLM (HC3 / NB2-HC3) | .3810–.8545 | comparison |
| G1, three error-prone covariates | .8810–.9065 | Passed |
| G2, three error-prone covariates | .8775–.9270 | Passed |
| G1, four error-prone covariates | .8895–.9040 | Passed |
| G2, four error-prone covariates | .8765–.9120 | Passed |

Calibrated bias was small (|bias| ≤ .017 on a slope of .3; naive −.02 to −.08). In the M cells with
reliability .7 and 100 km fields the moment correction was unstable: mean bias up to +.168 (G2, p = 4) and
up to 114 of 2,000 failed fits (counted as non-coverage). Coverage still held, so the criterion passes. The
engine now says so for fits with 3–4 error-prone covariates.

## Engine

`models.RC_VALIDATED` (ols, wls, poisson, negbin true; binomial false) and a
`regression_calibration_validated` diagnostic. A validated or EXPLORATORY note is added for each GLM.
The manifest coefficient extractor refuses binomial regression calibration in confirmatory runs. The MCP
`fit_model` next step marks it exploratory. `spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES = 4`, with a note
about instability at 3–4 error-prone covariates. The rule text is mirrored in `agent_protocol.md`, the
`regression_sampling_error` recipe, the MCP core instructions, the `fit_model` docstring and the `fit_eiv`
methods text. No registered manifest uses regression calibration.

## Exception

The plan's example (child poverty on income and unemployment, binomial regression calibration) was
replaced. Binomial regression calibration failed, so the example uses the Round 29 H1–H3 NB2 models with
poverty calibrated (`docs/studies/r46_rc_example.md`).

## Goldens and suite

Both goldens are byte-identical to Round 45 (`schema_r46`/`run_r46` vs `schema_r45`/`run_r45`).
Suite: 2015 passed, 37 skipped, 63 subtests; 0 failures (8 new tests in `tests/test_round46.py`).

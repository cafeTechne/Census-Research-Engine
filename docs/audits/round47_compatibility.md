# Round 47 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round47`, branch `phase47/causal-robustness`, based on defaultBranch `39d2733`.

## Frozen validation (criterion `cbdc97f`, pushed before the full run; 2,000 draws per cell)

| Procedure | Coverage | Outcome |
| :--- | :--- | :--- |
| T1 AIPW on calibrated confounders | .8885–.9050 | Passed |
| T0 plain AIPW, noisy confounders | .7710–.8660 | comparison (bias +.05 to +.16 on .5) |
| W2 Anderson–Rubin, by observed F bin | .8941–.9078 | Passed |
| W1 2SLS Wald, by observed F bin | .9042–.9974 | cut-off F₀ = 0 |
| S1 calibrated mediator | .8825–.8980 | Passed |
| S0 naive mediator | .5770–.8575 | comparison |
| D1 chained-equations MI, both slopes | .8980–.9155 | Passed |
| D0 complete case | .8350–.9150 | comparison (MAR bias −.05 to −.08) |

At F < 10 the 2SLS Wald interval covers only because it is extremely wide. Its mean bias was about ±1
on a slope of .5 at expected F of 2–5. The design has moderate endogeneity, which comes only from
measurement error. With stronger endogeneity, Wald intervals are known to under-cover when the
instrument is weak, so the engine points users to the AR interval below F = 10.

## Plan departures (recorded in the criterion before the run)

- The AR set is inverted exactly rather than over a grid; a test checks it against a grid.
- MAR missingness depends on the fully observed outcome only.
- The example uses the 2011–2015 release (cached tract tables summed to counties) rather than
  2013–2017, so that it needs no network access.

## Engine

New frozen `census/causal_robustness_core.py`.

**`causal.estimate_effect(calibrate=True)`**
- AIPW only.
- Takes `_se` or `_moe` columns.
- The path where every confounder is error-prone is the frozen core itself.
- Error-free confounders are passed through, with a note that this was not part of the design.

**Plain AIPW with noisy confounders** now reports `validated=False` (Round 41 reported True with a
warning).

**`iv_slope`**
- Adds `ar_interval` and `ar_validated`.
- `validated = F >= 0`.
- Adds a weak-instrument note below F = 10.
- The corr < .3 rule is removed, so `tests/test_round43.py`'s note assertion was updated.

**Other engine changes**
- `causal.mediation(calibrate=True)`: no controls; bootstrap only.
- `impute_and_fit` accepts a list of one or two covariates. A single name keeps the Round 42 routine.
- MCP: `estimate_effect(calibrate=...)`; the IV summary reports AR and F; `fit_model(impute=[...])`.

Rule text is mirrored in `agent_protocol.md`, the recipes `causal` and `regression_sampling_error`, and
the MCP core instructions. Causal tools are not in manifests.

## Goldens and suite

Both goldens byte-identical to Round 46 (`schema_r47`/`run_r47`). Suite: 2027 passed, 37 skipped, 63 subtests; 0 failures (12 new tests in `tests/test_round47.py`).

# Round 49 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round49`, branch `phase49/pums-models`, based on defaultBranch `434e732`.

## Frozen validation (criterion `c0dfd0a`, pushed before the full run; 2,000 draws per cell)

Generator: the Round 32 superpopulation (household clustering ρ ∈ {.1, .4}, weight CV ∈ {.3, 1.0},
800 or 3,000 households, ACS-style SDR replicate weights). V1 is the SDR replicate variance from 80
warm-started refits; V0 is the model-based SE with weights normalised to n (comparison only).

| Model | V1 coverage | V0 coverage | Outcome |
| :--- | :--- | :--- | :--- |
| O ordered logit (slope; pseudo-true target) | .8795–.9060 | .6250–.8750 | Passed |
| P ordered probit (slope .8) | .8750–.9060 | .6200–.8715 | Passed |
| M multinomial logit (two slopes; pseudo-true targets) | .8790–.9120 | .6275–.8790 | Passed |
| Q weighted median regression (.15, .3) | .8875–.9150 | none | Passed |
| G probit (.4, .5) | .8780–.9070 | .7055–.8865 | Passed |

No fit failed in any draw. The largest bias is −.009, for the first multinomial slope at 3,000
households, which is small relative to its SE.

**Deviation from the plan.** None in the procedures. Before freezing, the smoke run led to two solver
fixes that are recorded in the criterion: a Newton-decrement stop, for replicate warm starts that are
already at the optimum, and an exact-LP fallback for median IRLS.

## Engine

New frozen `census/pums_models_core.py` (solvers and the SDR wrapper). New `census/pums_models.py`
holds `fit_pums_model` and the flags, which `tests/test_round49.py` checks against the audit JSON.

| Function | Change |
| :--- | :--- |
| `fit_pums_model(formula, df, model)` | New: patsy formula on PUMS codes; ordered outcomes have their codes sorted and their thresholds reported; the multinomial baseline is the lowest code |
| MCP `pums_regression` | `model` also accepts `ordered_logit`, `ordered_probit`, `mnlogit`, `median` and `probit`, routed to `fit_pums_model`. The existing `ols`/`logit`/`poisson` path is unchanged |

Rule text is mirrored in `agent_protocol.md` (section 14 and the Round 40 note), the PUMS recipe and
the MCP core instructions. `pums_regression` is marked `[full]` there because it is not a core-profile
tool.

## Goldens and suite

Both goldens are byte-identical to Round 48 (`schema_r49`/`run_r49`). Suite: 2050 passed, 37 skipped, 63 subtests; 0 failures (15 new tests in `tests/test_round49.py`).

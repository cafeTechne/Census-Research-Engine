# Agent routing contract (Round 64)

Research questions an agent is likely to bring, the tool it should reach for in the named MCP profile, and the flag
the engine must return. `tests/test_agent_routing.py` runs every row on offline fixtures. It checks three things: the
tool exists in the profile, the named guidance (a recipe or the server instructions) mentions the tool, and the
result carries the expected flag. "Refused" means `success: false` with a reason; "exploratory" means
`validated: false` with a note.

Rows marked "library" check the flag through the library function the tool calls, because the tool itself downloads
data (PUMS) or needs replicate files. The same questions are tasks in `scripts/local_model_eval.py`; live model
evaluations stay paused.

| id | Research question | Profile | Tool and key arguments | Expected | Guidance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R1 | Is the difference between two county estimates real, given their MOEs? | core | `calculate_significance` | answered | compare_counties |
| R2 | Is poverty associated with rent across independent areas? | core | `fit_model(formula)` | answered | regression_sampling_error |
| R3 | The same, but neighbouring counties are spatially correlated | core | `fit_model(spatial="scpc")` | validated | regression_sampling_error |
| R4 | A share with known trials (e.g. children in poverty) across correlated counties | core | `fit_model(model="binomial", trials=..., spatial="scpc")` | validated | regression_sampling_error |
| R5 | A naive binomial SCPC fit with a weak benchmark (`rho_bar` .10) | core | `fit_model(model="binomial", spatial="scpc")`; library `fit_scpc(rho_bar=.10)` | exploratory | regression_sampling_error |
| R6 | Overdispersed death counts with expected counts as exposure | core | `fit_model(model="negbin", exposure=...)` | answered | external_health_outcome |
| R7 | Death counts where small counties are suppressed as 1–9 | core | `fit_model(model="negbin", exposure=..., censored=...)` | validated | external_health_outcome |
| R8 | Six noisy ACS predictors with high reliability, correlated counties | core | `fit_model(method="eiv", spatial="clusters")`; library `fit_spatial_eiv` | validated | regression_sampling_error |
| R9 | Nine noisy ACS predictors, correlated counties | core | `fit_model(method="eiv", spatial="error")`; library `fit_spatial_eiv` | exploratory | regression_sampling_error |
| R10 | Did yearly rates change after a 2014 policy (18 annual points)? | full | `interrupted_series(interruption_year=2014)` | validated | tract_trend |
| R11 | The same with only 15 annual points | full | `interrupted_series` | exploratory | tract_trend |
| R12 | A "series" of overlapping ACS five-year releases | full | `interrupted_series` | refused (use `trend_test`) | tract_trend |
| R13 | Change across three non-overlapping ACS releases | core | `trend_test` | answered | tract_trend |
| R14 | How unequal are personal incomes (Gini)? | core | `test_association(kind="inequality")`; library `pums_inequality` | validated | pums_tests |
| R15 | The Theil T index of the same incomes | core | `test_association(kind="inequality")`; library `pums_inequality` | exploratory | pums_tests |

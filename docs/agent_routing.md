# Agent routing contract (Rounds 64, 103, 107, 110)

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
| R16 | Between-group disparity (ACS rates, CV ≤ .30) and WHO PAR | full | `disparity_measures(who_measures=True)` | validated | health_inequality |
| R17 | WHO mean difference from overall mean or best group | full | `disparity_measures(who_measures=True)` | exploratory | health_inequality |
| R18 | Joinpoint count in a 20-year annual rate series + EARS C2 aberration | full | `joinpoint(aberration="ears_c2")` | validated | policy_change |
| R19 | Staggered policy adoption across states (Sun–Abraham) | full | `difference_in_differences(design="staggered")` | validated | policy_change |
| R20 | Policy panel with treatment-confounder feedback (MSM) | full | `difference_in_differences(design="msm")` | exploratory | policy_change |
| R21 | Triple-difference policy design (eligible vs ineligible groups) | full | `difference_in_differences(design="triple")` | validated | policy_change |
| R22 | Stratified 2×2 tables: Mantel–Haenszel RR/OR/RD and RERI | full | `stratified_analysis` | validated | confounding |
| R23 | Area threshold designation probability (Fay–Herriot posterior) | full | `designation_accuracy` | validated | small_area |
| R24 | Unmeasured-confounding E-value for a risk ratio | full | `bias_analysis(kind="e_value")` | validated | reporting |
| R25 | Causal effect with overlap weights and positivity diagnostics | full | `estimate_effect(weights="overlap")` | validated | causal |
| R26 | Nearest-neighbour matching ATE (Abadie–Imbens) | full | `estimate_effect(kind="matching")` | validated | causal |
| R27 | Sharp RDD at an age cutoff on PUMS with replicate weights | full | `regression_discontinuity` | validated | causal |
| R28 | BYM2 spatial disease map (relative-risk intervals exploratory; exceedance calibrated) | full | `spatial_model(kind="disease_map")` | exploratory | spatial_patterns |
| R29 | FCS multiple imputation (PMM) with 3 incomplete variables | core | `fit_model(impute=[...], impute_method="pmm")` | validated | regression_sampling_error |
| R30 | Abridged life table (e0/e65) and YPLL-75 from WONDER age-group exports | full | `demography_analysis(kind="life_table")` | validated | external_health_outcome |
| R31 | Random-effects meta-analysis prediction interval, meta-regression and Egger test (k ≥ 10) | full | `combine_estimates` | validated | reporting |
| R32 | Nearest-neighbour matching ATT with Kish effective-df | full | `estimate_effect(kind="matching", method="nn_att")` | validated | causal |
| R33 | BYM2 spatial disease map (`method="B3"`, median E ≥ 30) | full | `spatial_model(kind="disease_map", method="B3")` | validated | spatial_patterns |
| R34 | Continuous-running-variable sharp RDD (CCT CER bandwidth) | full | `regression_discontinuity` | validated | causal |
| R35 | Probabilistic misclassification quantitative bias analysis | full | `bias_analysis(kind="misclassification", prior_sd=...)` | validated | reporting |
| R36 | Policy panel with treatment-confounder feedback via parametric g-formula | full | `difference_in_differences(design="msm", method="gformula")` | validated | policy_change |
| R37 | Observed Lin's CCC agreement between two area sources | full | `check_agreement` | validated | reporting |
| R38 | Designation PPV predictive interval (`rule="prob80"`, Round 107) | full | `designation_accuracy`; library `designation_accuracy(ppv_intervals=True)` | validated | small_area |
| R39 | Multi-confounder policy panel with treatment-confounder feedback (`p = 2`, Round 108) | full | `difference_in_differences(design="msm", method="gformula")` | validated | policy_change |
| R40 | Joinpoint AAPC bootstrap-t interval (18 annual points, 200+ events/yr, Round 109) | full | `joinpoint`; library `joinpoint(...)["aapc_bootstrap_t"]` | validated | policy_change |

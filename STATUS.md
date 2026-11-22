# Project status

The single current summary of the Census Research Engine: what it does, which methods are validated, the
standing rules, and what is next. Read this instead of old plans. Updated each round when it merges.

**Current release:** v0.77.0 (Rounds 76–81: disparities, joinpoint, staggered DiD, decompositions, small-area
proportions, spatial scan; DOI 10.5281/zenodo.24444186). Previous: v0.71.0 (Round 75 and the local-model evaluation; DOI 10.5281/zenodo.24434858); v0.70.0 (Rounds 70–74; DOI 10.5281/zenodo.24433164); v0.65.0 (Round 69;
DOI 10.5281/zenodo.24411452); v0.64.0 (Rounds 64–68; DOI 10.5281/zenodo.24405380); v0.60.0 (Rounds 61–63; DOI 10.5281/zenodo.24400452); v0.57.0 (Rounds 57–60; DOI 10.5281/zenodo.24398149); v0.53.0 (Rounds 43–56; DOI 10.5281/zenodo.24384786); v0.39.0 (Rounds 31–42, the statistics roadmap; DOI
10.5281/zenodo.24371310); v0.27.0 (Round 30: IM-8 with ACS sampling error; DOI
10.5281/zenodo.24357238); v0.26.0 (Round 29: WONDER mortality, replicated in OH/PA; DOI 10.5281/zenodo.24356572). All versions: concept record
[zenodo.org/records/23925301](https://zenodo.org/records/23925301). Per-round detail: `CHANGELOG.md`.

## Where things are

| Path | What |
| :--- | :--- |
| `census/` | Library. `manifest/` package (pre-registered studies: `schema`, `validate`, `create`, `run` (typed `RunState` and ordered execution stages), `methods_text`, `methods` (single method registry), plus `adjustments`, `replicates`, `external`, `derivations`, `datasource`; import from `census.manifest`, but patch tests at the submodule that looks the name up), `models.py` (`fit_replicate`, `fit_eiv`, robust GLM SEs), `health_sources.py` (PLACES, USALEEP, CHR&R, WONDER exports), `spatial*.py`, `sae*.py`, `simulation*.py` (validation studies) |
| `mcp_server.py` | MCP server (78 tools; 16 in `core`, 17 in `core_spatial`; profiles in `census/mcp_profiles.py`) |
| `docs/agent_protocol.md`, `docs/recipes/` | What agents are told; keep in step with engine rules |
| `docs/audits/` | Validation reports (pass/fail, reproducible scripts in `scripts/`) |
| `docs/studies/` | Pre-registered study reports; outputs are release attachments, not in the repo |
| `examples/manifests/` | Registered manifests (their bytes are fixed once registered) |
| `PLAN_ROUND_<n>.md` | None queued (Rounds 82–87, from *Foundations of Epidemiology*, merged) (ecologic vs individual, last of the book's rounds); mapping in `docs/literature/foundations_of_epidemiology.md`. Implement only the lowest-numbered plan. Merged plans are archived (below) |
| `ROADMAP_BACKLOG.md` | Open items only (rewritten 2026-11-21; finished history at tag `backlog-r43-69`): N39 and N47–N52, Rounds 70–74 |
| `ROADMAP_STATISTICS.md` | Completed multi-round roadmap (Rounds 31–42, released as v0.39.0): SciPy/statsmodels methods wrapped for ACS replicates, PUMS weights and spatial dependence. Plans are drafted from it |
| `docs/data/wonder_exports.md` | Owner's guide to manual CDC WONDER exports (into gitignored `external_data/wonder/`) |

**Archived plans.** `PLAN_ROUND_1`–`22` are at tag `v0.21.0`, `PLAN_ROUND_23` at `v0.21.1`; from Round 24 on, each plan is at tag `plan-r<n>` (for example `git show plan-r29:PLAN_ROUND_29.md`). Code and docs still cite
them as labels (for example "PLAN_ROUND_16 A2"). To read one: `git show v0.21.0:PLAN_ROUND_16.md` (or the later tag), or
`https://github.com/cafeTechne/Census-Research-Engine/blob/v0.21.0/PLAN_ROUND_16.md`.

**Round 23 (v0.21.1, internal):** `census/manifest.py` became the `census/manifest/` package with no
behaviour change (478 golden snapshots identical; `scripts/refactor_golden.py`). `run_manifest` stages for a
later split are listed in `PLAN_ROUND_23.md` section 7 (at `v0.21.1`).

## Methods: validation status

Validated means a fixed, pre-set simulation or reference check passed. Failed methods stay exploratory only;
manifests refuse them in confirmatory analyses.

| Method | Status | Evidence |
| :--- | :--- | :--- |
| ACS derived estimates and MOEs (proportions, ratios, sums, medians) | Validated against Census-published values | `docs/audits/validation_report.md` |
| `fit_replicate` (OLS/WLS; 80 VRE replicate refits) | Validated: `population` 0.907, `these_areas` 0.897; `se_total` conservative (0.952–0.961) | `docs/audits/inference_validation.md` |
| `fit_eiv` (errors-in-variables) and its cluster jackknife | Validated (0.87–0.93) | `eiv_validation.md`, `eiv_cluster_validation.md` |
| Binomial/Poisson GLM with `scale: "robust"` (HC3) | Validated (0.879–0.897); required for external count outcomes | `robust_se_validation.md` |
| Binomial/Poisson with `scale: "X2"` (quasi-likelihood) | Failed under between-area overdispersion (0.689–0.79); refused for new manifests | `robust_se_validation.md` |
| Area SII / log RII / concentration (`inequality`, Round 24 implementation) | Passed fixed 90% conservative-interval validation: 0.876–0.905 for rank CV<=15%; high-error attenuation persists (CV30% information only). Independent areas. | `inequality_validation.md` (criterion `60330e3`) |
| Indirect SMR (`smr`, Round 24 implementation) | Passed combined Poisson/ACS log-interval validation: 0.893–0.909; rates fixed, independent band errors; negative band replicates refused. Exact Garwood limits condition on E. | `smr_validation.md` (criterion `680707e`) |
| Spatial CR1-t, G=8 (`cr1_t`, C1-8) | **Failed**: coverage 0.800–0.895; exploratory only | `spatial_cluster_validation.md`, criterion `46ec2ec` |
| Spatial CR1-t, G=12 (`cr1_t`, C1-12) | **Failed**: coverage 0.773–0.901; exploratory only | `spatial_cluster_validation.md` |
| Ibragimov–Müller, G=8 (`im`, C2-8) | **Passed**: 0.886–0.912; unweighted OLS/binomial, population only, no analysed ACS replicates; every cluster full-rank and >=5 units | `spatial_cluster_validation.md` |
| IM-8 C1 with ACS sampling error | **Passed** observed-estimate targets: linear .8790–.9130; binomial .8690–.9060; Poisson .8695–.9235. Population only, fixed Poisson E, no additive ACS variance. Constant cluster terms absorbed; no true-slope correction. **OH/PA re-check (Round 44): failed** with spatially correlated fields (.70–.85; independent cells .89–.91): exploratory outside MI/NY, with an engine note | `im_acs_validation.md`, criterion `2774140`; `ohpa_revalidation.md`, criterion `09ecd91` |
| IM-8 C2 cluster Fuller EIV | **Failed**: .0695–.9035 coverage; corrected-matrix failures up to 92.6%. Refused, no naive fallback | `im_acs_validation.md` |
| Restricted wild cluster bootstrap, G=12 (`wcr`, C3-12) | **Failed**: coverage 0.824–0.908; exploratory only, no ACS replicate combination | `spatial_cluster_validation.md` |
| Poisson–Gamma descriptive EB rate smoothing | **Passed** fixed 90% area-average criterion: posterior 0.8813–0.9000 (default); Laird–Louis 0.8718–0.8914 in six required cells. Fixed E/rates, independent areas; [1,9] censoring; 200 bootstrap refits for LL | `eb_rate_validation.md`, criterion `d4dec47` |
| Centered natural splines / joint chi-squared Wald | **Failed**: nominal .10 size 0.1055–0.1825; four cells exceed .13. `joint_wald` stays exploratory; binomial/Poisson splines are confirmatory only with `joint_test` (Round 31) | `joint_wald_validation.md`, criterion `376ce69` |
| Joint (omnibus) tests: `joint_test` | **Passed selected** (nominal .10 size in [.07,.13]): wild score bootstrap for OLS factor tests (.098–.110) and binomial/Poisson spline tests (.072–.103); IM-8 Hotelling for OLS/Poisson factor tests (.093–.103). F references failed everywhere. n = 145; other combinations exploratory | `omnibus_validation.md`, criterion `3e3094a` |
| Missing data, censored counts, interrupted series | **Multiple imputation passed** (.907–.919; complete case .871 when missingness depends on the outcome). Interval-censored Poisson for hidden 1–9 counts failed narrowly (.839–.856; complete case .824–.828): exploratory. Interrupted series with 20 annual points failed for OLS, Newey–West and AR(1) GLS (.47–.81): exploratory | `missing_censored_its_validation.md`, criterion `5f81de2` |
| Segregation under realistic ACS error (Round 50) | **Passed** (real 2024 MI/NY tract counts and MOEs; Gamma counts; group correlation 0 and −.3): bias-corrected D, isolation and H (two groups) and bias-corrected three-group H up to county noise level .50 (largest group median tract CV); naive isolation/H to .30. **Failed**: naive D (the Round 28 default) and naive three-group H. Defaults now all bias-corrected; 132 of 140 MI/NY counties validated (Round 28 gate: 0–1) | `segregation_realistic_validation.md`, criterion `686d121` |
| Survey-weighted PUMS models (Round 49) | **Passed**: ordered logit and probit, multinomial logit, weighted median regression and probit with the SDR replicate variance (80 warm-started refits; .875–.915 with household clustering ρ up to .4 and weight CV up to 1). Model-based SEs with normalised weights under-cover (.62–.887) | `pums_models_validation.md`, criterion `c0dfd0a` |
| Segregation beyond poverty and income (Round 52) | **Passed** (real 2024 B03002 tract counts and MOEs, MI/NY and OH/PA; ranges combine every design judging a noise bin): bias-corrected D [.15, 1.0), isolation any finite noise level, two-group H below 1.0; four- and five-group bias-corrected H any finite level (bin means .953–.997); release contrasts (2015–2019 vs 2020–2024) with the larger noise level below .50 (.869–.971). **Failed**: naive isolation/H for race groups at .15–.50 (lost their Round 50 range), naive D, naive multigroup H; D and H above noise 1.0 for Black/non-Black. Infinite noise never validated | `segregation_groups_validation.md`, criterion `b19696b` |
| Negative replicate estimates (Round 51) | **Passed**: segregation with negative replicate counts clipped at zero before the refits (Gaussian replicates; bias-corrected D/isolation/H and three-group H keep their Round 50 ranges to noise .50; affected county-draws .902–.990); SMR with negative band replicates used as published (.903–.922) or clipped (.891–.917). **Failed**: naive isolation/H with clipped cells (.847–.860). Library defaults clip (segregation) and accept (SMR); manifests opt in | `negative_replicates_validation.md`, criterion `2837bfb` |
| Small samples and spatial dependence (Round 48) | **Passed**: effective-sample-size intervals under spatial dependence for Spearman (.875–.917), Kendall (.862–.905), Pearson with replicates (.864–.967) and Feldt α (.912–.926) (`spatial=True`; partial correlations stay exploratory; IM-8 versions failed); Hartung–Knapp for 5–10 estimates with the variance factor truncated at 1 (.874–.918); Bland–Altman limits with moment-based SEs (.884–.936); interrupted series AR(1) bootstrap-t at 30+ points (.883–.896). **Failed**: REML AR(1) at 15–30 points (.79–.88) and bootstrap-t below 30 points | `small_spatial_validation.md`, criterion `3fb07d3` |
| Causal robustness (Round 47) | **Passed**: AIPW with confounders calibrated within treatment groups (`calibrate=True`; .889–.905 with same-sign noisy confounders, plain AIPW .77–.87); calibrated mediator (.883–.898; naive .58–.86); Anderson–Rubin interval at any first-stage F (.894–.908); the 2SLS Wald interval also covered at every F (pre-set cut-off 0) but its estimate is unstable below F = 10; chained-equations MI for two incomplete covariates (.898–.916; complete case .84 under MAR) | `causal_robustness_validation.md`, criterion `cbdc97f` |
| Causal tools (`estimate_effect`) | **Passed**: treatment effects (IPW/AIPW/RA) with precise confounders (.894–.899; residual confounding from noisy confounders not tested: design limitation); 2SLS with an independent second measurement (.882–.907 vs naive OLS .30); mediation with an exact mediator (.876–.891; mediator error .69–.72, exploratory) | `causal_validation.md`, criterion `b7464e5` |
| Beta and median regression (`fit_model` beta/median) | **Passed selected**: beta with HC0 (.885–.903; model-based SEs failed); median regression with the kernel SE (.912–.917). Replicate-augmented variants over-cover. PUMS models: Round 49 row; GEE deferred | `beta_median_validation.md`, criterion `d5c9b02` |
| Multivariate group tests and count models | **Passed**: multivariate wild score bootstrap (MANOVA/MANCOVA; size .090–.101); NB2 with HC3 (.885–.901, overdispersion and excess zeros). **Poisson HC3 under-covered with strong overdispersion (.808–.867)**; zero-inflated Poisson failed | `manova_counts_validation.md`, criterion `0686bc0` |
| Combining evidence (`combine_estimates`) | **Passed selected**: Paule–Mandel + Hartung–Knapp pooling for 2–4 estimates (.885–.911; 5–10 with truncation since Round 48); fixed effect only when homogeneity is declared in advance; TOST equivalence; z-test power. DerSimonian–Laird failed with heterogeneity (.82–.84) | `evidence_validation.md`, criterion `3edd5f4` |
| Agreement between sources (`check_agreement`) | **Passed selected**: bias (.894–.900) and kappa of quintile classes (.883–.912). Failed (estimates only, intervals exploratory): Bland–Altman limits observed (.838) and error-free (.826; both repaired in Round 48), Lin's CCC (.859) and corrected CCC (.38–.77) | `agreement_validation.md`, criterion `e6d4be6` |
| Spatial scan (Round 81) | **Passed**: Kulldorff Poisson scan, primary-cluster Monte Carlo test at α .10 has size .099–.116 (MI+NY and OH+PA counties, 5–100 expected per county, 50% windows, 999 replicates). Reported: power and location accuracy; with 5% ACS-like denominator error the size inflates to .15–.53, so noisy denominators are exploratory | `scan_validation.md`, criterion `b6b69d0` |
| Small-area proportions and several releases (Round 80) | **Passed** (real 2019–2023 S2701 sampling variances, MI/NY counties and tracts): arcsine Fay–Herriot with bias-corrected back-transform and bootstrap MSE, per-area coverage .898–.904, worst decile ≥ .880, relative bias ≤ .078 for p < .10 (quantile interval .892–.895 also passes); Rao–Yu temporal Fay–Herriot for 2–3 releases .897–.898 (MSE gain 3–7% counties, 10–24% tracts) | `sae_extensions_validation.md`, criterion `251dc9d` |
| PUMS gap decompositions (Round 79) | **Passed with size gates** (Round 32 design, weight CV 1, SDR intervals): Oaxaca–Blinder explained/unexplained totals from 300 records in the smaller group (.862–.894); Oaxaca–Blinder detailed contributions (Yun-normalised) and Fairlie totals and detailed contributions from 1,000 records (.863–.894); at 300 they under-covered (.802–.853) | `decomposition_validation.md`, criterion `9e52bb4` |
| Staggered adoption and synthetic control (Round 78) | **Passed selected** (51 units, 12/18 annual periods, AR(1) .3/.7, ACS-like error): Sun–Abraham event study and overall ATT (.881–.899); Callaway–Sant'Anna with the ACS variance added (.882–.906). **Failed**: Callaway–Sant'Anna multiplier bootstrap alone (.848–.868), uniform bands (.76–.81), synthetic-control placebo test (size .12–.19 at .10) and conformal intervals (.73–.86 with 9 pre-periods; .87–.95 with 15, not a pre-set gate): exploratory, library only | `policy_validation.md`, criterion `baf934b` |
| Ecologic vs individual (Round 87) | **Passed**: logit within/between/contextual decomposition on PUMS with SDR SEs (.871–, 30 or 150 PUMA-like areas, 5,000+ records). **Failed**: the identity-scale (risk-difference) decomposition and the ecologic slope and gap with 150 small areas (.62–.86; noisy area means bias the between slope): exploratory | `ecologic_validation.md`, tag `criterion-r87` |
| Bias analysis (Round 86) | E-values reproduce VanderWeele and Ding's published example (deterministic; available everywhere). **Failed**: the probabilistic misclassification interval (.76–.83 under correct priors with a null effect or exposure misclassification; about 1.00 with differential outcome misclassification): exploratory. The simple correction is unbiased (point correction, no interval) | `bias_analysis_validation.md`, criterion `734cce5` |
| Designation accuracy (Round 85) | **Passed**: Fay–Herriot posterior probability that an area truly exceeds a threshold (calibration within .031 in every bin, MI/NY tracts and counties). **Failed**: the flat-prior direct probability (off by up to .17) and the rule-accuracy criterion (expected Sn/Sp/PPV/NPV agreed within about .01 on average, but the PPV predictive interval under-covered on tracts, .54–.85): exploratory | `designation_validation.md`, criterion `61fa47a` |
| Marginal measures (Round 84) | **Passed** (every candidate): g-computation risk ratio, risk difference and attributable fraction for area binomial models with HC3 delta SEs (.862–.898) and for PUMS logit models with SDR SEs (.866–); modified-Poisson prevalence ratios with SDR SEs (.869–); dose-response trend tests (size .083–.129) | `epi_measures_validation.md`, criterion `c5f6266` |
| Stratified analysis (Round 83) | **Passed**: Mantel–Haenszel RR, OR, RD and IRR for counts (.877–.906, down to 5 expected cases per stratum and arm); MH RR/OR/RD on PUMS with SDR weights (.881–.909, from 300 records per stratum); RERI by delta, bootstrap and SDR (.887–); Breslow–Day–Tarone homogeneity (size .102–.114). **Failed**: Woolf RR homogeneity (size .032–.113, conservative with sparse strata) and the PUMS replicate Wald homogeneity test (.099–.151): exploratory | `stratified_validation.md`, criterion `b358799` |
| Joinpoint and age-adjusted rate ratios (Round 77) | **Passed selected**: the number of joinpoints by Kim et al. permutation tests (false-joinpoint rate .012–.023 at α .05; 15–25 annual points, 50–5,000 events per year); Tiwari (.900–.921) and log-delta (.887–.900) intervals for ratios of age-adjusted rates. **Failed**: APC intervals (t given the true number .51–.91; empirical-quantile with selection .02–.88) and AAPC intervals (.75–.92): exploratory, because joinpoint locations are estimated | `joinpoint_validation.md`, criterion `01ad5a4` |
| Between-group disparities and Kitagawa (Round 76) | **Passed selected** (90% coverage ≥ .86 in every cell; 2–6 groups): ACS replicate intervals for the rate difference (.879–.924) and Index of Disparity (.875–.919) up to a largest group-rate CV of .50; log rate ratio, between-group variance, Theil and MLD up to CV .30 (at .50: .50–.84). Counts: Poisson delta rate difference and log ratio from 20 expected events (.888–.911); bootstrap count index measures **failed** (.07–.84: exploratory). Kitagawa rate and composition effects passed everywhere (.887–.927; CV to .50, 20+ events per stratum) | `disparity_validation.md`, criterion `e995978` |
| Three-level models and published-loading indices (Round 73) | **Passed**: three-level random-intercept fixed-effect intervals with t(G_top − 1) (`multilevel_model(groups=[top, middle])`; .904–.913 with 30 or 49 top units, unbalanced, two share splits); per-area intervals of indices with fixed published loadings (`build_index(method="loadings")`; mean .897–.899, every area ≥ .878). **Screening only** (100 draws, stays exploratory): jackknife variance-share intervals (.88–.98). Parametric bootstrap dropped before the run (too slow) | `methods73_validation.md`, criterion `e97e9fc` (tag `criterion-r73`) |
| Composite index scores and Cronbach's α (`build_index`) | **Passed**: per-area score intervals (PCA and equal weights; mean coverage .898–.899, every area ≥ .874); Feldt α interval for independent areas (.891–.912; under-covers with spatial dependence, .58–.67; Round 48 effective-n repair). Quintile stability and typologies descriptive | `index_validation.md`, criterion `e86907d` |
| Replication D (Round 69) | **Replicated**: Monnat 2018 Model 4 (county drug-related mortality 2006–2015 on ACS 2010–2014 economic distress, spatial error, state FE): 9.95 (7.77–12.12) vs 9.62; sample counts match exactly (3,106; 2,484). Spatial error slope coverage on national counties .908/.881 (passes) | `r69_monnat_replication.md`, `r69_county_sem_validation.md`, criterion `20a4c13` |
| Replication E (Round 68) | **Replicated**: Boing et al. 2020 headline: tract/county/state shares of US life-expectancy variation 70.0/10.6/19.4% vs 70.4/10.7/19.0% (USALEEP; counts match exactly). Three-level model via statsmodels (engine is two-level only: N46) | `r68_le_variance_replication.md`, criterion `110c22e` |
| Tract-level spatial intervals (Round 71) | **Passed** (NC 2018 and MI 2020 tracts, fields correlated over 0–100 km): SCPC for OLS slopes with ρ̄ .20 (.885–.972; the tract default) and .30 (.932–.988). **Failed**: the spatial error ML slope interval (.63–.76 beyond 20 km) and HC3 (.10–.26 beyond 0 km). Tract Poisson and binomial SCPC are untested and stay exploratory | `tract_spatial_validation.md`, criterion `f947f64` |
| Replication C and SCPC at tract level (Round 67) | **Partly replicated**: Mitchell et al. 2022 (NC tract life expectancy on ICE), 5 of 6 slopes; ICE Race and Income match to the printed digit (R² 19.60%, 48.19% exact); the combined index's OLS slope is 13% larger (definition). **SCPC failed on NC tracts** at 100 km (.75/.81; HC3 .12–.26), so tract-level SCPC with ρ̄ .05/.10 is exploratory (Round 71 validated .20/.30) | `r67_nc_ice_replication.md`, `r67_nc_tract_validation.md`; plan `e75a41b`, criterion `14b78b2` (deviation 2) |
| Replication suite (Round 74) | **All five reruns agree** with their original audits through the engine's own routes (A exact against CHR, 2,055 counties; B within 5e-6; C 0; D 2e-14; E 1e-10). Reruns, not new registered results | `replication_suite.md`, `docs/replications/` |
| Replications and segregation on new geometry (Round 66) | **Replicated**: CHR 2025 county Black/White dissimilarity (2,055 counties, exact); Census state Gini B19083 from PUMS (median difference .0008; 10 of 12 intervals contain it). **Simulation on GA/TX/AZ**: isolation and H pass; bias-corrected D failed at noise .75–1 on TX (16 of 18 counties ≥ .80), so its range now ends at .75 | `r66_numeric_replication.md`, `r66_segregation_geometry_validation.md`, criterion `dd48bf6`/`d30d7ed` |
| Small samples and many covariates (Round 63) | **Passed**: conservative bootstrap-t (`bootstrap_t_cons`) for interrupted series from 17 points (.865–.896); bootstrap-bias-corrected variant from 19; G1 with up to 8 and G2 with up to 7 error-prone covariates when every reliability ≥ .8. **Failed**: every interrupted-series method at 15 points (.849–.855); G2 with 8 (.856) | `small_many_validation.md`, criterion `ac2f34c` |
| Leftover failures (Round 62) | **Passed**: binomial SCPC with ρ̄ .15 (.886–.954) and .20; clipped six-group bias-corrected H at any finite noise level. **Failed**: Theil T also with 8,000 households (.858): exploratory at every sample size tested | `leftover_failures_validation.md`, criterion `8f14e39` |
| PUMS inequality repairs (Round 60) | **Passed** with logit-transformed SDR intervals: Atkinson (ε 1) everywhere (.872–.893); Atkinson (ε .5) and the top-decile share with at least 7,000 records (≥ .871 at 3,000 households). **Failed**: Theil T (.820, .859 at 3,000 households); the SDR bias correction lowered coverage | `pums_inequality_repair_validation.md`, criterion `60a3b06` |
| Correlations under spatial dependence (Round 59) | **Passed**: partial correlations with the effective n of the residual series (one control, replicates; .869–.971 on MI/NY and OH/PA; independent-area partial .689); Round 48's effective-n Spearman, Kendall, Pearson (.880–.965) and α (.901–.933) replicate on OH/PA | `spatial_correlation_validation.md`, criterion `669a506` |
| Spatial inference outside MI/NY (Round 58) | **Passed**: SCPC intervals for naive slopes on MI/NY and OH/PA, OLS with ρ̄ .05 (.861–.930) and Poisson with ρ̄ .10 (.863–.934); G1/G2 with three to five error-prone covariates when every reliability is ≥ .8 (.886–.934, both regions); calibrated binomial slopes with IM-8 (.877–.907). **Failed**: binomial SCPC (.793/.846); IM-8 OLS in the low-reliability, correlated MI/NY cell confirmed at .858 (10,000 draws) | `spatial_outside_validation.md`, criterion `e8c6c8c` |
| Segregation gaps (Round 57) | **Passed**: clipped replicates on race designs above noise .50 (bias-corrected isolation to .75, two-group H to 1.0, four- and five-group H at any finite level; D stays at .50); six-group bias-corrected H at any finite level; same-release county contrasts to .50 for every variant except corrected D (.855). Group-quarters tract exclusion added as a definitional option | `segregation_gaps_validation.md`, criterion `8bcad0b` |
| PUMS income inequality (Round 56; `test_association(kind="inequality")`) | **Passed** (Round 32 generator; lognormal, heavier-tailed and zero-inflated incomes; SDR replicate variance): Gini (.861–.908), log P90/P10 and log P80/P20 (.888–.923), Gini difference between two groups (.873–.899). **Failed**: Theil T (.811), Atkinson .5 (.845) and 1 (.858), top-decile share (.850) in their worst cells. Heaped quantiles flagged as for medians | `pums_inequality_validation.md`, criterion `d91201b` |
| Short series and estimated reference populations (Round 55) | **Passed**: interrupted series with the bootstrap-t at a bias-corrected AR coefficient (`method="bootstrap_t_bc"`) for 20+ annual points (.867–.889; .857 at 15 points); SMR with survey-estimated reference person-years (`reference_population_se`; .892–.908). **Failed**: EWC HAR t test (.616–.720) | `short_series_reference_validation.md`, criterion `dd6d6b7` |
| OH/PA external validity, part 2 (Round 54) | **Replicated on OH/PA**: IM-8 count slopes (Round 45; .891–.911), calibrated IM-8 count slopes (Round 53; .875–.912), G2 with three or four error-prone covariates (.861–.920). **Failed on OH/PA** (reliability .7, 100 km fields; MI/NY validation kept, engine note): G1 with three to five covariates (.850–.859), G2 with five (.807). **Repair failed**: naive IM with 4 or 6 within-state clusters (OH/PA worst cells .827, .753; MI/NY passed). A fresh-seed MI/NY rerun of naive IM-8 covered .849 in one cell (linear, 100 km, reliability .7) | `ohpa_revalidation2.md`, criterion `e42840d` |
| Corrected GLM slopes, part 2 (Round 53) | **Passed**: regression calibration with delete-one-area jackknife SEs (t, n − p df) for binomial (.882–.904; the bootstrap failed at .851), Poisson (.886–.904) and NB2 (.897–.908); pooled calibration + IM-8 count slopes under spatial dependence for Poisson (.877–.904) and NB2 (.894–.909; naive IM-8 .349–.890); G1/G2 with five error-prone covariates (.864–.925; at reliability .7 with correlated fields up to 10% failed fits and very unstable estimates). **Failed**: six covariates (.804–.811) | `glm_correction2_validation.md`, criterion `8d48956` |
| GLM regression calibration (Round 46) | **Passed** for Poisson (.869–.893) and NB2 (.887–.918) against the true slope (two error-prone covariates, reliability .7–.9, error correlation 0–.3; naive GLMs .38–.85); **binomial failed** (.851–.889): exploratory, refused in confirmatory manifests | `glm_correction_validation.md`, criterion `4aceb22` |
| Count repairs (Round 45) | **Passed**: interval-censored NB2 for hidden 1–9 counts .869–.898 (censored Poisson .83–.86); IM-8 count slopes, NB2 at the full-sample α .896–.909 and Poisson .894–.905 (pooled NB2-HC3 fell to .80 with spatial correlation; MI/NY geometry); NB2 with noisy ACS exposures held fixed .888–.891 (Poisson .83–.86) | `count_repairs_validation.md`, criterion `0c368dd` |
| Corrected EIV slopes under spatial dependence (`fit_spatial_eiv`) | **Passed**: G1 pooled-correction IM-8 .879–.899; G2 SAR-whitened Fuller .863–.918 (true slope; reliability .7–.9; independent and 100 km fields; up to two error-prone covariates; **Round 46: three and four also pass**, .876–.927, with unstable point estimates at reliability .7 and correlated fields). Library, MCP and (Round 43) manifests via `fit_eiv` `args.spatial`. **Replicated on OH/PA (Round 44):** G1 .867–.909, G2 .863–.921 | `spatial_eiv_validation.md`, criterion `46fab40`; `ohpa_revalidation.md` |
| Rank intervals and area-versus-reference comparisons (`rank_areas`) | **Passed** (conservative): Klein–Wright–Wieczorek individual (coverage ≥ .999) and joint rank intervals; Holm and simultaneous comparisons with a weighted reference (FWER ≤ .109; joint coverage .894–.907). Bootstrap percentile ranks failed (per-area coverage down to .33) and are not offered | `ranking_validation.md`, criterion `6286ad9` |
| Rank/partial correlation and rank group tests | **Passed selected** (coverage ≥ .86, independent areas): Spearman and Kendall Fisher-type intervals; Pearson and partial (one control) only with the ACS replicate variance added (plain Fisher-z under-covered, .84); Brunner–Munzel superiority; Kruskal–Wallis size .095–.106. All correlation intervals under-cover with spatial dependence (.60–.89; Round 48 effective-n repair for Spearman, Kendall, Pearson). **Manifest `correlation` statistics still use the plain Fisher-z interval (not validated for Pearson)** | `rank_validation.md`, criterion `f660e9c` |
| PUMS design-based tests (`test_association`) | **Passed selected**: first-order Rao–Scott for tables up to 3 × 4 (size .097–.115); k-group mean tests (design F, z); differences, OR, RR, mean/median differences (coverage .877–.913); Korn–Graubard proportions (.902–.947). Design-blind Pearson (.13–.53) and Wald proportions (.848) failed. Medians of heaped values exploratory | `pums_tests_validation.md`, criterion `d65d034` |
| Pairwise post hoc (`compare_groups`) | **Passed**: Holm for OLS/binomial/Poisson (FWER ≤ .117); simultaneous max-\|t\| for OLS only (.067–.070) | `omnibus_validation.md` |
| County segregation, two groups: D / isolation / H (Round 28) | **Passed selected variants** at CV .15 (Gaussian): naive D .898–.911; corrected isolation .877–.901; corrected H .896–.961. Corrected D and naive isolation/H failed there. Superseded as the main gate by Round 50 (below); the max-CV ≤ .15 range still validates | `segregation_validation.md`, criterion `4791763` |
| SMR period scaling and Poisson reference-rate uncertainty | **Passed** .8995–.9105; known reference person-years, independent bands, 50/500/5000 reference deaths and E=10/100. Common reference covariance preserved when pooling. No-reference coverage reached .724 | `smr_reference_validation.md`, criterion `134bf7f` |
| Conley spatial HAC SEs (`spatial_se`) | **Failed** (0.71–0.87 at 150 km); exploratory only | `spatial_hac_validation.md` |
| Spatial error model λ correction (ME-SEM) | Validated for λ > 0 (0.86–0.93); lag model at γ 0.6 under-covers | `spatial_regression_validation.md` |
| LISA under sampling error | Characterised, information only | `lisa_validation.md` |
| Tract 2010→2020 apportionment: 1:1 and merged | Validated | `rate_apportionment_validation.md` |
| Split tracts: default `missing`; opt-in `split: "dominant"` (≥0.95 share) | Dominant passed held-out OH/PA (ratio 0.913); general split failed | `rate_apportionment_retest.md` |

**Round 24 (v0.22.0):** a new manifest method is one `MethodSpec` entry in `census/manifest/methods.py`
(golden identical for the refactor; 516 snapshots now). New methods `inequality` (SII, log RII,
concentration index; ridits least to most deprived, positive = worse in more deprived areas) and `smr`
(combined interval drives tests; fixed-E Garwood limits reported only). Both assume independent areas.
Exploratory example: `docs/studies/r24_lbw_inequality_example.md`. Suite: 1703 passed, 37 skipped.

**Round 25 (v0.22.1):** `run_manifest` drives typed `RunState` stages in `run.py`.
Both offline goldens are required for manifest refactors; suite unchanged at 1703 passed / 37 skipped.

**Round 26 (v0.23.0):** IM-8 passed, CR1/WCR did not.
Cluster assignments and inference bases are explicit; no new MCP tools (63). Cached original residual
Moran I remains 0.195464 / 0.183552. IM comparisons are unavailable under the retained ACS/EIV
protocol; the authorized R21b unclustered OLS/ACS sensitivity is separate from unchanged EIV outputs
(`docs/studies/r26_posthoc_spatial_clusters.md`). No original study files were rewritten.
Acceptance: 1734 passed, 37 skipped (31 new tests); both legacy goldens byte-identical.

**Round 27 (v0.24.0):** descriptive `eb_poisson_gamma`
includes censored-count likelihoods, posterior mixtures, optional rate units and
explicit validation metadata; posterior default. `cr(df=3/4/5)` freezes centered
full-sample state in replicates; joint tests use full HC3/sampling covariance,
record df and refuse singular covariance. Both nonlinear features remain
exploratory after the failed criterion. No new dependencies or tools (63).
Acceptance: 1782 passed, 37 skipped, 49 subtests; 0 failures; 48 new tests. Golden differences are supported-statistic
messages, additive covariance diagnostics and dependent hashes only; existing
scientific values unchanged (`docs/audits/round27_compatibility.md`).

**Round 28 (v0.25.0):** `segregation` is one
registry entry with strict tract/group replicates, preset correction and per-index
variant gates. County contrasts preserve replicate covariance; non-overlapping
release contrasts add variances; one-area tests require an explicit null.
SMR accepts hashed `period_years` and `reference_counts`, annual rate units and
pooled common-reference variance. Reference person-years remain fixed; internal
standardization conservatism is noted. No new tools (63) or dependencies.
Acceptance: 1838 passed, 37 skipped, 50 subtests; 0 failures; 56 added tests. Schema golden changes only in
supported-method messages; execution golden byte-identical. See
`docs/audits/round28_compatibility.md`. No real-data study or later round started.

**Round 29 (v0.26.0):** manual-only WONDER inventory, pinned age/sex standards,
replicate-aware expected deaths and suppression-safe bundles. Both mortality manifests registered at
`150e172` before analysis. MI/NY and held-out OH/PA support all three poverty associations after Holm
correction; H2 is stable under both registered suppression sensitivities. Independence assumptions and
fixed model offsets remain limitations. See the two `r29_*.md` study reports. No WONDER network access.
Acceptance: 1860 passed, 37 skipped, 4 warnings, 50 subtests; 20 new tests; no failures. Legacy schema
snapshots unchanged; execution golden differs only for the intended WONDER fix (`round29_compatibility.md`).

**Round 87 (v0.83.0; merged, release pending owner approval; implemented by the maintainer agent):**
ecologic versus individual-level associations on PUMS (N64).
- `census/ecologic.py` (frozen core `ecologic_core.py`); option `pums_regression(ecologic_check=...)`; no new tool
  (78); `pums_tests` recipe section; protocol rule against the ecologic fallacy.
- Validation (`ecologic_validation.md`): the logit decomposition passes; the identity-scale decomposition and the
  ecologic gap fail with many small areas (exploratory).
- Example (`r87_ecologic_example.md`, exploratory): disability and income-to-poverty, MI and OH: the area-level
  slope is about 1.7 times the individual-level slope in both states.
- Goldens byte-identical. Acceptance: 2279 passed, 42 skipped; 0 failures.

**Round 86 (v0.82.0; merged, release pending owner approval; implemented by the maintainer agent):**
quantitative bias analysis (N63).
- `census/bias_analysis.py` (frozen core `bias_analysis_core.py`); tool `bias_analysis` (78 tools); E-values in
  `stratified_analysis` and the marginal measures; `reporting` recipe section.
- Validation (`bias_analysis_validation.md`): E-values exact; the probabilistic misclassification interval fails
  (exploratory).
- Example (`r86_bias_example.md`, exploratory): MI uninsured Black/White crude RR 1.53 (1.46–1.60), E-value 2.43;
  illustrative misclassification moves it to 1.97.
- Goldens byte-identical. Acceptance: 2276 passed, 42 skipped; 0 failures.

**Round 85 (v0.81.0; merged, release pending owner approval; implemented by the maintainer agent):**
area designations as screening tests (N62).
- `census/designation.py` (frozen core `designation_core.py`); tool `designation_accuracy` (77 tools); `small_area`
  recipe section.
- Validation (`designation_validation.md`, criterion `61fa47a`): the Fay–Herriot probability passes; the direct
  probability and the rule-accuracy criterion fail (exploratory).
- Example (`r85_designation_example.md`, exploratory): MI tracts at 20% poverty: the point rule designates 682 tracts
  (expected PPV .78), probability ≥ .8 designates 373 (PPV .94); 309 tracts change status.
- Goldens byte-identical. Acceptance: 2272 passed, 42 skipped; 0 failures.

**Round 84 (v0.80.0; merged, release pending owner approval; implemented by the maintainer agent):**
marginal risk ratios and differences, prevalence ratios, attributable fractions and dose-response (N61).
- `census/epi_measures.py` (frozen core `epi_measures_core.py`); options `fit_model(marginal=..., dose_levels=...)`
  and `pums_regression(marginal=...)`; no new tool (76).
- Validation (`epi_measures_validation.md`, criterion `c5f6266`): all candidates pass.
- Example (`r84_marginal_example.md`, exploratory): MI/NY county disability prevalence was 1.11 times as high at
  the 80th as at the 20th poverty percentile (1.07–1.16); linear dose-response p = .005.
- Goldens byte-identical. Acceptance: 2269 passed, 42 skipped; 0 failures.

**Round 83 (v0.79.0; merged, release pending owner approval; implemented by the maintainer agent):**
stratified analysis, Mantel–Haenszel pooling, homogeneity, additive interaction (N60).
- `census/stratified.py` (frozen core `stratified_core.py`); tool `stratified_analysis` (76 tools); recipe
  `confounding` (26 recipes); manifest `covariables` roles (mediators refused in formulas; effect modifiers must
  enter as interactions).
- Validation (`stratified_validation.md`, criterion `b358799`): MH measures and RERI pass; Breslow–Day passes;
  Woolf and PUMS Wald homogeneity fail (exploratory).
- Example (`r83_stratified_example.md`, exploratory): Michigan adults 19–64, disability and uninsurance by age band:
  MH RR .875 (.836–.915), the ratio weakens with age (labelled an effect modifier on the ratio scale).
- Goldens byte-identical. Acceptance: 2264 passed, 42 skipped; 0 failures.

**Round 82 (v0.78.0; merged, release pending owner approval; implemented by the maintainer agent):**
epidemiologic reporting conventions from *Foundations of Epidemiology* (N59); no new statistics.
- Measure types and design labels in manifest methods text and run info; generated limitations; interpretation
  templates; 95% display option; ACS allocation shares (`reliability_profile(allocation_tables=...)`); Table 1;
  design limitations in results bundles; association-language rule.
- Checks (`r82_reporting_checks.md`): B99 lines sum to published totals in all 145 MI/NY counties; Table 1
  reproduces direct tertile means. Median allocation in MI/NY counties: health insurance 20.5%, disability 12.1%.
- Goldens: intended changes only (methods text, two run-info keys, hashes); `round82_compatibility.md`.
  Acceptance: 2258 passed, 42 skipped; 0 failures.

**Round 81 (v0.77.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
Kulldorff Poisson spatial scan for county counts (N58).
- `census/scan.py` (frozen core `scan_core.py`): circular windows, LLR, Monte Carlo and Gumbel p-values, secondary
  clusters; WONDER suppression and noisy-denominator rules.
- Validation (`scan_validation.md`, criterion `b6b69d0`): size passes in every null cell; noisy denominators inflate
  size (.15–.53).
- Full-profile tool `spatial_scan` (75 tools); `spatial_patterns` recipe section.
- Example (`r81_scan_example.md`, exploratory): MI/NY low-birth-weight births (CHR&R), primary cluster Wayne County
  (RR 1.37, p .001).

Goldens: both byte-identical. Acceptance: 2249 passed, 42 skipped; 0 failures.

**Round 80 (v0.76.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
Fay–Herriot for proportions and across releases (N57).
- `census/sae_extensions.py` (frozen core `sae_extensions_core.py`): arcsine Fay–Herriot (bias-corrected
  back-transform, bootstrap MSE) and Rao–Yu temporal Fay–Herriot (bootstrap MSE).
- Validation (`sae_extensions_validation.md`, criterion `251dc9d`): all three candidates pass.
- `small_area_estimates(transform="arcsine" | temporal=True)`; no new tool (74); `small_area` recipe sections. No
  manifest change (manifest `fay_herriot` tests coefficients; the validated quantities are area estimates).
- Example (`r80_sae_example.md`, exploratory): MI tract uninsured rates, median 90% interval 4.70 points against
  5.60 direct; MI counties across 2014–2018 and 2019–2023.

Goldens: both byte-identical. Acceptance: 2245 passed, 42 skipped; 0 failures.

**Round 79 (v0.75.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
Oaxaca–Blinder and Fairlie decompositions on PUMS (N56).
- `census/decomposition.py` (frozen core `decomposition_core.py`): twofold Oaxaca–Blinder with the pooled reference
  and Yun normalisation, threefold reported; Fairlie with rank-matched orderings; SDR replicate-weight intervals.
- Validation (`decomposition_validation.md`, criterion `9e52bb4`): totals from 300 records, detailed parts and
  Fairlie from 1,000.
- Full-profile tool `decompose_gap` (74 tools); `pums_tests` recipe section with the interpretation rule.
- Example: `r79_decomposition_example.md` (exploratory): the MI uninsured gap between Black and White non-Hispanic
  adults 19–64 (2.54 points) is fully explained by composition (Fairlie 2.73; income-to-poverty 1.47).

Goldens: both byte-identical. Acceptance: 2239 passed, 42 skipped; 0 failures.

**Round 78 (v0.74.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
staggered-adoption DiD and synthetic control (N55).
- `census/staggered.py` (frozen core `policy_core.py`): Sun–Abraham (default) and Callaway–Sant'Anna event studies
  and overall ATT; synthetic control with placebo and conformal inference (library only, exploratory).
- Validation (`policy_validation.md`, criterion `baf934b`): Sun–Abraham and Callaway–Sant'Anna with the ACS variance
  pass; the bootstrap alone, uniform bands and synthetic control fail.
- `difference_in_differences(design="staggered", first_treated=...)`; `policy_change` recipe step 3. No new tool
  (73) and no manifest method (no annual panels in manifests).
- Example (`r78_medicaid_example.md`, exploratory): ACA Medicaid expansion and the all-ages state uninsured rate,
  ACS 1-year 2010–2023 without 2020: overall ATT −1.23 points (90% CI −2.18 to −0.27), flat pre-trends.

Goldens: both byte-identical. Acceptance: 2235 passed, 42 skipped; 0 failures.

**Round 77 (v0.73.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
joinpoint regression and age-adjusted rate ratios (N54).
- `census/joinpoint.py` (frozen core `joinpoint_core.py`): log-linear joinpoint model (WLS, grid search, Kim et al.
  permutation selection), APC/AAPC; Tiwari ratio of age-adjusted rates.
- Validation (`joinpoint_validation.md`, criterion `01ad5a4`): selection and both ratio intervals pass; APC and AAPC
  intervals fail and are exploratory.
- Full-profile tool `joinpoint` (73 tools); `policy_change` recipe step 4. No manifest method (series are annual
  external data; manifests are ACS five-year area frames).
- Example: skipped as the plan allows (the owner's WONDER exports are pooled five-year periods, not annual series); see the
  compatibility audit.

Goldens: both byte-identical. Acceptance: 2229 passed, 42 skipped; 0 failures.

**Round 76 (v0.72.0; merged, released in the bundled v0.77.0; implemented by the maintainer agent):**
between-group disparity measures and Kitagawa decomposition (N53).
- `census/disparity.py` (frozen core `disparity_core.py`): rate difference and log ratio against a declared
  reference group, Index of Disparity, between-group variance, Theil and MLD over groups, with replicate (ACS) or
  Poisson (count) intervals; Kitagawa rate/composition decomposition.
- Validation (`disparity_validation.md`, criterion `e995978`): see the methods table; count index measures failed.
- Manifest methods `disparity` and `kitagawa`; full-profile tool `disparity_measures` (72 tools); the
  `health_inequality` recipe gains a between-groups section.
- Example (`r76_disparity_example.md`, exploratory): MI/NY county family poverty by race/ethnicity (B17010H/I and a
  derived other non-Hispanic group; B17020 has no VRE file); Wayne minus Oakland poverty gap 13.1 points, of which
  age composition explains 0.3.

Goldens: run golden byte-identical; schema golden differs only in the supported-method list (intended). Acceptance:
2223 passed, 42 skipped; 0 failures.

**Round 75 (v0.71.0; merged, released as v0.71.0; implemented by the maintainer agent):** manifest
support for the Round 73 methods, tract coordinates, recipes and README; no new statistics.
- Manifests gain:
  - method `multilevel`, with two levels (`"groups": "county_fips"`) or three (`["state_fips", "county_fips"]`);
  - an `"indices"` block, whose weights are fixed in every replicate and which refuses circular use;
  - `expected_count` `person_years`.
- Tract frames without `Year` try both tract vintages for representative points.
- Six new recipes (25 in all) and a refreshed README.

Goldens: run golden byte-identical; schema golden differs only in the supported-method list (intended). Acceptance:
run golden byte-identical, schema golden differs only in the method list; 2213 passed, 42 skipped; 0 failures.

**Round 74 (v0.70.0; merged after Round 73, released in the bundled v0.70.0; implemented by the maintainer agent):**
replication suite, no new statistics (N52).
- The five published replications are specs in `docs/replications/`. Each records the published target, the
  pre-set rule, the original result, the engine route and a fixed tolerance.
- `census/replications.py` and `scripts/run_replications.py` rerun the specs and write
  `docs/audits/replication_suite.md`. A missing input (the owner's WONDER exports) is reported as skipped and never
  fetched.
- **Every rerun agrees** with its original audit. A matches CHR exactly; B, C, D and E match their audits to within
  rounding.
- Recipe `replications`.

Goldens unchanged. Acceptance: goldens byte-identical; 2203 passed, 42 skipped; 0 failures; live reruns 4 passed.

**Round 73 (v0.69.0; merged after Round 71, released in the bundled v0.70.0; implemented by the maintainer agent):**
methods the replications needed (N51; criterion `e97e9fc`, kept at tag `criterion-r73`).
- **Validated:** three-level random-intercept fixed-effect intervals (`multilevel_model(groups=["state",
  "county"])`, .904–.913) and per-area intervals of indices with published fixed loadings (`build_index(method=
  "loadings")`, mean .897–.899).
- **Exploratory:** jackknife intervals for the variance shares (screened on 100 draws, .88–.98).
- `census.wonder_reference.expected_counts` builds expected counts from a national WONDER age × sex file. It
  reproduces Round 69's expected deaths (maximum relative difference 7.8e-16).
- Example: replication E through `multilevel_model` gives Round 68's shares exactly (69.99/10.60/19.41%).

Goldens unchanged. Acceptance: goldens byte-identical; 2195 passed, 38 skipped; 0 failures.

**Round 71 (v0.68.0; merged after Round 72, released in the bundled v0.70.0; implemented by the maintainer agent):**
tract-level spatial intervals (N49; criterion `f947f64`).
- **Validated for tract OLS slopes** (NC and MI tracts, fields correlated up to 100 km): SCPC with rho_bar .20, the
  tract default (.885–.972), and .30 (.932–.988).
- **Failed:** the spatial error ML slope interval (.63–.76 once fields correlate over 20 km) and HC3.
- `fit_model` now warns when OLS residuals are spatially dependent (Moran's I, permutation p < .01) and names the
  validated route.

Goldens unchanged. Acceptance: goldens byte-identical; 2185 passed, 38 skipped, 2 Round 61 tests updated for the tract rules (rerun: 6 passed).

**Round 72 (v0.67.0; merged before Round 71, released in the bundled v0.70.0; implemented by the maintainer
agent):** context covariate sources, no new statistics (N50).
- `census/context_sources.py`: CBP, ERS typology, ERS rural–urban codes and CHR additional measures, with cached
  files pinned by SHA-256.
- Reached through `build_analysis_frame(context=[...])`, the manifest `"context"` block and
  `list_health_sources(kind="context")`.
- Tract requests were already one per state (no change needed).

Goldens unchanged. Acceptance: goldens byte-identical; 2179 passed, 38 skipped, 1 core-profile rule failure fixed (affected tests rerun).

**Round 70 (v0.66.0; merged, released in the bundled v0.70.0; implemented by the maintainer agent):**
housekeeping, no new statistics (N47, N48).
- `census/env.py` loads `.env` from `CENSUS_DOTENV`, then upward from the working directory, then from the package
  location, so an installed engine finds the project's key.
- `run_manifest(checkpoint=True)` saves each finished analysis and reuses it on a rerun with the same manifest and
  data.
- Progress lines go to stderr (`CENSUS_PROGRESS=0` silences them).

Goldens unchanged. Acceptance: goldens byte-identical; 2171 passed, 37 skipped; 0 failures.

**Round 69 (v0.65.0; merged, released as v0.65.0; implemented by the maintainer agent):**
replication D is replicated. The economic distress coefficient is 9.95 against the paper's 9.62, using the owner's
manual WONDER multiple-cause exports, with the Appendix Table A.1 codes verified from the author manuscript. The
spatial error model's slope interval is validated on the national county geometry. All five shortlisted
replication targets are now done (A, B, D, E replicated; C partly). Goldens unchanged. Acceptance:
goldens byte-identical; 2163 passed, 37 skipped; 0 failures.

**Round 68 (v0.64.0; merged, released in the bundled v0.64.0; implemented by the maintainer agent):** replication
E is replicated (headline only; paper not open access): 70.0% of geographic life-expectancy variation lies between
tracts, 10.6% between counties and 19.4% between states (published 70.4/10.7/19.0). Goldens unchanged.
Acceptance: goldens byte-identical; 2162 passed, 37 skipped; 0 failures.

**Round 67 (v0.63.0; merged, released in the bundled v0.64.0; implemented by the maintainer agent):**
replication C is partly replicated (5 of 6 slopes; ICE Race and Income exact). Simulation S found SCPC
under-covers on North Carolina tract geometry when fields correlate over 100 km, so `fit_scpc` marks tract-level
results exploratory. Deviation 2: the criterion file was a placeholder at `daa1d15` (a tool error). The plan's rule
governed S, and the full criterion was committed before C ran. Goldens unchanged. Acceptance: goldens byte-identical; 2161 passed, 37 skipped; 0 failures.

**Round 66 (v0.62.0; merged, released in the bundled v0.64.0; implemented by the maintainer agent):** first
registered replications (owner's choice A and B). CHR's county segregation index is reproduced exactly from
public ACS data, and the Census state Gini from PUMS within .001. The GA/TX/AZ simulation narrows bias-corrected
D's validated noise range to [.15, .75). Deviation 1 (descriptive interval part only) is recorded in the criterion.
Goldens unchanged. Acceptance: 2158 passed, 37 skipped; 0 failures.

**Round 64 (v0.61.0; merged, released in the bundled v0.64.0; implemented by the maintainer agent):**
agent access, no new statistics (N40–N43): the CLI runs every shared workflow; new MCP tool `interrupted_series`
(full profile) and `fit_model(model="negbin", censored=...)` for interval-censored NB2; `docs/agent_protocol.md` is
the single source of the rule passages, generated into `mcp_server.py` by `scripts/sync_rule_text.py` (five stale
copies corrected); core-profile text names only reachable tools; routing contract `docs/agent_routing.md` (15
questions, tested). Goldens unchanged. Acceptance: 2155 passed, 37 skipped; 0 failures.

**Round 63 (v0.60.0; merged, released in the bundled v0.60.0; implemented by the maintainer agent):**
small samples and many covariates (criterion `ac2f34c`): `interrupted_series(method="bootstrap_t_cons")` validated
from 17 points (`bootstrap_t_bb` from 19; nothing at 15); spatial EIV under the reliability gate with up to 8 (G1)
or 7 (G2) error-prone covariates. Demonstration (`r63_short_series_demonstration.md`). Goldens unchanged.
Acceptance: 2137 passed, 37 skipped; 0 failures.

**Round 62 (v0.59.0; merged, released in the bundled v0.60.0; implemented by the maintainer agent):**
leftover failures (criterion `8f14e39`): binomial SCPC validated at ρ̄ .15 (default) and .20; clipped six-group
segregation counties validated; Theil T confirmed exploratory (fails with 8,000 households). Exploratory example
(`r62_binomial_scpc_example.md`). Goldens unchanged. Acceptance: 2132 passed, 37 skipped; 0 failures.

**Round 61 (v0.58.0; merged, released in the bundled v0.60.0; implemented by the maintainer agent):**
manifest routing for spatial methods, no new statistics: `fit_replicate` `args.spatial_scpc` (with an SCPC p-value
consistent with the interval), `regression_calibration` `args.spatial: "clusters"` and `correlation_matrix`
`args.spatial: true`. Registered manifests unchanged; goldens unchanged. Acceptance: 2127 passed, 37 skipped; 0 failures.

**Round 60 (v0.57.0; released in the bundled v0.57.0; implemented by the maintainer agent):**
PUMS inequality repairs (criterion `60a3b06`): logit-transformed SDR intervals validate Atkinson (ε 1) and, from
7,000 records, Atkinson (ε .5) and the top-decile share; Theil T stays exploratory. `pums_inequality` reports the
interval method and applies the record gate. Exploratory example (`r60_inequality_repair_example.md`). Goldens
unchanged. Acceptance: 2121 passed, 37 skipped; 0 failures.

**Round 59 (v0.56.0; released in the bundled v0.57.0; implemented by the maintainer agent):**
correlations under spatial dependence (criterion `669a506`): effective-n partial correlations validated
(`correlation_matrix(spatial=True)` now covers them); Round 48's correlation and α intervals replicate on OH/PA
(targets recomputed for that geometry). Exploratory example (`r59_spatial_correlation_example.md`). Goldens
unchanged. Acceptance: 2117 passed, 37 skipped; 0 failures.

**Round 58 (v0.55.0; released in the bundled v0.57.0; implemented by the maintainer agent):**
spatial inference outside MI/NY (criterion `e8c6c8c`): SCPC (`census.scpc.fit_scpc`, MCP `fit_model(spatial="scpc")`)
validated for naive OLS and Poisson slopes on both regions; IM-8 OLS gets a note (.858 in a 10,000-draw rerun);
spatial EIV reports covariate reliabilities and is validated outside MI/NY at reliability ≥ .8; calibrated binomial
IM-8 slopes (`regression_calibration_clusters`). Exploratory example (`r58_scpc_example.md`). Goldens unchanged.
Acceptance: 2112 passed, 37 skipped; 0 failures.

**Round 57 (v0.54.0; released in the bundled v0.57.0; implemented by the maintainer agent):**
segregation gaps (criterion `8bcad0b`): clipped race-design counties validated above .50 for bias-corrected
isolation and H; six-group H validated; same-release county contrasts gated (corrected D refused); new
`exclude_tracts`, `group_quarters_tracts` and manifest `args.group_quarters`. Exploratory example
(`r57_segregation_gaps_example.md`): 114 and 130 counties validated for Black–non-Black and four-group H; prison
tracts drove Wyoming's H (.519 to .040 without them). Goldens unchanged. Acceptance: 2105 passed, 37 skipped; 0 failures.

**Round 56 (v0.53.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
PUMS income inequality (criterion `d91201b`): Gini, log P90/P10, log P80/P20 and Gini differences validated with
SDR replicate variance; Theil, Atkinson and the top-decile share fail and stay exploratory. New
`census.pums_inequality`; MCP `test_association(kind="inequality")` (no new tool). Exploratory Michigan example
(`r56_pums_inequality_example.md`). Goldens unchanged. Acceptance: 2100 passed, 37 skipped; 0 failures.

**Round 55 (v0.52.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
short series and estimated reference populations (criterion `dd6d6b7`): `interrupted_series(method="bootstrap_t_bc")`
validated for 20+ points (was 30+); the EWC HAR test failed; SMR `reference_population_se` (library and manifest
`args`) validated. Demonstration on simulated inputs (`r55_demonstration.md`; no suitable real input offline).
Goldens unchanged. Acceptance: 2094 passed, 37 skipped; 0 failures.

**Round 54 (v0.51.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
OH/PA external validity, part 2 (criterion `e42840d`): IM-8 count slopes and calibrated count slopes replicate on
OH/PA; G2 replicates with up to four error-prone covariates, G1 (three to five) and G2 (five) do not; IM with 4
or 6 within-state clusters does not repair naive IM outside MI/NY; one fresh-seed MI/NY IM-8 cell covered .849.
Engine notes only. Exploratory example (`r54_ohpa_im_example.md`). Goldens unchanged. Acceptance: 2088 passed, 37 skipped; 0 failures.

**Round 53 (v0.50.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
corrected GLM slopes, part 2 (criterion `8d48956`): `regression_calibration(se_method="jackknife")` validated
for binomial, Poisson and NB2 (closes backlog 4); `fit_count_model(spatial="clusters", calibrate=[...])` for
spatially correlated counts; spatial EIV validated with five error-prone covariates. MCP `fit_model(se_method=)`
and calibrated IM-8 route. Exploratory example (`r53_rc_example.md`): child poverty on income and unemployment;
jackknife SEs about 40–50% wider than the bootstrap's. Goldens unchanged. Acceptance: 2082 passed, 37 skipped; 0 failures.

**Round 52 (v0.49.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
segregation beyond poverty and income (criterion `b19696b`): race/ethnicity groups (B03002), four and five
groups, OH/PA and release contrasts. Bias-corrected ranges widen (D and two-group H to 1.0, isolation and
four/five-group H any finite noise); naive isolation/H fail race groups and are no longer validated; release
contrasts need the larger noise level below .50. Exploratory example (`r52_segregation_groups_example.md`):
102–126 of 145 MI/NY counties validated for race designs; clipped counties above .50 stay exploratory (N30).
Goldens unchanged. Acceptance: 2074 passed, 37 skipped; 0 failures.

**Round 51 (v0.48.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
negative replicate estimates (criterion `2837bfb`): clipping negative replicate group counts passes for the
bias-corrected segregation indices and three-group H (same noise ranges); naive isolation/H fail with clipped
cells. SMR accepts negative band replicates (accept and clip both pass). Library defaults `"clip"` and
`"accept"`; manifests keep `"refuse"` unless `args.negative_replicates` opts in. Exploratory example: all ten
county-designs Round 50 refused are now validated (`r51_negative_replicates_example.md`). Goldens unchanged.
Acceptance: 2066 passed, 37 skipped; 0 failures.

**Round 50 (v0.47.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
segregation under realistic ACS error (criterion `686d121`): bias-corrected D, isolation and H and
three-group H valid to county noise level .50; naive D failed, so all defaults are bias-corrected.
`segregation_replicate` reports `noise_level` and gates on it (`REALISTIC_RANGES`). Exploratory example
(`r50_segregation_example.md`). Goldens unchanged. Acceptance: 2058 passed, 37 skipped; 0 failures.

**Round 49 (v0.46.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
survey-weighted PUMS models (criterion `c0dfd0a`): ordered logit/probit, multinomial logit, median
regression and probit with the SDR replicate variance all pass. New frozen `census.pums_models_core`;
`census.pums_models.fit_pums_model`; MCP `pums_regression(model=...)`. Exploratory example
(`r49_pums_models_example.md`). Goldens unchanged. Acceptance: 2050 passed, 37 skipped; 0 failures.

**Round 48 (v0.45.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
small samples and spatial dependence (criterion `3fb07d3`): effective-n correlation and α intervals,
truncated Hartung–Knapp for 5–10 estimates, moment-based Bland–Altman limits and the ITS bootstrap-t
(30+ points) pass. New frozen `census.small_spatial_core`, flags in `census.small_spatial`; MCP
`correlation_matrix(spatial=True)`, `build_index(spatial=True)`. Exploratory example
(`r48_spatial_example.md`). Goldens unchanged. Acceptance: 2035 passed, 37 skipped; 0 failures.

**Round 47 (v0.44.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
causal and missing-data robustness (criterion `cbdc97f`): calibrated AIPW, calibrated mediation,
Anderson–Rubin intervals and two-covariate chained MI pass; 2SLS Wald covered at every F. New frozen
`census.causal_robustness_core`; `estimate_effect(calibrate=True)`, `impute=["w", "v"]`; plain AIPW with
noisy confounders is now labelled exploratory. Exploratory MI/NY example (`r47_causal_example.md`).
Goldens unchanged. Acceptance: 2027 passed, 37 skipped; 0 failures.

**Round 46 (v0.43.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
measurement-error-corrected GLM slopes and spatial EIV with more covariates (criterion `4aceb22`):
regression calibration passes for Poisson and NB2, fails for binomial (.851); G1/G2 pass with three and four
error-prone covariates. `RC_VALIDATED`, `VALIDATED_MAX_ERROR_COVARIATES = 4`; exploratory Round 29 example
with poverty's error corrected (slopes rise 4–10%). Goldens unchanged. Acceptance: 2015 passed, 37 skipped; 0 failures.

**Round 45 (v0.42.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
count-model repairs (criterion `0c368dd`): censored NB2, IM-8 count slopes and NB2 with noisy offsets pass.
New `census.count_repairs_core`; `fit_censored_negbin`; `fit_count_model(spatial="clusters")` and MCP
`fit_model(model="negbin", spatial="clusters")`; `within_states` cluster assignment. Goldens unchanged. Acceptance: 2007 passed, 37 skipped; 0 failures.

**Round 44 (v0.41.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
post hoc NB2 sensitivity of Round 29 (all three associations hold in both regions) and an OH/PA re-check of
the spatial validations (criterion `09ecd91`): corrected-slope G1/G2 replicate; naive IM-8 C1 fails with
spatially correlated fields. Engine notes for IM-8 outside MI/NY and for clusters crossing state borders;
NB2 optimizer fallback. Goldens unchanged. Acceptance: 1999 passed, 37 skipped; 0 failures.

**Round 43 (v0.40.0; released in the bundled v0.53.0; implemented by the maintainer agent):**
manifest routing and housekeeping, no new statistics. Opt-in manifest options: validated correlation
intervals, NB2 counts and spatial EIV. Saturated-model fix. Core-profile instructions cut from 12,480
to under 4,000 characters (bounded by a test at 8,000); tool counts corrected and tested. Acceptance: goldens identical; 1993 passed, 37 skipped; 0 failures.

**Round 42 (v0.39.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
missing data, censored counts and interrupted series; the last round of `ROADMAP_STATISTICS.md`.
Criterion `5f81de2` pushed before the run. New `census.mci_core`, `census.missing_censored_its`; MCP
`fit_model(impute=...)`. Goldens unchanged. Acceptance: 1977 passed, 37 skipped; 0 failures.

**Round 41 (v0.38.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
causal tools. Criterion `b7464e5` pushed before the run. New `census.causal_core`, `census.causal`,
MCP tool `estimate_effect` (full profile), recipe `causal`. Goldens unchanged. Acceptance: 1972 passed,
37 skipped; 0 failures.

**Round 40 (v0.37.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
beta and median regression. Criterion `d5c9b02` pushed before the run. New `census.beta_median_core`,
`census.regression_families`; MCP `fit_model(model="beta"|"median")`. Goldens unchanged. Acceptance:
1967 passed, 37 skipped; 0 failures.

**Round 39 (v0.36.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
multivariate tests and count models. Criterion `0686bc0` pushed before the run. New
`census.manova_counts_core`, `census.count_models`; MCP `compare_groups(outcomes=...)` and
`fit_model(model="negbin")`. Note for registered Poisson HC3 studies (R29): under strong
overdispersion that interval under-covered here; a sensitivity with NB2 is backlog, not a
reinterpretation. Goldens unchanged. Acceptance: 1963 passed, 37 skipped; 0 failures.

**Round 38 (v0.35.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
combining evidence. Criterion `3edd5f4` pushed before the run. New `census.evidence_core`,
`census.evidence`, MCP tool `combine_estimates` (full profile), recipe `combine_estimates`. Goldens unchanged.
Acceptance: 1957 passed, 37 skipped; 0 failures.

**Round 37 (v0.34.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
agreement between sources. Criterion `e6d4be6` pushed before the 8-cell run. New `census.agreement_core`,
`census.agreement`, MCP tool `check_agreement` (full profile), recipe `agreement`. Goldens unchanged.
Acceptance: 1951 passed, 37 skipped; 0 failures.

**Round 36 (v0.33.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
composite indices. Criterion `e86907d` pushed before the 8-cell run. New `census.index_core`,
`census.composite_index`, MCP tool `build_index` (full profile), recipe `composite_index`. The MI/NY
example showed an index dominated by NYC's car-free, high-cost housing (α 0.40): a construct-validity
warning now in the recipe. Goldens unchanged. Acceptance: 1946 passed, 37 skipped; 0 failures.

**Round 35 (v0.32.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
corrected EIV slopes under spatial dependence. Criterion `46fab40` pushed before the 8-cell run;
both candidates passed. New `census.spatial_eiv_core`, `census.spatial_eiv`, MCP
`fit_model(method="eiv", spatial=...)`. Post hoc: R21b H1 and H4 hold under both
(`docs/studies/r35_posthoc_spatial_eiv.md`). Goldens unchanged. Acceptance: 1940 passed, 37 skipped;
0 failures.

**Round 34 (v0.31.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
ranking areas. Criterion `6286ad9` pushed before the 8-cell run. New `census.ranking_core`,
`census.ranking`, MCP tool `rank_areas` (full profile), recipe `rank_areas`. Goldens unchanged.
Acceptance: 1935 passed, 37 skipped; 0 failures.

**Round 33 (v0.30.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
rank methods and diagnostics. Criterion `f660e9c` pushed before the 8-cell run. New
`census.rank_methods`, `correlation.validated_correlations` (Kendall, partial), `compare_groups`
method `rank`, `census.diagnostics` (VIF, Cook's distance, Breusch–Pagan, RESET; information only),
recipe `rank_methods`. Manifests unchanged (goldens identical); moving manifest correlation intervals
to the validated variants is backlog. Acceptance: 1930 passed, 37 skipped; 0 failures.

**Round 32 (v0.29.0; released in the bundled v0.39.0; implemented by the maintainer agent):**
design-based PUMS tests. Criterion `d65d034` pushed before the 8-cell run (household clustering,
weight CV, sample size; ACS-style SDR replicate weights). New `census.pums_inference`, MCP core tool
`test_association`, recipe `pums_tests`. Exploratory Michigan example
(`docs/studies/r32_pums_tests_example.md`) found that medians of heaped dollar amounts get zero
replicate SEs; such results are now labelled exploratory. Goldens unchanged. Acceptance: 1922 passed,
37 skipped, 57 subtests; 0 failures.

**Round 31 (v0.28.0; released in the bundled v0.39.0; implemented by the maintainer agent):** omnibus tests and group
comparisons. Criterion `3e3094a` pushed before the 36-cell run. F references failed; the wild score
bootstrap and IM-8 Hotelling passed for the combinations above. New `joint_test` statistic,
`compare_groups` (t-test, ANOVA, ANCOVA, interactions; MCP core tool) and recipe `group_comparison`.
Exploratory MI/NY example: `docs/studies/r31_group_comparison_example.md`. Execution golden
unchanged; schema golden changes only in the supported-statistics message
(`round31_compatibility.md`). Acceptance: 1908 passed, 37 skipped, 54 subtests; 0 failures.

**Round 30 (v0.27.0):** criterion and beta-star targets
committed/pushed at `2774140` before the fixed 12-cell run; no changes or extra draws. C1 passed all
three models for observed-ACS coefficients; C2 EIV failed and remains refused. State terms constant
within every cluster are absorbed and not estimable; partial constancy is refused. The post hoc
report preserves all original registrations/results. Both legacy goldens are unchanged. No new tools,
dependencies, WONDER access or private-export-checkout access. Acceptance: 1886 passed, 37 skipped,
4 warnings, 50 subtests; zero failures, 26 new tests (`round30_compatibility.md`).

## Standing rules

- **Circularity (enforced, R1/R2):** determinant studies use the ACS's own measure (disability: B18101).
  Model-based external estimates such as PLACES only for measures the ACS lacks (such as diabetes).
- **Pre-registration:** a manifest is hashed and committed before any outcome association is examined.
  Registered results are never rewritten; later checks are labelled post hoc.
- **Studies:** MI (26) and NY (36) are the test states. Study reviews by an agent are labelled "author
  self-review, not independent".
- **Releases:** every merged round gets a tag, GitHub release and Zenodo DOI. Study outputs are attached as
  a tarball after a key scan. Merges and releases need the owner's explicit approval.
- WONDER outputs: no sub-national counts 1–9 or values derived from them; no raw exports in the repo or releases.
- **Secrets and attribution:** see `CLAUDE.md`.

## Studies so far

| Round | Study | Headline |
| :--- | :--- | :--- |
| 19 | MI/NY tract income change | `docs/studies/r19_mi_ny_tract_income_change.md` |
| 20 | Disability and its determinants | `r20_mi_ny_disability_determinants.md` |
| 21 | PLACES disability vs ACS | PLACES inflates the education gradient 1.4× |
| 21b | County premature mortality | Poverty, disability supported; vehicle, cost burden not |
| 22 | County low birth weight | Poverty supported (holds with robust SEs); cost burden fragile (fails with robust SEs) |
| 24 | LBW inequality by poverty (exploratory) | RII 1.25 (90% CI 1.00–1.57); all intervals include the null |
| 26 | Cached spatial re-check / OLS sensitivity | IM unavailable for registered ACS/EIV inputs; `r26_posthoc_spatial_clusters.md` |
| 29 | WONDER mortality and held-out OH/PA replication | H1–H3 supported and replicated; H2 stable in registered sensitivity; spatial inference unresolved |
| 73 | Replication E through `multilevel_model(groups=["state", "county"])` (descriptive) | Shares 69.99/10.60/19.41%, identical to Round 68's hand script; `r73_three_level_example.md` |
| 71 | Replication C's slopes with the validated tract interval (descriptive) | SCPC ρ̄ .20 intervals 3–6 times wider than HC3 (residual Moran's I .17–.41); every slope stays positive; `r71_tract_example.md` |
| 69 | Replication D: county economic distress and drug-related mortality (registered) | Replicated (9.95 vs 9.62; Model 4 analogue); `r69_replication_monnat.md` |
| 68 | Replication E: shares of US life-expectancy variation (registered headline) | Replicated (70.0/10.6/19.4% vs 70.4/10.7/19.0%); `r68_replication_le_variance.md` |
| 67 | Replication C: NC tract life expectancy and ICE (registered) | Partly replicated (5 of 6 slopes; two indices exact to the printed digit); `r67_replication_nc_ice.md` |
| 66 | Replications A and B (registered numeric checks) | CHR county dissimilarity reproduced exactly (2,055 counties); state Gini within .001 (10/12 intervals contain it); `r66_replication_chr_segregation.md`, `r66_replication_state_gini.md` |
| 63 | A simulated 17-point interrupted series with each method (demonstration, not data) | Only `bootstrap_t_cons` is validated at 17 points; `r63_short_series_demonstration.md` |
| 62 | OH/PA county child poverty as a binomial outcome with SCPC (exploratory example) | Unemployment log-odds slope 0.121 (0.075–0.168), validated; consistent with the OLS percentage-point slope; `r62_binomial_scpc_example.md` |
| 60 | Michigan earnings and income inequality with the repaired intervals (exploratory example) | Atkinson and top-decile share now validated at state scale (top 10% of adults 25+ receive 37% of personal income); Theil T still exploratory; `r60_inequality_repair_example.md` |
| 59 | OH/PA county correlations with the spatial correction (exploratory example) | Child poverty and log income: n_eff 78 of 155, spatial interval ~50% wider (−.68, −.77 to −.56); partial poverty–unemployment given income stays positive (exploratory without replicates); `r59_spatial_correlation_example.md` |
| 58 | OH/PA county child poverty with SCPC (exploratory example) | Validated SCPC interval for the unemployment slope 1.23 (0.26–2.21), about 60% wider than HC3 and still excluding zero; `r58_scpc_example.md` |
| 57 | Race/ethnicity segregation with group-quarters tracts excluded, MI/NY (exploratory example) | Validated counties rise to 114 (Black–non-Black) and 130 (four groups); without group-quarters tracts Wyoming's H falls from .519 to .040 and Greene's from .426 to .131; Wayne minus Oakland H .164 (.148–.179); `r57_segregation_gaps_example.md` |
| 56 | Earnings and income inequality by disability, Michigan PUMS (exploratory example) | Earnings Gini .501 with a disability vs .445 without (difference .056, .048–.064, validated); income Gini .522; earnings P90/P10 heaped (flagged); `r56_pums_inequality_example.md` |
| 55 | Short interrupted series and SMR reference SE (demonstration, simulated) | Validated 22-point interval is the widest AR(1) interval and cannot separate a level change of 1 from none; reference CV .05 widens an SMR interval ~5%; `r55_demonstration.md` |
| 54 | OH/PA county child poverty with naive IM at 4, 6 and 8 clusters (exploratory example) | Income slope stable (−17.8 to −18.6); the unemployment interval includes zero with 4 or 6 clusters but not 8; none of the IM intervals is validated on OH/PA; `r54_ohpa_im_example.md` |
| 53 | County child poverty on income and unemployment, binomial with corrected slopes (exploratory example) | Calibration raises the unemployment slope 5% (reliability .78); validated jackknife intervals ~40–50% wider than the bootstrap's (income −1.11, −1.76 to −0.45; unemployment 0.134, 0.028 to 0.240 per point); `r53_rc_example.md` |
| 52 | Race/ethnicity segregation and the 2019–2024 poverty-segregation change, MI/NY (exploratory example) | Black–non-Black H validated in 102 counties (highest Wyoming NY .52, Wayne .50; prison group quarters drive rural highs); four-group H in 88; poverty segregation changed little (median D +.004; 23 of 133 intervals exclude zero, unadjusted); `r52_segregation_groups_example.md` |
| 51 | Counties with negative 2024 replicate estimates (exploratory example) | All ten county-designs Round 50 refused (Bronx, Kings, Wayne and others) estimated and validated with clipped replicates; dropping tracts instead moves Sullivan's D from .326 to .346; `r51_negative_replicates_example.md` |
| 50 | County poverty and income segregation, MI/NY 2024 (exploratory example) | 132 of 140 counties validated (0–1 under Round 28); Washtenaw has the highest poverty H (0.19); 5 counties per design refused for negative VRE replicates; `r50_segregation_example.md` |
| 49 | Disability, poverty band, insurance and earnings, MI PUMS models (exploratory example) | Disability: ordered logit −1.30 (odds 0.27 of a higher poverty band); uninsured probit −0.06; median earnings 36% lower; `r49_pums_models_example.md` |
| 45 | Round 29 counts with the count repairs (exploratory example) | H2 stays positive with hidden counts as [1, 9]; under IM-8 NB2 the MI/NY overdose slope includes zero (as in Round 30), H1/H3 hold; `r45_count_example.md` |
| 44 | Round 29 under NB2 (post hoc) | H1–H3 hold under NB2-HC3 in MI/NY and OH/PA; hidden H2 counts as [1, 9] give the same slope; `r44_posthoc_r29.md` |
| 40 | Poverty by metro class and share 65+, beta and median models (exploratory example) | Metro gaps agree across models; the share-65+ slope halves in median regression (tails drive OLS); `r40_beta_median_example.md` |
| 39 | Poverty and share 65+ by metro class, MANOVA (exploratory example) | Joint p = .0025 (validated) vs Pillai p ≈ 3e-11 (iid); `r39_manova_example.md` |
| 38 | Pooling R29's MI/NY and OH/PA coefficients (exploratory example) | HKSJ pooled intervals wide with two studies (only premature excludes zero); no pair shown equivalent within ±0.01; `r38_evidence_example.md` |
| 37 | ACS vs Census population estimates, MI/NY counties (exploratory example) | Bias −0.53% (−0.76 to −0.31); kappa 0.98; largest gaps in group-quarters counties; `r37_agreement_example.md` |
| 36 | MI/NY county deprivation index (exploratory example) | α 0.40 (0.25–0.52); "no vehicle" and cost burden make NYC boroughs the top scorers: construct-validity warning; `r36_index_example.md` |
| 35 | Post hoc spatial EIV re-check of R21b | H1 (poverty) and H4 hold under G1 and G2; H2/H3 still unsupported (outside the validated design); `r35_posthoc_spatial_eiv.md` |
| 34 | Michigan counties ranked by poverty (exploratory example) | Median rank interval spans 55 of 83 ranks; only Isabella surely top 10%; 34 counties differ from the state rate (Holm); `r34_ranking_example.md` |
| 33 | Rank methods on MI/NY county poverty (exploratory example) | Nonmetro > large-metro poverty: superiority 0.72 (0.61–0.83); Kruskal–Wallis p = .001; Bronx most influential in the ANCOVA; `r33_rank_methods_example.md` |
| 32 | Disability, insurance, poverty and earnings, MI PUMS (exploratory example) | Poverty OR 3.15 (3.04–3.26) with vs without disability; insurance type differs (Rao–Scott, design effect 3.15); median earnings difference not estimable with replicate SEs (heaped); `r32_pums_tests_example.md` |
| 31 | County poverty by metro class (exploratory example) | Nonmetro poverty higher than large and other metro (joint p = .010; ANCOVA .005); IM-8 unavailable (groups missing from clusters); `r31_group_comparison_example.md` |
| 30 | Post hoc IM/ACS checks | R21b unavailable (C2 failed); R22 H1/H2 retained; R29 MI/NY H1/H3 retained, H2 not retained (Holm p=.169); `r30_posthoc_im_acs.md` |

## Open backlog

`ROADMAP_BACKLOG.md` lists the open items (rewritten 2026-11-21; finished history at tag `backlog-r43-69`):
- N47: `.env` discovery when installed (Round 70);
- N48: long-job progress and checkpoints (70);
- N49: tract-level spatial inference (71; closed: SCPC rho_bar .20/.30 validated for tract OLS);
- N50: context data sources (CBP, ERS, CHR additional) and state-wide tract pulls (72);
- N51: three-level models, loading-weighted indices, expected counts (73; closed);
- N52: replication suite (74; closed);
- N53: between-group disparity measures and Kitagawa (76; closed);
- N54: joinpoint and age-adjusted rate ratios (77; closed);
- N55: staggered DiD and synthetic control (78; closed);
- N56: Oaxaca–Blinder and Fairlie decompositions (79; closed);
- N57: small-area proportions and several releases (80; closed);
- N58: spatial scan (81; closed);
- N59: epidemiologic reporting conventions (82; closed);
- N60: stratified analysis (83; closed);
- N61: marginal measures, prevalence ratios, attributable fractions, dose-response (84; closed);
- N62: designation accuracy (85; closed);
- N63: bias analysis (86; closed);
- N64: ecologic vs individual-level associations (87; closed);
- N39: ACS 2021–2025 refresh, about 2026-12-20.

Recorded limits are listed in its section 2.

## Plan format (keeps agent context small)

Plans may be queued ahead; agents implement only the lowest-numbered one. A round plan stays under about 15 KB: goal, ground rules, exact names and files, fixed acceptance checks,
and a short status table. When the round merges, add its outcome here in a few lines, then delete the plan
from the tree (it stays at its release tag).

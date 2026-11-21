# Project status

The single current summary of the Census Research Engine: what it does, which methods are validated, the
standing rules, and what is next. Read this instead of old plans. Updated each round when it merges.

**Current release:** v0.64.0 (Rounds 64–68: agent access and replications A, B, C, E; released as one bundle; DOI
10.5281/zenodo.24405380). Previous: v0.60.0 (Rounds 61–63; DOI 10.5281/zenodo.24400452); v0.57.0 (Rounds 57–60; DOI 10.5281/zenodo.24398149); v0.53.0 (Rounds 43–56; DOI 10.5281/zenodo.24384786); v0.39.0 (Rounds 31–42, the statistics roadmap; DOI
10.5281/zenodo.24371310); v0.27.0 (Round 30: IM-8 with ACS sampling error; DOI
10.5281/zenodo.24357238); v0.26.0 (Round 29: WONDER mortality, replicated in OH/PA; DOI 10.5281/zenodo.24356572). All versions: concept record
[zenodo.org/records/23925301](https://zenodo.org/records/23925301). Per-round detail: `CHANGELOG.md`.

## Where things are

| Path | What |
| :--- | :--- |
| `census/` | Library. `manifest/` package (pre-registered studies: `schema`, `validate`, `create`, `run` (typed `RunState` and ordered execution stages), `methods_text`, `methods` (single method registry), plus `adjustments`, `replicates`, `external`, `derivations`, `datasource`; import from `census.manifest`, but patch tests at the submodule that looks the name up), `models.py` (`fit_replicate`, `fit_eiv`, robust GLM SEs), `health_sources.py` (PLACES, USALEEP, CHR&R, WONDER exports), `spatial*.py`, `sae*.py`, `simulation*.py` (validation studies) |
| `mcp_server.py` | MCP server (71 tools; 16 in `core`, 17 in `core_spatial`; profiles in `census/mcp_profiles.py`) |
| `docs/agent_protocol.md`, `docs/recipes/` | What agents are told; keep in step with engine rules |
| `docs/audits/` | Validation reports (pass/fail, reproducible scripts in `scripts/`) |
| `docs/studies/` | Pre-registered study reports; outputs are release attachments, not in the repo |
| `examples/manifests/` | Registered manifests (their bytes are fixed once registered) |
| `PLAN_ROUND_<n>.md` | `PLAN_ROUND_69.md` (replication D: Monnat 2018). Implement only the lowest-numbered plan. Merged plans are archived (below) |
| `ROADMAP_BACKLOG.md` | Follow-up roadmap (Rounds 43–63 complete; section 8, Round 64 onward, planned; N39 ACS 2021–2025 refresh deferred to about 2026-12-20): the backlog below plus issues N1–N38 |
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
| Composite index scores and Cronbach's α (`build_index`) | **Passed**: per-area score intervals (PCA and equal weights; mean coverage .898–.899, every area ≥ .874); Feldt α interval for independent areas (.891–.912; under-covers with spatial dependence, .58–.67; Round 48 effective-n repair). Quintile stability and typologies descriptive | `index_validation.md`, criterion `e86907d` |
| Replication E (Round 68) | **Replicated**: Boing et al. 2020 headline: tract/county/state shares of US life-expectancy variation 70.0/10.6/19.4% vs 70.4/10.7/19.0% (USALEEP; counts match exactly). Three-level model via statsmodels (engine is two-level only: N46) | `r68_le_variance_replication.md`, criterion `110c22e` |
| Replication C and SCPC at tract level (Round 67) | **Partly replicated**: Mitchell et al. 2022 (NC tract life expectancy on ICE), 5 of 6 slopes; ICE Race and Income match to the printed digit (R² 19.60%, 48.19% exact); the combined index's OLS slope is 13% larger (definition). **SCPC failed on NC tracts** at 100 km (.75/.81; HC3 .12–.26), so tract-level SCPC is exploratory | `r67_nc_ice_replication.md`, `r67_nc_tract_validation.md`; plan `e75a41b`, criterion `14b78b2` (deviation 2) |
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

Scheduled in `ROADMAP_BACKLOG.md` (section 2 lists issues N1–N16 found in Rounds 31–42: unbounded
core-profile instructions, stale tool counts, untested weak-instrument cut-off and noisy-confounder
robustness, mediator error, MI with several incomplete covariates or ACS error, censored NB2, short
interrupted series, spatially robust correlations and α, small-k meta-analysis, survey-weighted PUMS
models, and MI/NY-only validation geography).

1. Spatial dependence: naive-target IM-8 (Round 30 C1, OLS/binomial/Poisson) and corrected linear EIV
   (Round 35 G1/G2, library, MCP and, since Round 43, manifests via `fit_eiv` `args.spatial`) are
   validated. Round 44 re-checked both on OH/PA: G1/G2 replicate; naive C1 under-covers there with
   spatially correlated fields (exploratory outside MI/NY). Pooled k-means clusters can straddle adjacent
   states, leaving a state term partly constant (refused): the engine says so, and `within_states=True`
   (Round 45; `fit_spatial_eiv`, `fit_count_model`) assigns clusters within each state. Count slopes under
   IM-8 and NB2 with noisy exposures were validated in Round 45; G1/G2 with three and four error-prone covariates in Round 46, five in Round 53 (six failed); corrected Poisson/NB2 slopes under spatial dependence in Round 53. Remaining: six or more covariates; corrected binomial slopes under spatial dependence. No extra cluster counts or retuned
   simulations were tried. Do not substitute naive C1 for registered EIV. Round 58: SCPC is the validated naive
   interval outside MI/NY (OLS, Poisson) and the reliability gate (≥ .8) restores G1/G2 with three to five
   covariates there. Round 54 re-checked Rounds 45, 46 and 53
   on OH/PA (count slopes and G2 up to four covariates replicate; G1 three to five and G2 five do not) and found that
   4 or 6 within-state clusters do not repair naive IM there; Round 48's effective-n intervals are not re-checked
   (N31).
2. Closed in Round 44: Poisson HC3 (used by R29) under-covered with strong overdispersion in Round 39;
   R29's H1–H3 hold under NB2-HC3 in MI/NY and OH/PA (`r44_posthoc_r29.md`). The NB2 alpha optimizer now
   falls back to Nelder–Mead when BFGS fails (large counts, little overdispersion).
3. Closed in Round 43: manifests opt in to the Round 33 intervals with `correlation_matrix`
   `args.interval: "validated"`; registered manifests keep the Fisher-z interval (their bytes are fixed).
4. Closed in Round 53: `regression_calibration` is validated for Poisson and NB2 slopes (Round 46, bootstrap SEs) and, with `se_method="jackknife"`, for binomial, Poisson and NB2 (Round 53; the binomial bootstrap failure was an SE problem, not bias). Spatially correlated counts: calibration + IM-8 (Round 53). Corrected binomial slopes under spatial dependence remain untested.
5. Held-out OH/PA mortality replication completed in Round 29 under the unchanged registered protocol;
   all three associations replicate, including both H2 suppression sensitivities. All 62 manual WONDER
   exports pass inventory. Later causes with suppressed national child-age reference cells need a
   separately pre-registered rule before analysis; do not replace them by zero, an invented count or
   an unregistered pooling rule. The 2013–2017 and MCD files remain inventory-only.
6. Further validation: closed for segregation in Round 50 (realistic error, real MI/NY tract MOEs;
   bias-corrected indices and three-group H valid to noise level .50). Remaining: race/ethnicity group
   structures, four and five groups, release contrasts and OH/PA: closed in Round 52. Negative replicate
   estimates: closed in Round 51 (clipped for segregation, accepted for SMR); Round 57 extended clipping above
   .50 and added six groups, same-release county contrasts and a group-quarters exclusion (N30, N33 closed;
   clipped six-group counties stay exploratory). Uncertain reference
   denominators for SMRs: closed in Round 55 (`reference_population_se`). Round 27 splines/joint tests remain exploratory and require a
   separately pre-specified finite-sample validation before confirmatory use.
   Microdata inequality measures: closed in Round 56 (Gini, quantile ratios, Gini differences; Theil,
   Atkinson and top shares exploratory).
7. Closed in Round 43: a saturated `fit_replicate` (residual df 0) now reports missing model SEs,
   intervals and p-values with a SATURATED MODEL note instead of infinite ones, and the coefficient
   plot never draws infinite whiskers.

## Plan format (keeps agent context small)

Plans may be queued ahead; agents implement only the lowest-numbered one. A round plan stays under about 15 KB: goal, ground rules, exact names and files, fixed acceptance checks,
and a short status table. When the round merges, add its outcome here in a few lines, then delete the plan
from the tree (it stays at its release tag).

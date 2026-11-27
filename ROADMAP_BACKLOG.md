# Backlog roadmap (open items only)

**Status: rewritten 2026-11-21, after v0.65.0 (DOI 10.5281/zenodo.24411452); Rounds 70–74 released as v0.70.0 (DOI 10.5281/zenodo.24433164); Round 75 as v0.71.0 (DOI 10.5281/zenodo.24434858); Rounds 76–81 released as v0.77.0 (DOI 10.5281/zenodo.24444186); Rounds 82–119 tagged & pushed as v0.115.0 (2026-11-26; Zenodo DOI pending).** Finished work (Rounds 43–69,
issues N1–N46, the replication shortlist) was removed from this file. It stays in git at tag `backlog-r43-69`,
in `CHANGELOG.md` and in the plan tags `plan-r<n>`. This file is the owner's backlog, from which
`PLAN_ROUND_<n>.md` files are drafted; it is not itself a plan. **Implementing agents: do not read this file
unless the owner asks; implement only the lowest-numbered `PLAN_ROUND_<n>.md`.**

**Ground rules (unchanged):**
- Validation first: the criterion is committed before the full run, and failed methods stay exploratory.
- MI/NY are the test states and OH/PA the replication states; later geometries are added where a round needs
  them.
- Goldens stay byte-identical unless a round says otherwise.
- No automated WONDER access, and no sub-national counts 1–9 in any output.
- Releases need the owner's yes each time.

## 1. Open issues

| # | Issue | Found in | Kind | Round |
| :--- | :--- | :--- | :--- | :--- |
| N39 | The ACS 2021–2025 five-year release (due about December 2026) needs its metadata archive, a concordance audit and a price-index refresh; BLS's 2025 annual average is still provisional | owner, 2026-11-20 | data refresh | about 2026-12-20 |
| N47 | `load_dotenv()` searches from the engine's own file location, not the working directory. Installed from a wheel, the engine misses the user's project `.env` (Census API key). Seen in every worktree run of Rounds 66–69 | R66–R69 | bug | 70 (closed) |
| N48 | Long workflows give no progress and save results only at the end; a killed run loses everything (Round 69's first run) | R69 | usability | 70 (closed) |
| N49 | No tract-level spatial interval is validated: on NC tracts SCPC under-covers at 100 km (.75/.81) and HC3 covers .12–.26. Fits give no warning when residuals are clearly spatially dependent | R67 | validation gap | 71 (closed) |
| N50 | Data sources the replications needed are not in the engine: County Business Patterns, ERS county typology and rural–urban codes, CHR additional measures. All-state tract pulls need a hand loop (no one-request-per-state path) | R66, R69 | missing capability | 72 (closed) |
| N51 | Methods the replications needed are missing: three-level multilevel models (was N46), indices from published loadings, indirect standardization for a county frame from a national age × sex file | R68, R69 | missing method | 73 (closed) |
| N52 | The replications are one-off scripts: an agent cannot rerun them through MCP or manifests, and nothing checks that the engine still reproduces them | R66–R69 | reproducibility | 74 (closed) |
| N53 | No between-group disparity measures (rate ratio/difference vs a reference group, Index of Disparity, between-group variance, Theil and MLD over groups) or Kitagawa rate decomposition; only area-gradient SII/RII exist | owner, 2026-11-22 | missing method | 76 (closed) |
| N54 | Annual surveillance trends lack joinpoint regression (number of joinpoints, APC/AAPC) and rate ratios of age-adjusted rates (Tiwari) | owner, 2026-11-22 | missing method | 77 (closed) |
| N55 | Policy evaluation has two-group DiD and ITS only: staggered adoption (two-way FE is biased) and synthetic control are missing | owner, 2026-11-22 | missing method | 78 (closed) |
| N56 | No decomposition of group gaps in microdata (Oaxaca–Blinder, Fairlie) with replicate-weight SEs | owner, 2026-11-22 | missing method | 79 (closed) |
| N57 | Fay–Herriot is validated on the linear scale only: proportions near 0 and borrowing strength over releases (Rao–Yu) are missing | owner, 2026-11-22 | missing method | 80 (closed) |
| N58 | No cluster detection for county counts (Kulldorff spatial scan) | owner, 2026-11-22 | missing method | 81 (closed) |
| N59 | Results do not say what kind of measure an outcome is (prevalence vs incidence rate), that area analyses are ecologic and cross-sectional, or how much of each ACS answer was imputed (allocation); bundles lack a "Table 1" and a limitations section (Foundations of Epidemiology ch. 1, 2, 6, 9, App. 1) | owner, 2026-11-22 (book) | reporting | 82 (closed) |
| N60 | No stratified analysis: Mantel–Haenszel pooling, homogeneity tests, crude-versus-adjusted comparison, effect-modifier reporting or additive interaction (ch. 7–8) | owner, 2026-11-22 (book) | missing method | 83 (closed) |
| N61 | Binomial/logit results give odds ratios only, which overstate risk ratios for common ACS outcomes; no marginal RR/RD, prevalence ratio, attributable fraction or dose-response trend (ch. 4, 10) | owner, 2026-11-22 (book) | missing method | 84 (closed) |
| N62 | Area designations by thresholds on noisy ACS estimates have no accuracy statement (probability above threshold, sensitivity, PPV) (ch. 11) | owner, 2026-11-22 (book) | missing method | 85 (closed) |
| N63 | No quantitative bias analysis: E-values, misclassification correction, both-directions covariable sensitivity (ch. 6–7) | owner, 2026-11-22 (book) | missing method | 86 (closed) |
| N64 | No way to measure ecologic bias: within-area versus between-area (contextual) associations on PUMS (ch. 9) | owner, 2026-11-22 (book) | missing method | 87 (closed) |
| N65 | Causal tools run without a stated causal question: no target-trial specification, no causal diagram, adjustment sets chosen by hand or by the associational 10% rule (Hernán and Robins chapters 3, 6–8, 18, 22) | owner, 2026-11-23 (book) | missing method | 89 (closed) |
| N66 | Inverse-probability methods report no positivity (overlap) diagnostics, stabilized or truncated weights, or IPW-versus-g-formula agreement (chapters 3, 12–13, 15) | owner, 2026-11-23 (book) | validation gap | 90 (closed) |
| N67 | Annual policy panels with time-varying confounders affected by past treatment need g-methods (IP-weighted marginal structural models); Round 78 adjusts for nothing time-varying (chapters 19–21) | owner, 2026-11-23 (book) | missing method | 91 (closed) |
| N68 | Data sources from Walker chapters 4 and 11 are missing: Population Estimates (annual population by age and sex, the denominators for annual rates), LEHD LODES jobs and commuting, ACS county-to-county migration flows | owner, 2026-11-23 (book) | data source | 92 (closed) |
| N70 | Results do not attribute their methods: tool outputs, bundles and the CLI carry no list of the papers and textbooks a method rests on (owner request) | owner, 2026-11-23 | reporting | 88 (closed) |
| N69 | No geographically weighted regression, geodemographic classification, regionalization or diversity index with ACS uncertainty (Walker chapter 8) | owner, 2026-11-23 (book) | missing method | 93 (closed) |
| N71 | Health inequality monitoring per WHO (2013) is incomplete: no mean difference from the overall mean or best subgroup, no population attributable risk against the best subgroup, no change in inequality over time, no double disaggregation or level-by-inequality priority view | owner, 2026-11-23 (book) | missing method | 94 (closed) |
| N72 | No YPLL from mortality exports and no aberration detection (historical limits, EARS) for the latest period of an annual series (CDC SS1000 lessons 3–5) | owner, 2026-11-23 (book) | missing method | 95 (closed) |
| N73 | No count-scale spatial disease mapping (Besag/BYM2 Poisson) and no exceedance probabilities (Moraga chapters 9–10) | owner, 2026-11-23 (book) | missing method | 96 (closed) |
| N74 | Model checks are in-sample: no spatial block cross-validation (MAE, RMSE, coverage, CRPS) and no MAUP scale/zoning sensitivity (Moraga chapters 11, 16) | owner, 2026-11-23 (book) | validation gap | 97 (closed) |
| N75 | No regression discontinuity design (sharp/fuzzy, robust bias-corrected intervals, density test) for age or threshold cutoffs (Cunningham, Mixtape) | owner, 2026-11-23 (book) | missing method | 98 (closed) |
| N76 | No matching estimators (bias-corrected nearest neighbour, coarsened exact matching) and no triple-difference design (Mixtape) | owner, 2026-11-23 (book) | missing method | 99 (closed) |
| N77 | Multiple imputation covers at most two covariates under a normal model: no predictive mean matching, general FCS, passive derived variables, δ-adjustment MNAR sensitivity or FMI reporting (van Buuren, FIMD) | owner, 2026-11-23 (book) | missing method | 100 (closed) |
| N78 | No demographic data assessment (age heaping, age-sex accuracy), life tables, life-expectancy decomposition or census-survival migration (IUSSP Tools for Demographic Estimation) | owner, 2026-11-23 (book) | missing method | 101 (closed) |
| N79 | Meta-analysis gaps: unvalidated prediction interval, no I² interval, influence diagnostics, meta-regression or small-study test (Harrer et al.) | owner, 2026-11-23 (book) | validation gap | 102 (closed) |
| N80 | Validated/documented methods from Rounds 93–101 (`demography`, `ypll`, `double_disaggregation`, `priority_quadrants`, `diversity_index`) are Python-only and unreachable via MCP/CLI | R93–R101 | agent access | 103 (closed) |
| N81 | Agent routing contract (`docs/agent_routing.md`) has not been extended since Round 64 (15 rows; none of Rounds 76–102 tested) | R76–R102 | agent access | 103 (closed) |
| N82 | Documentation and backlog drift after 21 merged rounds since v0.77.0 (stale tool/recipe counts in README, unclosed backlog markers) | R76–R102 | hygiene | 103 (closed) |
| N83 | Meta-analysis prediction intervals, meta-regression (k=10) and Egger test failed Round 102 validation | R102 | repair | 104 (closed) |
| N84 | Nearest-neighbour matching ATT failed narrowly (.852 at N=145, limited overlap) | R99 | repair | 104 (closed) |
| N85 | BYM2 disease mapping relative-risk intervals failed in 1 sparse cell (.790, log-grid 1/σ pile-up) | R96 | repair | 104 (closed; B3 gated E ≥ 30) |
| N86 | IP-weighted MSM failed (.805–.881); baseline-L0 + cluster jackknife improved to .850–.918 (34/36 cells) | R91 | repair | 104 (closed; stays exploratory) |
| N87 | WHO mean differences mdm/mdb failed at small spread + high CV (folded-normal bias) | R94 | repair | 104 (closed; stays exploratory) |
| N88 | Validated area methods from Rounds 41–100 (`estimate_effect`, `spatial_scan`, `stratified`, `marginal`, `impute`, `who_measures`) missing from pre-registered manifests | R41–R100 | manifest | 104 (closed) |
| N89 | Continuous RDD under strong curvature failed Round 98 (.78–.80); repaired via CCT CER bandwidth `h_ik * n^(-1/20)` (.877–.920) | R98 | repair | 105 (closed) |
| N90 | PUMS replicate Wald homogeneity test failed Round 83 (.099–.151); Hotelling F tested (`H2b`) | R83 | repair | 105 (closed; stays exploratory) |
| N91 | Designation PPV predictive interval failed Round 85 (.54–.85); FH parametric bootstrap tested (`Q2b`) | R85 | repair | 105 (closed; stays exploratory) |
| N92 | Probabilistic misclassification failed Round 86 (.76–1.00); repaired via propagated observed-table sampling (.890–.908) | R86 | repair | 105 (closed) |
| N93 | IP-weighted MSM Firth-logit + L0 + jackknife (`M4`: 34/36 cells ≥ .86, 2 K=18 d1 cells .832/.852) | R91/R104 | repair | 105 (closed; stays exploratory) |
| N94 | PUMS Hotelling F homogeneity under exact per-measure nulls (`H2c`: 11/12 cells ≤ .13, rd K=5 n=300 at .131) | R83/R105 | repair | 106 (closed; stays exploratory) |
| N95 | Designation PPV bootstrap with rule re-selection (`Q2c`: 7/8 cells ≥ .86, N=1000 A=0.02 point at .850) | R85/R105 | repair | 106 (closed; stays exploratory) |
| N96 | Ecologic / between-area slope Croon/Fuller reliability correction (`E3`: .883–.888 at n_j=40, .810–.825 at n_j=20) | R87 | repair | 106 (closed; stays exploratory) |
| N97 | Observed Lin's CCC failed Round 37 (.859); repaired via delete-one-area Fisher-z jackknife (.886–.901) | R37 | repair | 106 (closed) |
| N98 | Annual policy panels with treatment-confounder feedback repaired via Hernán & Robins ch. 21 parametric g-formula + cluster jackknife (.883–.920 across all 36 cells) | R91/R104/R105 | repair | 106 (closed) |
| N99 | Designation PPV predictive intervals repaired via FH parametric bootstrap (`Q2d-prob80` .875–.915, `Q2d-point` with LL floor .873–.922) | R85/R105/R106 | repair | 107 (closed) |
| N100 | PUMS homogeneity repaired via Korn–Graubard Hotelling F gated at `min_stratum_n ≥ 500` (`H2d`: size .068–.128 across all 12 cells) | R83/R105/R106 | repair | 107 (closed) |
| N101 | Ecologic slope (`E3b`: .825 at `J=150 n_j=40`) and Shannon entropy SDR bias correction (`S2`: .856 at `G=6 n=100`) tested; stay exploratory | R87/R93/R106 | repair | 107 (closed; stay exploratory) |
| N102 | Agent/workflow parity for Rounds 104–107 repairs (`difference_in_differences(design="msm", method="gformula")`, protocol sync, routing R31–R37) | R104–R107 | agent access | 107 (closed) |
| N103 | Multi-confounder vector parametric g-formula (`M5b`, `p ∈ {2, 3}`, `.880–.922` across all 48 cells) | R106 | extension | 108 (closed) |
| N104 | Shannon entropy diversity SDR bias correction gated at `n_resp >= 150` (`S2b`, `.866–.906` across all 6 cells) | R93/R107 | repair | 108 (closed) |
| N105 | Croon/Fuller ecologic slope (`E3c`: 11/12 cells `.870–.905`, `ICC=0.05 J=150 n_j=80` at `.853`) | R87/R107 | repair | 108 (closed; stays exploratory) |
| N106 | Manifest support for `designation` (Round 85/107) and `agreement` (Round 37/48/106) (20 manifest methods total) | R37/R85/R106–107 | manifest | 108 (closed) |
| N107 | Fuller (1987, $\alpha=4$) ecologic/between-area slope repair (`E3d`, `.873–.920` across all 12 cells, `areas ≥ 50, median_area_n ≥ 80`) | R87/R108 | repair | 109 (closed) |
| N108 | Joinpoint AAPC parametric residual bootstrap-$t$ with location re-estimation (`J3c`, `.887–.950` across all 8 cells) | R77 | repair | 109 (closed) |
| N109 | Manifest support for `rdd` (Round 98/105) and `disease_map` (Round 96/104 `method="B3"`) (22 manifest methods total) | R96/R98/R104–105 | manifest | 109 (closed) |
| N110 | Synthetic-control conformal (`S3`, `T_pre ≥ 15`: 11/12 cells ≥ .86, `T_pre=20 ρ=0.7` at .856) and WHO `mdm_w`/`mdb_w` SNR gate (`W2`: .843–.907 / .795–.863) | R78/R94 | repair | 110 (closed; stay exploratory) |
| N111 | Manifest support for `joinpoint` (Round 77/109) and `demography` (Round 101) (24 manifest methods total) | R77/R101/R109 | manifest | 110 (closed) |
| N112 | Agent routing contract expansion (`R38–R40`; 40 offline-tested rows) | R107–R109 | agent access | 110 (closed) |
| N113 | Edge-case hardening of confirmed methods (constant-`x` ZeroDivisionError in ecologic Fuller; identical-series crash in `agreement.py`) | R106/R109 | hardening | 111 (closed) |
| N114 | Independent reference cross-checks & out-of-DGP adversarial stress audit of confirmed methods (10/10 held) | R104–R110 | audit | 111 (closed) |
| N115 | Designation PPV interval for `rule="lower"` (`Q2e-lower`, `.890–.917` across all 4 cells; `prob50` stays exploratory) | R85/R107 | repair | 112 (closed) |
| N116 | Count-scale disparity indices (`idisp`, `bgv`, `theil`, `mld`, gated at `min_events ≥ 100`: `.863–.920`) | R76 | repair | 112 (closed) |
| N117 | RDD manipulation/density test null-size validation (continuous `n ≥ 1,000`: `.083–.122`) | R98 | repair | 112 (closed) |
| N118 | Three-level variance shares (`M3b`: 11/12 ≥ .86, `.850` at `G_top=30`) and Woolf RR homogeneity (`W3_rr`: `.065–.135`) tested; stay exploratory | R73/R83 | repair | 112 (closed; stay exploratory) |
| N119 | Pre-specified national-domain `M3c` (`G_top ∈ {49, 51}`: 11/12 ≥ .86, `.850` at `G_top=49 mid`); stays exploratory | R73/R112 | repair | 113 (closed; stays exploratory) |
| N120 | Final 4 manifest methods (`difference_in_differences`, `interrupted_series`, `combine_estimates`, `bias_analysis`; 28 total) | R38–R108 | manifest | 114 (closed) |
| N121 | Published textbook & closed-form reference benchmark suite (8 benchmarks, `tests/test_reference_benchmarks.py`) | R76–R112 | replication | 115 (closed) |
| N122 | Recipes & README discoverability refresh (81 tools, 28 manifest methods, 40 routing rows) | R104–R115 | docs | 116 (closed) |
| N123 | Offline N39 ACS 2021–2025 release-refresh preflight script & runbook (`scripts/acs_release_preflight.py`) | N39 | tooling | 117 (closed) |
| N124 | Pre-commit release hygiene audit (`scripts/release_hygiene_check.py`) & full Rounds 103–118 verification | R103–R118 | hygiene | 118 (closed) |
| N125 | Missing manifest citation keys in `census/references.py` (10 keys registered + hygiene invariant) | R104–R114 | bug | 119 (closed) |
| N127 | Layer B Tier 2 Neural Hybrid RAG (Option B): isolated `.venv-layer-b` with dense scientific embeddings (`allenai/specter2` or `BAAI/bge-base-en-v1.5`) stored on Samsung 850 EVO SSD + `OpenScholar/OpenScholar_Reranker` cross-encoder reranking via RRF, keeping Layer A `.venv` and `pyproject.toml` untouched | owner, 2026-11-27 | layer_b enhancement | open |
| N126 | Modern manifest templates (`examples/manifests/templates/`) & end-to-end `run_manifest` integration tests | R104–R114 | docs/tests | 119 (closed) |

## 2. Recorded limits (not scheduled; reopen only with a new idea)

- Interrupted series below 17 annual points (every method failed at 15).
- G2 with eight error-prone covariates (.856); spatial EIV beyond the gated caps (G1 8, G2 7).
- Theil T from PUMS (fails up to 8,000 households).
- Bias-corrected segregation D above noise .75 (failed on Texas), and any index at infinite noise.
- Clipped six-group segregation only as validated in Round 62; naive isolation and H are exploratory.
- IM-8 correlation and α intervals; CCC intervals; PUMS GEE (deferred: SDR replicates carry the design).
- Round 27 splines and joint tests (exploratory until a pre-specified finite-sample validation).
- WONDER causes with suppressed national child-age reference cells need a pre-registered rule before analysis.

## 3. Rounds

| Round | Theme | Covers | Status |
| :--- | :--- | :--- | :--- |
| 70 | Housekeeping: `.env` discovery and long-job progress/checkpoints (no new statistics) | N47, N48 | merged (v0.66.0) |
| 71 | Tract-level spatial inference: validation, plus a residual-dependence warning | N49 | merged (v0.68.0; SCPC .20/.30 pass for tract OLS; SEM fails) |
| 72 | Data sources: CBP, ERS typology and rural–urban codes, CHR additional measures, state-wide tract pulls | N50 | merged (v0.67.0; state-wide tract pulls already existed) |
| 73 | Methods: three-level multilevel models, loading-weighted indices, indirect standardization helper | N51 | merged (v0.69.0; three-level fixed effects and loadings indices validated; share intervals exploratory) |
| 74 | Replication suite: the five replications as registered manifests and engine regression checks | N52 | merged (v0.70.0; specs + runner, all five agree; not manifests, see round74_compatibility.md) |
| 75 | Manifest support for the Round 73 methods, tract coordinates, recipes, README | gaps after R74 | merged, released (v0.71.0) |
| 76 | Between-group disparity measures and Kitagawa decomposition | N53 | merged (v0.72.0) |
| 77 | Joinpoint regression and age-adjusted rate ratios | N54 | merged (v0.73.0) |
| 78 | Staggered-adoption DiD and synthetic control | N55 | merged (v0.74.0) |
| 79 | Oaxaca–Blinder and Fairlie decompositions (PUMS) | N56 | merged (v0.75.0) |
| 80 | Fay–Herriot for proportions and temporal Fay–Herriot | N57 | merged (v0.76.0) |
| 81 | Spatial scan statistic for county counts | N58 | merged (v0.77.0) |
| 82 | Epidemiologic reporting conventions: measure types, design labels, allocation rates, Table 1, limitations | N59 | merged (v0.78.0) |
| 83 | Stratified analysis: Mantel–Haenszel, homogeneity, effect modification, additive interaction | N60 | merged (v0.79.0) |
| 84 | Marginal risk ratios/differences, prevalence ratios, attributable fractions, dose-response | N61 | merged (v0.80.0) |
| 85 | Area designations as screening tests (probability above threshold, Sn/Sp/PPV/NPV) | N62 | merged (v0.81.0) |
| 86 | Quantitative bias analysis: E-values, misclassification, both-directions sensitivity | N63 | merged (v0.82.0) |
| 87 | Ecologic versus individual-level associations on PUMS (within, between, contextual) | N64 | merged (v0.83.0) |
| 88 | Method attribution: a source registry, sources on every tool result, references in bundles | N70 | done (v0.84.0) |
| 89 | Causal question specification: target trial, causal diagram, adjustment-set checks | N65 | done (v0.85.0) |
| 90 | Positivity diagnostics, stabilized and truncated weights, IPW vs g-formula | N66 | done (v0.86.0) |
| 91 | IP-weighted marginal structural models for annual policy panels | N67 | done (v0.87.0; exploratory) |
| 92 | Data sources: Population Estimates, LEHD LODES, ACS migration flows | N68 | done (v0.88.0) |
| 93 | Geographically weighted regression, geodemographic classification, regionalization, diversity index | N69 | done (v0.89.0; exploratory) |
| 94 | Inequality monitoring (WHO): mean differences, PAR vs best subgroup, trends in inequality, double disaggregation, priority quadrants | N71 | done (v0.90.0) |
| 95 | YPLL and surveillance aberration detection (CDC SS1000) | N72 | done (v0.91.0) |
| 96 | Spatial disease mapping: BYM2 Poisson with exceedance probabilities (Moraga) | N73 | done (v0.92.0) |
| 97 | Spatial block cross-validation and MAUP sensitivity (Moraga) | N74 | done (v0.93.0; exploratory) |
| 98 | Regression discontinuity: robust bias-corrected local polynomial, density and placebo tests; PUMS age-65 example | N75 | done (v0.94.0) |
| 99 | Matching (bias-corrected nearest neighbour, coarsened exact) and triple differences | N76 | done (v0.95.0) |
| 100 | Multiple imputation: FCS with predictive mean matching, passive variables, δ-adjustment, FMI | N77 | done (v0.96.0) |
| 101 | Demographic estimation: age-data quality indices, life tables with SEs, Arriaga decomposition, census-survival migration | N78 | done (v0.97.0) |
| 102 | Meta-analysis completeness: validated prediction interval, I² interval, leave-one-out, meta-regression, Egger test | N79 | done (v0.98.0) |
| 103 | Agent access, routing contract (R16–R30) and release hygiene after Rounds 76–102 (no new statistics) | N80–N82 | done (v0.99.0) |
| 104 | Exploratory-measure repairs (P2/R2/E2, M1b-ATT, B3 pass; M3/MD2 exploratory) and manifest support for validated methods | N83–N88 | done (v0.100.0) |
| 105 | Second-wave exploratory-measure repairs (R1b continuous RDD, M1b probabilistic misclassification pass; H2b/Q2b/M4 exploratory) | N89–N93 | done (v0.101.0) |
| 106 | Third-wave exploratory-measure repairs (C2 Lin's CCC, M5 parametric g-formula pass; H2c/Q2c/E3 exploratory) | N94–N98 | done (v0.102.0) |
| 107 | Final-wave gated repairs (Q2d-prob80, Q2d-point, H2d pass; E3b/S2 exploratory) + full MCP/protocol/routing parity (R31–R37) | N99–N102 | done (v0.103.0) |
| 108 | Multi-confounder parametric g-formula (M5b), entropy diversity repair (S2b, n >= 150), and `designation`/`agreement` manifest methods | N103–N106 | done (v0.104.0) |
| 109 | Fuller ecologic slope (E3d) & Joinpoint AAPC bootstrap-$t$ (J3c) repairs + `rdd`/`disease_map` manifest methods | N107–N109 | done (v0.105.0) |
| 110 | `joinpoint`/`demography` manifests (24 total), routing `R38–R40` (40 rows), and validation audit of `S3`/`W2` (stay exploratory) | N110–N112 | done (v0.106.0) |
| 111 | Confirmed-method correctness, edge-case hardening & out-of-DGP adversarial stress-test audit (10/10 held) | N113–N114 | done (v0.107.0) |
| 112 | Final repairable exploratory wave (`Q2e-lower`, count disparity indices, RDD density pass; `M3b`/`prob50`/`W3_rr` exploratory) | N115–N118 | done (v0.108.0) |
| 113 | National-domain `M3c` check (`G_top ≥ 49`: stays exploratory) & full-repository verification (Rounds 103–113) | N119 | done (v0.109.0) |
| 114 | Final 4 pre-registered manifest methods (`difference_in_differences`, `interrupted_series`, `combine_estimates`, `bias_analysis`; 28 total) | N120 | done (v0.110.0) |
| 115 | Published textbook & closed-form reference benchmark suite (8 benchmarks) | N121 | done (v0.111.0) |
| 116 | Recipes & README discoverability refresh (81 tools, 28 manifest methods, 40 routing rows) | N122 | done (v0.112.0) |
| 117 | Offline N39 ACS 2021–2025 release-refresh preflight tooling & runbook | N123 | done (v0.113.0) |
| 118 | Pre-commit release hygiene audit & full-repository verification (Rounds 103–118) | N124 | done (v0.114.0) |
| 119 | Citation integrity, modern manifest templates, E2E `run_manifest` tests & static hygiene | N125–N126 | done (v0.115.0) |
| — | ACS 2021–2025 refresh | N39 | about 2026-12-20 |

Order rationale:
- **Rounds 98–102** (added 2026-11-23 from Cunningham's Mixtape, van Buuren's FIMD, IUSSP Tools for Demographic
  Estimation and Harrer et al.; mappings in `docs/literature/`): causal designs first (98–99), then missing data
  (100), demographic tools (101) and meta-analysis (102).
- **Rounds 94–97** (added 2026-11-23 from the WHO inequality-monitoring handbook, CDC SS1000 and Moraga; mappings in
  `docs/literature/`): 94 extends the existing inequality tools; 95 adds mortality measures and surveillance; 96 adds
  count-scale spatial models; 97 assesses models out of sample, including 96's.
- **Rounds 88–93** (added 2026-11-23): 88 (method attribution, owner request) first so every later round registers
  its sources; then, from Hernán and Robins and from Walker (mappings in `docs/literature/`), 89 before 90–91, which
  rely on its causal specification; 92 adds the annual denominators 91 needs; 93 is exploratory spatial modelling.
- **Rounds 82–87** (added 2026-11-22 from *Foundations of Epidemiology*; mapping in
  `docs/literature/foundations_of_epidemiology.md`): 82 first, because its labels and reporting conventions are used
  by every later round; 83–84 add the book's core measures of association; 85 frames area designations as screening;
  86 adds bias analysis on top of 83–84's measures; 87 quantifies the ecologic fallacy.
- **Round 70** fixes a user-facing bug first.
- **Round 71** closes the largest validation gap; tract studies are common in public health.
- **Rounds 72–73** turn the replications' hand-built steps into engine features.
- **Round 74** depends on 72–73, so that the replications can run through manifests.
- **Rounds 76–81** (added 2026-11-22, owner request for more inferential statistics) follow the public-health focus:
  - 76 and 77 cover disparity and surveillance measures that public-health reports use every day;
  - 78 and 79 cover policy and gap-decomposition designs;
  - 80 and 81 cover small-area and cluster methods.

  Each is validated first; a failed method stays exploratory. Round 76 should precede 79, which reuses its group
  definitions, and N39 (the ACS refresh) may interrupt when the release lands.

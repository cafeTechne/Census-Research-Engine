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
| R41 | Large-sample discrete PUMS age-cutoff RDD with 80 SDR replicate weights (Round 121) | mcp | `regression_discontinuity` | validated | causal |
| R42 | Multi-release nonmetro vs metro DiD with 4-state HKSJ pooling (Round 122) | mcp | `difference_in_differences`, `combine_estimates` | validated | policy_change |
| R43 | National Chiang II life tables, Arriaga sex-gap decomposition and YPLL-75 (Round 126) | mcp | `demography_analysis(kind="life_table"|"arriaga"|"ypll")` | validated | external_health_outcome |
| R44 | Publication bundle SHA-256, `references.bib` and LaTeX integrity verification (Rounds 124/129) | cli | `python -m census verify-bundle <bundle_dir>` | validated | reporting |
| R45 | PUMS earnings inequality (Gini, P90/P10, Atkinson) & PUMA ecologic fallacy decomposition (Round 136) | python | `census.pums_inequality.pums_inequality`, `census.ecologic.ecologic_check` | validated | pums, ecologic |
| R46 | County spatial Spearman effective-n correlation & SCPC vs. HC3 regression inference (Round 137) | python | `census.correlation.validated_correlations`, `census.scpc.fit_scpc` | validated | spatial, regression |
| R47 | County poverty KWW individual/joint rank intervals & Holm state-reference comparison (Round 139) | python | `census.ranking.rank_intervals`, `census.ranking.compare_to_reference` | validated | ranking, multiplicity |
| R48 | Standalone Layer B evidence & hypothesis-gap matrix (`geography x method x recency`) (Round 138) | layer_b | `layer_b_openscholar.gap_matrix.build_gap_matrix`, `python -m layer_b_openscholar gap-matrix` | exploratory_hypothesis_seed | literature |
| R49 | Multi-indicator county deprivation index (PCA/typology) & BEA RPP real-income adjustment (Round 141) | python | `census.composite_index.build_index`, `census.rpp.adjust_for_place` | validated | index, rpp |
| R50 | PUMS observational causal ATE (AIPW/IPW) with positivity/overlap diagnostics (Round 142) | python | `census.causal.estimate_effect`, `census.positivity.diagnose` | validated | causal, pums |
| R51 | Standalone Layer B pre-registration manifest seed drafter (`draft-seed` CLI & MCP tool) (Round 143) | layer_b | `layer_b_openscholar.manifest_seeder.draft_manifest_seed`, `python -m layer_b_openscholar draft-seed` | exploratory_hypothesis_seed | literature |
| R52 | County mortality BYM2 (`B3`) spatial disease mapping & E-value quantitative bias analysis (Round 144) | python | `census.disease_mapping.disease_map`, `census.bias_analysis.e_value` | validated | spatial, qba |
| R53 | Layer B → Layer A literature-to-preregistration handoff recipe & provenance bridge (Round 146) | recipe | `get_recipe("literature_to_preregistration")`, `layer_b_openscholar.handoff_bridge.validate_and_bridge_seed` | exploratory_hypothesis_seed | literature, manifest |
| R54 | Publication bundle SHA-256, BibTeX & LaTeX verification over Layer A MCP (Round 147) | mcp | `verify_bundle`, `get_recipe("publication_verification")` | validated | reporting, mcp |
| R55 | Introspect registered pre-registration manifest methods & citations over MCP (Round 147) | mcp | `list_manifest_methods` | validated | manifest, mcp |
| R56 | Focused `publication` & `epidemiology` MCP server profiles (Round 147) | mcp | `python mcp_server.py --profile publication|epidemiology` | validated | mcp |
| R57 | One-command offline Layer B exploratory pipeline (`local-search` → `gap-matrix` → `draft-seed` → `bridge`) (Round 153) | layer_b | `python -m layer_b_openscholar run-pipeline`, `run_exploratory_pipeline` | exploratory_hypothesis_seed | literature, manifest |
| R58 | Layer A MCP server capability introspection (`version`, `profiles`, `recipes`, `manifest_methods`) (Round 154) | mcp | `mcp_capabilities` | validated | mcp |
| R59 | Keyword-filtered workflow recipe discovery (`get_recipe(query=...)`) across 32 recipes (Rounds 153–154) | mcp | `get_recipe(query=...)` | validated | mcp, recipes |
| R60 | Extended validation (`F6–F11`) & extraction replay modular facades (`validation_extended`, `pipeline_replay`) (Rounds 151–152) | python | `census.validation_extended`, `census.pipeline_replay` | validated | architecture |
| R61 | End-to-end live Layer B SSD → Layer A pre-registered study & bundle verification (Round 156) | python | `scripts/r156_layer_b_to_layer_a_study.py`, `census.report_tables.verify_bundle` | validated | literature, spatial |
| R62 | Modularized manifest causal/epi methods & EIV/SIMEX model facades (`methods_epi`, `models_eiv`) (Rounds 157–158) | python | `census.manifest.methods_epi`, `census.models_eiv` | validated | architecture |
| R63 | Async FastMCP protocol integration verification across Layer A & Layer B servers (Round 159) | mcp | `tests/test_round159.py` | validated | mcp |
| R64 | Cross-study empirical synthesis (`R120–R156`), SSD corpus benchmark & N39 preflight tracker (Round 159) | docs | `docs/studies/r120_r156_synthesis.md`, `scripts/acs_release_preflight.py` | validated | reporting |
| R65 | 36-domain background corpus miner & OpenAlex 1-hop citation-graph expander (Round 161) | layer_b | `python -m layer_b_openscholar mine-corpus --daemon`, `expand_citations` | exploratory_hypothesis_seed | literature |
| R66 | Hybrid RAG v2 (`FTS5 + BM25 RRF + local passages`, JATS cleaning, filters, BibTeX & Evidence Briefs) (Round 162) | layer_b | `rag_query`, `evidence_brief`, `python -m layer_b_openscholar rag-query` | exploratory_hypothesis_seed | literature, rag |
| R67 | Persistent daemon ops (`systemd --user` unit generator & SSD corpus health telemetry) (Round 163) | layer_b | `corpus_health`, `python -m layer_b_openscholar corpus-health|systemd-unit` | exploratory_hypothesis_seed | literature, ops |
| R68 | Pluggable SQLite+NumPy vector store (N127 Tier 2 RAG prep) & `domain_hybrid_rag` recipe (Round 164) | layer_b | `layer_b_openscholar.vector_store.LocalVectorStore`, `get_recipe("domain_hybrid_rag")` | exploratory_hypothesis_seed | literature, rag |
| R69 | 3-way Hybrid RAG (`FTS5 + BM25 + Vector Cosine RRF`) & SSD vector sync (`sync-vectors`) (Round 166) | layer_b | `sync_vectors`, `rag_query`, `python -m layer_b_openscholar sync-vectors` | exploratory_hypothesis_seed | literature, rag |
| R70 | Modularized replicate derived-statistic algebra facade (`census.replicate_stats`) (Round 167) | python | `census.replicate_stats` | validated | architecture, replicates |
| R71 | WONDER 2018–2022 county suicide & diabetes BYM2 (`B3`) mapping + E-value QBA + bundle verification (Round 168) | python | `scripts/r168_wonder_suicide_diabetes_study.py`, `verify_bundle` | validated | spatial, qba |
| R72 | Multi-domain exploratory research agenda synthesizer across 36 domains (`build-agenda`) (Round 169) | layer_b | `build_research_agenda`, `python -m layer_b_openscholar build-agenda` | exploratory_hypothesis_seed | literature, agenda |
| R73 | Auto-vector-sync in `CorpusMiner` & incremental local passage indexing (`sync-passages`) (Round 171) | layer_b | `python -m layer_b_openscholar sync-passages <dir>`, `CorpusMiner(auto_sync_vectors=True)` | exploratory_hypothesis_seed | literature, rag |
| R74 | Modularized concordance rule/override validation facade (`census.concordance_overrides`) (Round 172) | python | `census.concordance_overrides` | validated | architecture, concordance |
| R75 | WONDER 2018–2022 county CLRD & liver disease BYM2 (`B3`) mapping + E-value QBA + bundle verification (Round 173) | python | `scripts/r173_wonder_clrd_liver_study.py`, `verify_bundle` | validated | spatial, qba |
| R76 | Multi-domain publication velocity, citation & OA PDF trend analyzer (`domain-trends`) (Round 174) | layer_b | `domain_trends`, `python -m layer_b_openscholar domain-trends` | exploratory_hypothesis_seed | literature, trends |
| R77 | Modularized panel harmonization & wide-row apportionment facade (`census.geo_crosswalk_io`) (Round 176) | python | `census.geo_crosswalk_io` | validated | architecture, crosswalk |
| R78 | Modularized spatial regression & known-variance correction facade (`census.spatial_regression_helpers`) (Round 177) | python | `census.spatial_regression_helpers` | validated | architecture, spatial |
| R79 | WONDER 2018–2022 county kidney disease & firearm BYM2 (`B3`) mapping + E-value QBA + bundle verification (Round 178) | python | `scripts/r178_wonder_kidney_firearm_study.py`, `verify_bundle` | validated | spatial, qba |
| R80 | Layer B FTS5 integrity auditor, orphan-vector pruner & SQLite compaction (`compact-corpus`) (Round 179) | layer_b | `compact_corpus`, `python -m layer_b_openscholar compact-corpus` | exploratory_hypothesis_seed | literature, ops |
| R81 | Modularized PUMS regression & PUMA geography facade (`census.pums_stats`) (Round 181) | python | `census.pums_stats` | validated | architecture, pums |
| R82 | Modularized external health source loading/joining facade (`census.health_sources_io`) (Round 182) | python | `census.health_sources_io` | validated | architecture, health |
| R83 | WONDER 2018–2022 county alcohol-induced & unintentional injury BYM2 (`B3`) + E-value QBA (Round 183) | python | `scripts/r183_wonder_alcohol_injury_study.py`, `verify_bundle` | validated | spatial, qba |
| R84 | Layer B normalized-title deduplication merger & FTS5 rebuild (`dedupe-corpus`) (Round 184) | layer_b | `dedupe_corpus`, `python -m layer_b_openscholar dedupe-corpus` | exploratory_hypothesis_seed | literature, ops |
| R85 | Layer B Tier 2 Neural BGE embeddings, OpenAlex polite pool & Europe PMC JATS XML full-text harvester (Round 186) | layer_b | `harvest_fulltext`, `sync-vectors --model BAAI/bge-small-en-v1.5`, `neural_benchmark` | exploratory_hypothesis_seed | literature, rag |
| R86 | Layer A environment & bundled-data integrity self-check (`doctor`) and dual-MCP quickstart (Round 187) | cli | `python -m census doctor --json`, `examples/mcp/dual_mcp_config.json`, `docs/dual_mcp_quickstart.md` | ok_true_zero_secret_leak | ops, setup |
| R87 | Flagship 11-cause CDC WONDER county mortality spatial atlas & 4-pitfall publishable manuscript package (Round 188) | python | `scripts/r188_flagship_manuscript_builder.py`, `docs/studies/r188_flagship_manuscript.md` | verified_bundle_11_causes | epi, publication |
| R88 | Full-repository regression sweep, release hygiene & `v0.185.0` readiness audit (Round 189) | cli | `scripts/release_hygiene_check.py`, `docs/audits/v0185_release_readiness.md` | release_hygiene_ok | ops, release |

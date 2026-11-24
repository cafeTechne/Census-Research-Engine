# Census Research Engine

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23925301.svg)](https://doi.org/10.5281/zenodo.23925301)

A research toolkit for US Census data: extract comparable measures across places and years, quantify uncertainty, and carry an analysis through to tables, maps and reproducible study outputs. The engine combines ACS area estimates, PUMS microdata, 2020 Census counts and selected external health outcomes. It offers **81 MCP tools**, **28 pre-registered manifest methods**, **40 offline-tested agent routing contracts**, a Python library and a command-line interface.

Use it to compare counties or neighborhoods, study associations while accounting for noisy ACS predictors and spatial dependence, construct custom population tabulations, measure segregation or income inequality, and evaluate agreement between sources. Statistical methods have different validated ranges; an available method is not automatically suitable for every research design. Each inference method was checked by a simulation whose pass criterion was fixed in advance (90% intervals must cover at least 86% of the time); methods or settings that failed are still available but are marked exploratory in their results (`validated: false` and a note). [STATUS.md](STATUS.md) records the current release, validation evidence and remaining limitations.

Extraction keeps estimates paired with margins of error, checks variable meanings across releases, converts dollar values to constant dollars, and records provenance. Calculations are checked against [Census-published values](#validation-against-census-published-values); inference methods have separate simulation audits.

| Interface | Entry point | When to use it |
| :--- | :--- | :--- |
| MCP server | `mcp_server.py` | An MCP client or research agent selects and runs tools; [profiles](#mcp-server) control which tools it sees |
| Command line | `python -m census` / `census-acs` | Script extraction and supported analyses; `tool <name>` exposes a subset of the shared workflows |
| Python library | `census` | Notebooks, custom pipelines and methods without a standalone MCP tool |
| Desktop GUI | `acs_downloader.py` (Tkinter) | Point-and-click extraction; maintenance mode, with a smaller feature surface |

Extraction uses the shared pipeline. Advanced analyses are exposed through the MCP/CLI workflows, manifests or Python; the GUI does not expose the whole research engine.

Start with [choosing an analysis](#inference), [MCP setup and tool inventory](#mcp-server), or the [research workflow](#a-reproducible-research-workflow).

**Latest tagged release: v0.77.0** ([DOI 10.5281/zenodo.24444186](https://doi.org/10.5281/zenodo.24444186)):
- disparities between population groups and the Kitagawa decomposition;
- joinpoint trends and ratios of age-adjusted rates;
- difference-in-differences for policies adopted in different years;
- Oaxaca–Blinder and Fairlie decompositions on PUMS;
- small-area estimates for proportions near 0 or 1 and across releases;
- a spatial scan for clusters of high county counts.

**Recent development (Rounds 82–119, v0.115.0):**
- **Epidemiology, causal & policy designs:** stratified Mantel–Haenszel / Breslow–Day–Tarone / RERI (and validated PUMS Hotelling *F* homogeneity at `min_n ≥ 500`), marginal risk ratios/differences & attributable fractions, area designation PPV predictive intervals (`prob80`, `point`, `lower`), E-values & validated probabilistic misclassification, Fuller $\alpha=4$ ecologic slope, target-trial & DAG checks, overlap/truncated IPW & g-formula, multi-confounder parametric g-formula for annual policy panels (`p ≥ 1`), sharp/fuzzy RDD (discrete replicates, continuous CCT CER bandwidth, and density test), matching (ATE/ATT, CEM, caliper) & triple differences, FCS multiple imputation (PMM/norm, δ-sensitivity, FMI), demographic life tables & Arriaga decomposition (`demography_analysis`), BYM2 spatial disease mapping (`method="B3"`, `median E ≥ 30`), SDR bias-corrected Shannon entropy (`n ≥ 150`), Joinpoint AAPC bootstrap-*t*, count-scale disparity indices (`min_events ≥ 100`), observed Lin's CCC, and random-effects meta-analysis (NNF prediction interval, truncated Knapp–Hartung meta-regression, and RE Egger for `k ≥ 10`).
- **Pre-registered manifests & templates:** **28 manifest methods** (complete confirmatory coverage across area, panel, causal, spatial, demographic, and summary designs) with schema-validated templates in `examples/manifests/templates/` and complete citation keys in `census/references.py`.
- **Verification & release tooling:** **40 offline-tested agent routing contracts** (`docs/agent_routing.md`), **8 published textbook reference benchmarks** (`tests/test_reference_benchmarks.py`), **10/10 out-of-DGP adversarial stress tests** (`docs/audits/confirmed_stress_audit.md`), offline N39 ACS 2021–2025 preflight (`scripts/acs_release_preflight.py`), and automated release-hygiene checks (`scripts/release_hygiene_check.py`).

[CHANGELOG.md](CHANGELOG.md) lists every round.

## Installation

Requires Python 3.11 or later and SciPy 1.16 or later.

```bash
git clone https://github.com/cafeTechne/Census-Research-Engine
cd Census-Research-Engine
pip install -r requirements.txt
```

Or install it as an editable package from the clone (`pip install -e .`, or `pip install -e ".[dev]"` for pytest and ruff; the toolkit reads its metadata archive and data files from the repository), which adds the `census-acs` command (same as `python -m census`) and `census-acs-mcp` (the MCP server; `census-acs-mcp --profile core`). Releases are listed in `CHANGELOG.md`; each tagged release is archived on Zenodo with a DOI to cite.

Price-index data (R-CPI-U-RS, CPI-U, and C-CPI-U, 2000–2024) ships with the repository, so constant-dollar conversion works out of the box.

**Refreshing R-CPI-U-RS** (once a year, after BLS publishes a new annual average). BLS publishes the series only as an Excel file and blocks anonymous scripted downloads. Download `https://www.bls.gov/cpi/research-series/r-cpi-u-rs-allitems.xlsx` in a browser, save it over `data/price_indexes/source/r-cpi-u-rs-allitems.xlsx`, and run:

```bash
python scripts/update_price_indexes.py --r-cpi-u-rs-xlsx data/price_indexes/source/r-cpi-u-rs-allitems.xlsx
```

Alternatively, set `BLS_USER_AGENT` to an identifying User-Agent that includes a contact email (BLS's requirement for automated clients) and run the script without arguments. A year the index does not cover fails with `PRICE_INDEX_UNAVAILABLE`.

## Configuration

| Variable | Purpose |
| :--- | :--- |
| `CENSUS_API_KEY` | Census API key ([request one](https://api.census.gov/data/key_signup.html)); requests without a key are rate-limited |
| `CENSUS_CACHE_PATH` / `CENSUS_CACHE_DISABLED=1` | SQLite query cache location (default `.cache/census_cache.db`), or disable it |
| `CENSUS_METADATA_DIR` | Alternate per-vintage metadata archive (default `metadata/`) |
| `CENSUS_CROSSWALK_DIR` | Alternate override directory (default `crosswalks/`) |
| `CENSUS_PRICE_INDEX_DIR` | Alternate price-index directory (default `data/price_indexes/`); not checksum-verified, its CSV's SHA-256 is recorded instead |
| `CENSUS_PRICE_PARITY_DIR` | Alternate Regional Price Parity directory (default `data/price_parities/`); same treatment |
| `BLS_USER_AGENT` | Identifying User-Agent for `scripts/update_price_indexes.py` |
| `CENSUS_VRE_DIR` | Cache for downloaded Census Variance Replicate Estimate files (default `.cache/vre/`) |
| `CENSUS_WWW2_MIN_INTERVAL` / `CENSUS_WWW2_ATTEMPTS` / `CENSUS_WWW2_BACKOFF_BASE` / `CENSUS_WWW2_REJECTED_RETRY_DELAY` | census.gov file downloads (`census/http.py`): seconds between requests to one host (default 1), attempts on HTTP 429/5xx or connection errors (4), backoff base in seconds (2; doubled per retry, capped at 60, honours `Retry-After`), and the wait before the single retry of a firewall "Request Rejected" page (30). A rejection that persists names the cache path where a browser-downloaded copy of the file is picked up; for a rejected (or 404) B01003 VRE file, `fetch_vre` instead reads the identical B01001 line 1 and records the substitution (`attrs["substitution"]`, with a warning) |
| `CENSUS_LIVE_TESTS=1` | Enable live API contract tests and the live validation battery |
| `CENSUS_MCP_PROFILE` | MCP tool profile (`full`, `core`, `core_spatial`, `review`, `verification`); same as `--profile` |
| `CENSUS_HEALTH_OFFLINE=1` | Use only locally cached external health data (no downloads) |
| `CENSUS_DOTENV` | Explicit `.env` file. Otherwise the engine loads the first `.env` found upward from the working directory, then from the package location (an installed engine finds your project's `.env`); variables already set are never overridden |
| `CENSUS_PROGRESS=0` | Silence progress lines (stderr) from long workflows: `run_manifest`, `batch_download`, replicate refits |
| `CENSUS_VERIFICATION_REQUEST` | The locally reviewed proposition pinned for `--profile verification` |

**Exact proposition verification (opt-in).** The [verification workflow](docs/verification.md) pins a locally reviewed proposition through `CENSUS_VERIFICATION_REQUEST` before the server starts with `--profile verification`; model tools cannot approve formalizations. `python scripts/verification_eval.py --request request.json` prepares prompts and scores transcripts offline and contacts no model service. `scripts/verification_live.py --run-model ...` tests a chosen local runtime explicitly; the guide lists its settings and raw traces.

## Quick start

### Python

```python
from census import ResearchOptions, build_entities, plan_extraction, run_batch

entities = build_entities("tract", "48", ["453"])       # all tracts in Travis County, TX
options = ResearchOptions(compute_reliability=True, inflation_base_year=2022, include_codebook=True)

plan = plan_extraction("B19013", entities, range(2015, 2023), "parquet", options,
                       variables=["B19013_001"])        # name the variables you analyze
print(plan["would_block"], plan["selection"], plan["issues"][:3])

result = run_batch("B19013", entities, range(2015, 2023), "out", "parquet", options,
                   variables=["B19013_001"])
print(result["success"], result.get("error_code"), result.get("panel_path"))
```

Results are dictionaries. Failures carry `success: False`, an `error_code`, and `error`; nothing raises on API failure.

### Command line

```bash
python -m census plan    --table DP02 --geo state --state 36 --years 2018-2022 --variables DP02_0016 --json
python -m census extract --table DP02 --geo state --state 36 --years 2018-2022 --variables DP02_0016 --out out --json
python -m census concordance --table B27001 --years 2016-2017 --variables B27001_006 --json
python -m census describe --code DP02_0002PE --year 2018
python -m census extract --table B19013 --geo county --state all --years 2022 --format parquet --out out
python -m census replay out/B19013_extraction_metadata.json --json
python -m census derive proportion --estimates 4500,30000 --moes 400,900 --json
python -m census aggregate --input out/B17001_tract_panel_2023.csv --groups groups.csv --year 2023 \
    --derive '[{"name": "poverty_rate", "op": "proportion", "num": "B17001_002E", "den": "B17001_001E"}]'
python -m census validate --offline
```

Exit codes: `0` success, `2` invalid input, `3` concordance review required, `4` API or data failure.

### MCP server

```bash
claude mcp add census -- python mcp_server.py
```

Call `get_recipe()` to list the 26 task guides, then `get_recipe(name="regression_sampling_error")` (or another recipe) for the steps and applicable limits. `get_recipe` is in the core and full profiles. `get_research_protocol` returns the full protocol in profiles that expose it. Client configuration is in [docs/claude_setup.md](docs/claude_setup.md).

| Profile | Tools | Use |
| :--- | ---: | :--- |
| `full` (default) | 81 | All registered tools; use this for the complete research workflow |
| `core` | 16 | A smaller set for discovery, extraction, basic models, group/PUMS tests and outputs; guided results include `summary` and `next_step` |
| `core_spatial` | 17 | Core plus `spatial_autocorrelation`; advanced tools such as `rank_areas` still require `full` |
| `review` | 10 | Variable concordance and independent review of overrides |
| `verification` | 1 | The separate [operator-pinned proposition workflow](docs/verification.md); requires its reviewed request |

Select a profile with `python mcp_server.py --profile core` or `CENSUS_MCP_PROFILE=core`. Switching profiles changes tool visibility, not the underlying statistical methods. Small local-model setup and evaluations are in [docs/local_models.md](docs/local_models.md).

The CLI runs every shared analysis workflow through `python -m census tool <name>` (Round 64 added `compare_groups`, `test_association`, `estimate_effect`, `check_agreement`, `combine_estimates`, `rank_areas`, `build_index`, `list_health_sources`, `run_variant` and `interrupted_series`). The MCP tools it does not list are discovery, metadata and review tools with their own CLI subcommands or server-only behaviour. For a supported offline calculation, estimate the difference that two MOEs can detect:

```bash
python -m census tool minimum_detectable_difference --arg moe1=2.1 --arg moe2=2.4 --json
```

<details>
<summary>All 26 recipes</summary>

| Recipe | Covers |
| :--- | :--- |
| [`preregistered`](docs/recipes/preregistered.md) | Pre-registered (manifest) confirmatory analysis |
| [`regression_sampling_error`](docs/recipes/regression_sampling_error.md) | Regression whose SEs include ACS sampling error |
| [`compare_counties`](docs/recipes/compare_counties.md) | Compare a rate between two counties in one release |
| [`tract_trend`](docs/recipes/tract_trend.md) | Trend in a tract or county rate using non-overlapping releases |
| [`policy_change`](docs/recipes/policy_change.md) | Policy or event effects: difference-in-differences on non-overlapping releases, interrupted annual series (Round 75) |
| [`group_comparison`](docs/recipes/group_comparison.md) | Compare an area outcome across groups of areas: t-test, ANOVA, ANCOVA, interactions (Round 31) |
| [`rank_methods`](docs/recipes/rank_methods.md) | Rank and partial correlations and rank comparisons of groups with ACS error (Round 33) |
| [`rank_areas`](docs/recipes/rank_areas.md) | Rank areas with rank intervals, and compare each area with the state value (Round 34) |
| [`composite_index`](docs/recipes/composite_index.md) | Composite (deprivation) index with score intervals, quintile stability and alpha (Round 36) |
| [`agreement`](docs/recipes/agreement.md) | Agreement between two sources of the same quantity: bias, kappa, limits, concordance (Round 37) |
| [`combine_estimates`](docs/recipes/combine_estimates.md) | Pool replications (meta-analysis), test equivalence, plan power (Round 38) |
| [`causal`](docs/recipes/causal.md) | Treatment effects, instrumental variables and mediation with ACS data, and their assumptions (Round 41) |
| [`pums_tests`](docs/recipes/pums_tests.md) | Survey-correct tests and intervals on PUMS microdata: tables, odds ratios, means, medians (Round 32) |
| [`small_area`](docs/recipes/small_area.md) | Small-area ACS estimates (Fay-Herriot) and descriptive event-count smoothing (EB) |
| [`health_inequality`](docs/recipes/health_inequality.md) | Area health inequality indices, indirectly standardized ratios, and disparities between population groups (Kitagawa too) with ACS uncertainty |
| [`external_health_outcome`](docs/recipes/external_health_outcome.md) | Health outcome from CDC PLACES, USALEEP, County Health Rankings or WONDER, without circularity; binomial counts with denominator trials and robust (HC3) SEs |
| [`segregation`](docs/recipes/segregation.md) | County residential segregation from tract counts with strict ACS replicate uncertainty |
| [`context_covariates`](docs/recipes/context_covariates.md) | County covariates from other sources (County Business Patterns, ERS county types and rural-urban codes, CHR additional measures; Round 92: Population Estimates, LEHD LODES jobs, ACS migration flows), joined to an ACS frame (Round 72) |
| [`custom_geographies`](docs/recipes/custom_geographies.md) | Neighborhoods and combined areas: mapping tracts to polygons, summed counts with MOEs, medians from brackets, 2010/2020 tracts (Round 75) |
| [`dollars`](docs/recipes/dollars.md) | Inflation (R-CPI-U-RS) and place price levels (BEA RPPs) for dollar estimates (Round 75) |
| [`spatial_patterns`](docs/recipes/spatial_patterns.md) | Global and local spatial clustering (Moran's I, LISA) and maps with reliability (Round 75) |
| [`cross_release`](docs/recipes/cross_release.md) | Variable concordance across releases and reviewed crosswalk decisions (Round 75) |
| [`decennial_counts`](docs/recipes/decennial_counts.md) | Use 2020 Census counts (P.L. 94-171, DHC) without inventing margins of error |
| [`confounding`](docs/recipes/confounding.md) | Confounders and effect modifiers: stratified analysis, Mantel-Haenszel, homogeneity, additive interaction (Round 83) |
| [`reporting`](docs/recipes/reporting.md) | Publication tables, maps, codebooks and exploratory results bundles (Round 75); epidemiologic reporting conventions: measure types, ecologic and cross-sectional limits, allocation shares, Table 1 (Round 82) |
| [`replications`](docs/recipes/replications.md) | Rerun the five published replications (Rounds 66-69) and check the engine still reproduces them (Round 74) |

</details>

<details>
<summary>All 81 MCP tools, grouped by purpose</summary>

The analysis tables below explain which to choose. This inventory also includes discovery, maintenance and review tools.

| Purpose | Tool names |
| :--- | :--- |
| Orientation | `get_recipe`, `get_research_protocol` |
| Find geography and measures | `list_states`, `list_vintages`, `list_places`, `list_counties`, `list_tracts`, `list_zctas`, `search_tables`, `list_variables`, `describe_variable` |
| Plan, extract and reproduce data | `plan_extraction`, `download_table`, `batch_download`, `fetch_table_data`, `query_data_profile`, `replay_extraction`, `generate_codebook`, `cache_import` |
| Review cross-release meanings | `check_variable_concordance`, `draft_crosswalk_override`, `record_crosswalk_review`, `draft_rule_override`, `record_rule_review`, `validate_crosswalks` |
| Derive and aggregate | `derive_estimate`, `check_replicate_availability`, `aggregate_geographies`, `median_from_distribution`, `apportion_tracts` |
| Assess precision and compare estimates | `calculate_cv`, `calculate_significance`, `batch_significance`, `trend_test`, `minimum_detectable_difference`, `reliability_profile` |
| Analyze area-level relationships | `build_analysis_frame`, `fit_model`, `compare_groups`, `correlation_matrix`, `rank_areas`, `build_index`, `disparity_measures`, `bias_analysis` |
| Agreement, evidence and causal designs | `check_agreement`, `combine_estimates`, `estimate_effect`, `regression_discontinuity` |
| Geographic analysis and maps | `get_boundaries`, `custom_area_mapping`, `make_map`, `make_web_map`, `spatial_autocorrelation`, `spatial_regression`, `spatial_scan`, `spatial_model` |
| Small-area and hierarchical models | `small_area_estimates`, `spatial_small_area_estimates`, `multilevel_model`, `designation_accuracy` |
| Survey microdata | `pums_tabulate`, `test_association`, `pums_regression`, `decompose_gap`, `stratified_analysis` |
| Time, demography and purchasing power | `interrupted_series`, `joinpoint`, `demography_analysis`, `difference_in_differences`, `adjust_inflation`, `adjust_for_place`, `place_adjust_frame` |
| Register studies and publishable outputs | `create_manifest`, `run_manifest`, `run_variant`, `make_figure`, `make_table`, `make_results_bundle`, `list_health_sources` |
| Numerical checks and exact verification | `run_validation`, `verify_proposition` |

</details>

## Cross-release concordance

ACS variable meanings drift between releases. The offline audit ([docs/audits/concordance_audit.md](docs/audits/concordance_audit.md)) covers every profile, subject, and comparison-profile table for 2009–2024. It finds thousands of renumbered lines, reused codes, and changed definitions. Real examples:

| Case | Example |
| :--- | :--- |
| Renumbered | DP02 "average household size": `DP02_0015` (2018) became `DP02_0016` (2019) |
| Code reused | `DP02_0002`: "family households" (2018), then "married couple family" (2019) |
| Definition changed | `B27001_006`: "6 to 17 years" (2016), then "6 to 18 years" (2017) |

How it is handled:

1. **Per-vintage metadata.** `metadata/<dataset>/<year>/` holds every release's `variables.json` and `groups.json` (gzipped, SHA-256 in `metadata/manifest.json`), so labels and matching never depend on a single vintage.
2. **Concordance.** Labels are normalized by tested, versioned rules (measurement prefixes, the dollar year, punctuation, part order). Only exact matches merge automatically. Renumbered lines become one column, and reused codes become separate columns.
3. **Continuity check.** Every concept that spans years is compared at the national level. A change that is both significant and implausible blocks the run.
4. **Selection.** `variables=` names what the analysis uses. A bare code resolves in the latest requested year, `YEAR:CODE` pins a vintage, and concept IDs are exact.
5. **Modes.** `fail` (default) stops when unresolved issues touch selected variables, `strict` proceeds and reports, and `code` is the legacy raw-code mode.
6. **Reviewed overrides.** `crosswalks/<dataset>/<table>.csv` records `merge`, `split`, and `exclude` decisions, each drafted and then independently reviewed (by an agent or a human) with generated evidence and a census.gov source. The rules are in [docs/agent_protocol.md](docs/agent_protocol.md) and enforced in code.
7. **Table-scoped rules.** `crosswalks/<dataset>/<table>_rules.csv` holds reviewed regex rewrites for systematic redesigns (two rules resolve 165 of the 171 S1701 lines changed in 2017). Rules that would change any number in a label are rejected, and merged concepts are still continuity-checked. See [docs/rule_overrides.md](docs/rule_overrides.md).

Each multi-year run writes `<table>_concordance.csv` (every output column traced to its code in each year) and `<table>_concordance_issues.json`.

## Concepts

### Geography levels

| `geo_level` | Summary level | `GEOID` | `codes` in `build_entities` |
| :--- | :--- | :--- | :--- |
| `us` | 010 | `US` | none |
| `state` | 040 | `SS` | none; `state_code` required (`"all"` = 50 states + DC everywhere) |
| `county` | 050 | `SSCCC` | county FIPS; default all in state |
| `tract` | 140 | `SSCCCTTTTTT` | county FIPS; one request per county; default all |
| `block group` | 150 | `SSCCCTTTTTTG` | county/tract selection; ACS five-year detailed tables from 2013 |
| `place` | 160 | `SSPPPPP` | place FIPS (required) |
| `zcta` | 860 | `ZZZZZ` | ZCTAs; default all ZIPs in the state (`zip2fips.json`); requested in chunks of 50 |
| `msa` | 310 | `MMMMM` | CBSA codes; default all metro and micro areas |
| `block` | 100 | `SSCCCTTTTTTBBBB` | 2020 Census only (`dec/pl`, or DHC `H1`): county FIPS; one request per county, default one per state |

### Datasets

| `dataset` | Endpoint | Tables | Variable suffixes |
| :--- | :--- | :--- | :--- |
| `acs5` | `/acs/acs5` | `B…`, `C…` | `E`, `M`, `EA`/`MA` annotations |
| `profile` | `/acs/acs5/profile` | `DP02`–`DP05` | adds `PE`/`PM` percentages |
| `subject` | `/acs/acs5/subject` | `S…` | `E`, `M` per column (`_C01_`, …) |
| `cprofile` | `/acs/acs5/cprofile` | `CP02`–`CP05` | codes embed the period; `SS` significance flags |
| `dec/pl` | `/2020/dec/pl` | 2020 Census P.L. 94-171 redistricting data: `P1`–`P5`, `H1` | `N` (count), `NA` annotation; no MOE |
| `dec/dhc` | `/2020/dec/dhc` | 2020 Census Demographic and Housing Characteristics: e.g. `P1`, `P12`, `H1`, `H3` | `N` (count), `NA` annotation; no MOE |

The ACS dataset is inferred from the table code. The 2020 Census datasets are selected with `dataset="dec/pl"` / `"dec/dhc"` or `product="decennial"` (DHC); see [2020 Decennial Census](#2020-decennial-census).

### Outputs

| `output_format` | Files |
| :--- | :--- |
| `both`, `wide_only`, `melted_only` | Per entity folder: wide `compiled_unmelted_data.csv` and/or long per-year CSVs |
| `excel` | Per entity folder: workbook with `Wide_Data` and `Melted_Data` sheets |
| `panel` | `<table>_<geo>_panel_<span>.csv`, one row per `(geoid, year)` |
| `parquet` | The same panel as Parquet (snappy, native dtypes) |

Every run also writes `<table>_extraction_metadata.json`. It records the request, the package version and git commit, the metadata checksum per vintage, the concordance mode and normalization version, the overrides applied, the price index and its source, the advisories, and the failed calls. `include_codebook=True` adds `<table>_codebook.csv` (code, slug, measurement type, description, concept, universe, unit, concept ID, codes by year, concordance status).

### Column conventions

| Column | Meaning |
| :--- | :--- |
| `GEOID` / `geoid` | Standard Census GEOID (TIGER/Line join key) |
| `Year` / `year` | ACS 5-year period end year (2022 = 2018–2022) |
| `<base>E`, `<base>M` | Estimate and 90% margin of error; in panels, `<base>` is the concept's latest-year code |
| `<base>__<first>_<last>` | Concept segment when a code was reused for different measures |
| `<base>_SE`, `_CV`, `_RELIABILITY` | Derived standard error, CV (%), and reliability flag |
| `*_est`, `*_moe`, `*_pct`, `*_pct_moe`, `*_se`, `*_cv`, `*_rel`, `*_sig` | Panel slugs; `slug_style="code"` gives Stata-safe names |
| `<base>N`, `*_count` | 2020 Census count (and its panel slug); no MOE, SE or CV columns exist |

## Methodology

| Operation | Rule | Function |
| :--- | :--- | :--- |
| Standard error | `SE = MOE / 1.645` | `census.stats.standard_error` |
| Coefficient of variation | `CV = SE / estimate × 100`; High ≤ 15%, Moderate ≤ 30%, Low > 30% | `census.stats.coefficient_of_variation` |
| Difference test | `Z = |X1 − X2| / sqrt(SE1² + SE2²)`, with the difference SE scaled by `sqrt(1 − overlap/5)` for overlapping periods | `census.stats.z_test` |
| Sum of estimates | `MOE = sqrt(Σ MOE²)` over every component, including zeros (Handbook 2020 ch. 8; the older largest-zero-MOE rule is available) | `census.derived.sum_estimates` |
| Proportion (subset) | `MOE = sqrt(MOE_X² − P²·MOE_Y²) / Y`; ratio formula if the radicand is negative | `census.derived.proportion` |
| Ratio, product, percent change | Handbook 2020 ch. 8 formulas | `census.derived` |
| Exact variance | `Var = 4/80 · Σ (rep_r − est)²` over Census's 80 replicate estimates | `census.replicate`, `census.variance` |
| Median for custom areas | Sum bracket counts, linear interpolation (ACS Subject Definitions); MOE by replicates or an approximation | `census.medians` |
| Custom geographies | Sum counts, then derive; non-additive measures refused | `census.aggregate` |
| Multiple comparisons | Holm (default), Bonferroni, Benjamini–Hochberg, Benjamini–Yekutieli | `census.multitest` |
| Tract harmonization | `Σ w·X`, `MOE = sqrt(Σ (w·MOE)²)` with Census 2010/2020 tract relationship weights | `census.geo_crosswalk` |
| Sentinel values | Census jam values (`-999999999`, `-666666666`, …) become null | `census.stats.clean_census_sentinels` |
| Constant dollars | `real = nominal × index_base / index_year` on dollar-valued estimates and MOEs (not counts in dollar brackets); default R-CPI-U-RS, optional CPI-U and C-CPI-U | `census.inflation.deflate_dataframe` |

Price indexes live in `data/price_indexes/` and are generated from BLS sources by `scripts/update_price_indexes.py`, with checksums. Each bundled CSV (and each Regional Price Parity CSV in `data/price_parities/`) is checked against the `csv_sha256` in its sidecar JSON the first time it is loaded in a process; a mismatch raises `BundledDataIntegrityError` naming the file and both hashes. Tables from `CENSUS_PRICE_INDEX_DIR` or `CENSUS_PRICE_PARITY_DIR` are not checked; their SHA-256 is recorded in `price_index_info()["custom_table"]` (and so in the extraction metadata) or in the RPP adjustment notes. The sidecar JSON files themselves (including provisional values) are not hashed. R-CPI-U-RS values are the workbook's annual averages; the source workbook is kept in `data/price_indexes/source/` and its SHA-256 is recorded. CPI-U annual averages are computed from monthly values (they match BLS's published averages to ±0.001). 2025 is omitted because BLS did not publish October 2025; the R-CPI-U-RS workbook's 11-month 2025 average is stored as provisional and used only with `allow_provisional_index=True`, which adds an advisory. The Census Bureau switched its CPS income reports to C-CPI-U in 2023 but still uses R-CPI-U-RS for all ACS years.

Every derived result records its `method` (for example `proportion`, `proportion_ratio_fallback`, `replicate`, `median_interpolated`, `apportioned`) alongside `estimate`, `moe`, `se`, and `cv_percent`. Approximation formulas ignore covariance; for estimates that feed a hypothesis test, check `check_replicate_availability` and prefer replicate variances.

## Validation against Census-published values

`python scripts/validate_against_census.py` (or `python -m census validate`, or the MCP tool `run_validation`) recomputes numbers the Census Bureau publishes independently and compares them with this toolkit's output. Every check runs offline against frozen fixtures in the normal test suite, and CI runs the live battery weekly. The latest report is [docs/audits/validation_report.md](docs/audits/validation_report.md).

| Check | Recomputed by the toolkit | Census-published value |
| :--- | :--- | :--- |
| F1 | Pipeline output cells (panel, Parquet) | Raw API cells |
| F2 | Proportions and MOEs from detailed tables | Data Profile percentages and percent MOEs |
| F3 | MOEs from 80 replicate estimates | Published MOEs |
| F4 | Exact replicate proportion MOEs | Data Profile percent MOEs |
| F5 | Medians from distribution tables | Published medians |
| F6 | Prior-period dollars adjusted with R-CPI-U-RS | Comparison Profile values in current dollars |
| F7 | Z-tests between periods | Comparison Profile significance flags |
| F8 | Sums of counties | State estimates |
| F11 | 2020 Census state population; block housing units summed to tracts and counties; DHC vs P.L. 94-171 | Apportionment-release state totals; published tract and county totals (invariants and hierarchy) |

## Inference

Choose the observation unit first. **Area analyses** use one row per county, tract or other geography; **PUMS analyses** use weighted person or household records. Area associations do not establish individual-level relationships. The tool names below refer to the **full MCP profile**; selected workflows also have CLI access. Recipes give parameter details.

| Research question | Start with | When and how to use it |
| :--- | :--- | :--- |
| Is a difference meaningful given the MOEs? | `calculate_significance`; `batch_significance` for many areas | Two estimates or releases; use multiplicity correction when comparing many areas. For design planning, use `minimum_detectable_difference` and `reliability_profile`. [Compare counties](docs/recipes/compare_counties.md) |
| Is there change over time? | `trend_test`; `difference_in_differences` for a treatment/control design (`design="staggered"` for staggered adoption, `"triple"` for triple differences, `"msm"` exploratory for time-varying confounders); `interrupted_series` (full profile) for an annual series with a break; `joinpoint` (full profile) for an annual series with no known break date (`aberration="historical_limits" \| "ears_c2"` flags the latest year) | Trends need at least three non-overlapping ACS five-year releases. DiD needs a defensible comparison group and parallel-trends assumptions. Interrupted series need annual, non-ACS-window data and are validated from 17 points ([below](#methods-accessed-through-manifests-or-python)). [Tract trends](docs/recipes/tract_trend.md), [policy change](docs/recipes/policy_change.md) |
| How are area characteristics associated? | `build_analysis_frame` → `fit_model` | OLS/WLS or GLMs with ACS replicate information, marginal risk ratios/differences (`marginal=...`), and FCS multiple imputation (`impute=[...], impute_method="pmm" \| "norm"`, Round 100). Replicate refits describe sampling variability; they do not remove predictor measurement-error bias. [Regression](docs/recipes/regression_sampling_error.md) |
| Are noisy predictors biasing the slope? | `fit_model(method="eiv")` or `method="regression_calibration"` | EIV corrects linear-model measurement error using replicates. Calibration supports selected GLMs; binomial needs `se_method="jackknife"`. Check the reported reliabilities and validated range. [Regression](docs/recipes/regression_sampling_error.md) |
| Are neighboring areas correlated? | `fit_model(..., spatial="scpc")` for naive slopes; corrected EIV/calibration have separate spatial routes | SCPC is validated for OLS, Poisson and binomial slopes on two geographies (MI/NY and OH/PA); each model has a default benchmark `rho_bar`. Corrected linear EIV uses `spatial="clusters"` or `"error"`; calibrated GLMs use `spatial="clusters"`. These estimate different targets. Reliability and covariate-count gates apply. Manifests reach the same routes through `args.spatial_scpc`, `args.spatial: "clusters"` and `args.spatial: true` (correlations). [Spatial choices](#choosing-uncertainty-and-spatial-inference) |
| How does an outcome differ across groups? | `compare_groups` | t-tests, ANOVA/ANCOVA, interactions, multivariate outcomes and rank comparisons. Validated omnibus routes use wild-score bootstrap or selected IM tests; ordinary F references failed validation. [Group comparison](docs/recipes/group_comparison.md) |
| Are variables correlated after accounting for uncertainty? | `correlation_matrix` | Pearson, Spearman, Kendall and partial correlations. Pearson/partial need replicate information for the validated sampling-error interval; dependent areas need `spatial=True`. [Rank methods](docs/recipes/rank_methods.md) |
| Which areas are reliably high or low? | `rank_areas` | Report rank intervals, simultaneous intervals or tests against a reference. Point ranks alone hide uncertainty. Suppressed/missing areas are excluded and listed. [Ranking](docs/recipes/rank_areas.md) |
| Can several indicators describe one construct? | `build_index` | PCA/equal-weight scores, or a paper's published loadings (`method="loadings"`, Round 73), with intervals, quintile stability and Cronbach's alpha; use `spatial=True` for alpha under spatial dependence. Inspect loadings and construct validity; exclude the outcome from its own index. [Composite index](docs/recipes/composite_index.md) |
| Do two sources measure the same thing? | `check_agreement` | Bias, quintile kappa and Bland–Altman limits of agreement. High correlation alone does not establish agreement; CCC intervals remain exploratory. [Agreement](docs/recipes/agreement.md) |
| Can estimates be pooled, or considered practically equivalent? | `combine_estimates` | Paule–Mandel/REML + Hartung–Knapp pooling of independent estimates with Q-profile τ² intervals (validated), TOST equivalence, power, plus exploratory prediction intervals, leave-one-out, meta-regression and Egger test (Round 102). Declare the equivalence margin in advance. [Combining evidence](docs/recipes/combine_estimates.md) |
| Does an outcome jump at an age or threshold cutoff? | `regression_discontinuity` (full profile) | Robust bias-corrected regression discontinuity, sharp or fuzzy (Round 98). Validated for PUMS ages with replicate weights (e.g. insurance at 65); continuous running variables and the density test are exploratory. [Causal designs](docs/recipes/causal.md) |
| What can a policy or exposure plausibly cause? | `estimate_effect`; `difference_in_differences` for policy timing | Target-trial and DAG checks (Round 89), positivity diagnostics with overlap/truncated weights (Round 90), matching (`kind="matching"`, Round 99), AIPW/IPW/RA, IV and mediation. Calibration is available for noisy confounders/mediators; weak instruments need the Anderson–Rubin interval. [Causal designs](docs/recipes/causal.md) |
| How robust is an association to unmeasured confounding or misclassification? | `bias_analysis` (full profile) | E-values (validated, deterministic) and a misclassification correction of 2 x 2 tables (probabilistic interval exploratory) (Round 86). [Bias analysis](docs/recipes/reporting.md#bias-and-sensitivity-analyses-round-86) |
| Is a third variable a confounder or an effect modifier? | `stratified_analysis` (full profile) | Crude, stratum-specific and Mantel-Haenszel adjusted RR/OR/RD for county count tables or PUMS, homogeneity tests, RERI and a descriptive confounder/effect-modifier label (Round 83). Never adjust for a mediator. [Confounding](docs/recipes/confounding.md) |
| Does an area-level association hold for individuals? | `pums_regression(..., ecologic_check=...)` | Within-PUMA (individual), between-PUMA, contextual and area-level associations and the ecologic gap (Round 87; logit decomposition validated, risk-difference scale exploratory). [Area versus individual](docs/recipes/pums_tests.md#area-versus-individual-associations-round-87) |
| How much of a group gap is explained by composition? | `decompose_gap` (full profile) | Oaxaca–Blinder (numeric outcomes) or Fairlie (0/1 outcomes) on PUMS with replicate-weight intervals (Round 79). Totals validated from 300 records in the smaller group, detailed parts from 1,000. Explained is composition, not causation. [Decomposing a gap](docs/recipes/pums_tests.md#decomposing-a-gap-round-79) |
| How do individuals or households differ? | `pums_tabulate`, `test_association`, `pums_regression` | Weighted custom tabulations, Rao–Scott tables, mean/median and OR/RR comparisons, and survey regressions. Use all 80 replicate weights. [PUMS](docs/recipes/pums_tests.md) |
| How unequal are individual or household incomes? | `test_association(kind="inequality")` | Gini, quantile ratios, Gini differences, selected Atkinson measures and top shares with survey intervals. Theil T remains exploratory; some repaired intervals need 7,000+ records. [Income inequality](docs/recipes/pums_tests.md#income-inequality-round-56) |
| How does health disadvantage vary across the area deprivation gradient? | Manifest method `inequality` | SII, RII and concentration indices across ranked areas with population weights. This describes an area gradient, a different quantity from PUMS income inequality. [Health inequality](docs/recipes/health_inequality.md) |
| How do rates differ between population groups (race/ethnicity, sex) within an area? | `disparity_measures` (full profile) or manifest method `disparity` | Rate difference and ratio against a reference group declared in advance, Index of Disparity, between-group variance, Theil and MLD, reported together (Round 76). Groups must be mutually exclusive. Validated ranges depend on the largest group-rate CV; count-based index measures are exploratory. `kitagawa` splits a crude-rate gap between two areas into rate and composition effects. [Between groups](docs/recipes/health_inequality.md#between-population-groups-round-76) |
| Is mortality high relative to a reference population? | Manifest method `smr` | Observed deaths versus expected deaths from age/sex reference rates, with period scaling and combined uncertainty. Reference counts and estimated reference populations have explicit options. [SMRs](docs/recipes/health_inequality.md) |
| How separated are population groups within counties? | Manifest method `segregation` | Dissimilarity, isolation and Theil H (two to six groups) from mutually exclusive tract counts and all 80 replicates. Use the bias-corrected versions (the default); each county is validated or not according to its noise level, and contrasts between releases have their own gates. Counties with negative replicate counts can use `args.negative_replicates: "clip"`; `args.group_quarters` can drop prison and dormitory tracts (a definitional choice to declare). [Segregation](docs/recipes/segregation.md) |
| How accurate is designating areas by a threshold (e.g. poverty at least 20%)? | `designation_accuracy` (full profile) | Each area's probability of truly exceeding the threshold (validated) and the expected sensitivity, specificity, PPV and NPV of four designation rules (exploratory) (Round 85). [Designating areas](docs/recipes/small_area.md#designating-areas-round-85) |
| Can information be shared across noisy small areas? | `small_area_estimates`, `spatial_small_area_estimates`, `multilevel_model` | Fay–Herriot for direct estimates with known sampling SEs (`transform="arcsine"` for proportions near 0 or 1, `temporal=True` across non-overlapping releases, Round 80); spatial Fay–Herriot for neighboring areas; mixed models for nested observations such as tracts within counties, and three levels such as tracts in counties in states (`groups=["state", "county"]`). [Small-area recipe](docs/recipes/small_area.md) |
| Do I need areas the Census does not publish? | `custom_area_mapping` → `aggregate_geographies`; `median_from_distribution` | Sum counts with combined MOEs, then derive rates; never average rates or medians. [Custom geographies](docs/recipes/custom_geographies.md) |
| Are dollar amounts comparable across years or places? | `adjust_inflation`, `adjust_for_place`, `place_adjust_frame` | R-CPI-U-RS for years; BEA Regional Price Parities for places (their error is not in ACS MOEs). [Dollars](docs/recipes/dollars.md) |
| How do life tables, YPLL or age-data quality behave? | `demography_analysis` (full profile) | Abridged life tables with Chiang II intervals (`kind="life_table"`, validated), Arriaga age/cause decomposition (`"arriaga"`), Whipple/Myers/UN age-quality indices (`"age_quality"`), census-survival migration (`"survival_migration"`), and age-adjusted YPLL-65/75 with Fay–Feuer intervals (`"ypll"`, validated; suppression bounds for 1–9 counts) (Rounds 95, 101, 103). [External health outcomes](docs/recipes/external_health_outcome.md) |
| Does a relationship vary over space, or which tracts are alike? | `spatial_model` (full profile) | BYM2 disease mapping (`kind="disease_map"`, exceedance probabilities calibrated, RR intervals exploratory; Round 96), spatial-block CV and MAUP (`"cv"`, `"maup"`, Round 97), GWR (`"gwr"`), k-means types, SKATER regions with stability, and entropy diversity (`"diversity"`, Round 93). [Spatial patterns](docs/recipes/spatial_patterns.md) |
| Is there a cluster of counties with high event counts? | `spatial_scan` (full profile) | Kulldorff Poisson scan of county counts with Monte Carlo p-values (Round 81; validated size with 50% windows). Denominators must be exact; descriptive unless the window was pre-specified. [Spatial scan](docs/recipes/spatial_patterns.md#clusters-of-high-counts-spatial-scan-round-81) |
| Where does a variable cluster? | `spatial_autocorrelation` (`local=True` for LISA), `make_map` | Moran's I with a conservative replicate SE; local clusters are descriptive under sampling error. [Spatial patterns](docs/recipes/spatial_patterns.md) |
| Does a variable mean the same thing in every release? | `check_variable_concordance`, crosswalk draft/review tools | Split when unsure; merges need a census.gov source and an independent reviewer. [Cross-release](docs/recipes/cross_release.md) |

### Choosing uncertainty and spatial inference

For replicate-based area models, `target="population"` uses model SEs for the general relationship; `"these_areas"` uses ACS replicate SEs for these areas in this period; `"conservative"` combines both. Corrected and spatial procedures have their own interval basis. Report the result's `interval_se_column`, interval target and uncertainty notes rather than selecting a convenient SE column.

- **Counts:** use NB2 (`fit_model(model="negbin", exposure=...)`) when counts are overdispersed. Poisson HC3 under-covered under strong overdispersion; Pearson `scale="X2"` is not a validated substitute. Binomial proportions need their trial counts. Beta regression is available for shares in (0,1), and median regression for skewed outcomes.
- **Spatially dependent areas, naive slopes:** SCPC (Müller and Watson 2022) gives validated intervals and p-values for OLS, Poisson and binomial slopes on both tested geographies (MI/NY and OH/PA). It is the recommended spatial interval outside MI/NY and for OLS anywhere. At **tract** level (Round 71, NC and MI tracts) OLS slopes are validated with `rho_bar` .20 (the tract default) or .30; tract Poisson/binomial SCPC is exploratory, and the spatial error model under-covers on tracts. `fit_model` warns when residuals are spatially dependent and names the validated route.
- **Spatially dependent areas, corrected slopes:** G1 (`spatial="clusters"`, pooled correction with eight clusters) and G2 (`spatial="error"`, spatial-error whitening) target the error-corrected linear slope. Both are validated with up to five error-prone covariates. With more, a fit is validated only when every covariate's estimated reliability (reported as `reliability`) is at least .8: up to eight covariates for G1 and seven for G2. Calibrated Poisson, NB2 and binomial slopes with `spatial="clusters"` have their own validation. Use the [regression recipe](docs/recipes/regression_sampling_error.md) and the result's notes.
- **IM-8 is not a universal spatial fix:** naive IM-8 slopes passed on MI/NY but under-covered on OH/PA with spatially correlated fields, and dropped to .858 in a 10,000-draw MI/NY rerun of the low-reliability OLS cell; use SCPC instead. The failed per-cluster EIV candidate is distinct from the later pooled-correction G1 method. Conley HAC, CR1 and WCR failed validation. Do not change cluster counts or discard ACS uncertainty to obtain significance.
- **Read scope, not just availability:** validation depends on sample size, reliability, spatial geometry, group definitions and the estimand. Inspect `validated` where provided, warnings and deviations, then consult [STATUS.md](STATUS.md) and the linked audit. SIMEX, Theil T, CCC intervals and some model/test combinations remain exploratory. Defaults and a wide interval do not certify an unsupported design.

### A reproducible research workflow

1. Define the population, observation unit, release windows, geographic vintage and outcome before choosing a method. Call `get_recipe()` and inspect the relevant measure's universe with `describe_variable`.
2. Use `plan_extraction`, inspect `would_block`, concordance issues and advisories, then download. Build an analysis frame, check replicate availability and reliability, and handle missing/suppressed values explicitly.
3. For confirmatory work, write a manifest, call `create_manifest` to validate/hash it, and **commit it before examining outcome associations**. Run the completed, registered file with `run_manifest`. A hash alone is not pre-registration.
4. Check the run status and deviations: an incomplete run is not a confirmatory result. Registered methods need explicit choices; the validator does not automatically upgrade a legacy interval to a later validated one. For example, manifest correlations use `args.interval: "validated"` to opt in.
5. For long runs, pass `checkpoint=true` to `run_manifest` with a fixed `output_dir`: a rerun after a crash reuses the finished analyses (same manifest and data only), and results are identical.
6. Save tables, figures, methods and provenance with the manifest hash. `run_manifest` writes its bundle; `make_results_bundle` packages exploratory work. `run_variant` is an explicitly exploratory refit of cached inputs, leaving the registered analysis unchanged.

Start with the [pre-registration recipe](docs/recipes/preregistered.md), the [executable offline example](docs/reference_workflow.md), or the [worked real-data workflow](docs/case_study_mi_ny.md). The [study reports](docs/studies/) distinguish registered analyses, post hoc checks and exploratory demonstrations; [validation audits](docs/audits/) report both passing and failed methods.

## Geography, maps, and spatial analysis

Built on GeoPandas, Shapely (GEOS), pyogrio (GDAL), pyproj, and PySAL. Outputs are GeoPackage by default, which ArcGIS Pro and QGIS open natively.

| Capability | Function / tool | Notes |
| :--- | :--- | :--- |
| Census boundaries matched to each ACS release | `census.boundaries.get_boundaries` / `get_boundaries` | Cartographic (1:500k) for maps, TIGER/Line for areal work; vintage mismatches are errors |
| Journal maps that show uncertainty | `census.maps.choropleth` / `make_map` | Quantile classes by default; legend reports class separability (Sun and Wong 2010); low-reliability areas hatched; uncertainty and significance maps |
| Spatial autocorrelation | `census.spatial.morans_i`, `local_morans` / `spatial_autocorrelation` | Reproduces PySAL references; replicate SE of Moran's I is conservative (coverage 0.987); local clusters use two-sided permutation p-values (9999 permutations, BH): false-positive rates at nominal under randomness |
| Spatial regression | `census.spatial.spatial_regression` / `spatial_regression` | Lag (GMM default) and error (ML default) models with LM diagnostics (spreg); simulated coverage under ACS outcome error: rho 0.89-0.90 (GMM lag), lambda attenuated (0.003-0.85). Error model option `correct_outcome_error=True, se_col=...` corrects lambda for the outcome's sampling error (spatial Fay-Herriot likelihood, REML): lambda coverage 0.86-0.93. It assumes independent errors across areas, which ACS replicates support for rates, shares and medians ([covariance audit](docs/audits/acs_sampling_covariance.md)); it warns for population/household totals and is biased by positively correlated errors ([validation](docs/audits/spatial_regression_validation.md)) |
| Spatial Fay–Herriot | `census.sae_spatial.spatial_fay_herriot` / `spatial_small_area_estimates` | Reproduces the R `sae` grapes example; coverage 0.891 |
| Population-weighted tract crosswalks | `census.block_weights`, `harmonize_panel(weight="auto")` | Decennial block weights; Delaware test: mean error 444 vs 624 people with land-area weights |
| Block groups and custom polygons | `geo_level="block group"`, `census.custom_areas` / `custom_area_mapping` | Area or block-population allocation |
| ACS errata and user notes | `census.errata.errata_for`; in every extraction plan | 258 notes from census.gov with sources |

## Microdata, 1-year estimates, and research designs

PUMS supports custom person/household universes with the appropriate survey weights. Its smallest geography is the PUMA; use published area tables for county or tract estimates. Heaped dollar values can make median and quantile-ratio uncertainty unreliable, so inspect the returned flags.

| Capability | Function / tool | Validation |
| :--- | :--- | :--- |
| PUMS custom tabulations (count, mean, proportion, median, ratio, crosstabs) | `census.pums.tabulate` / `pums_tabulate` | Reproduces all 32 Census PUMS verification estimates and SEs (Wyoming, 2024 1-year and 2020–2024 5-year) |
| PUMS regression with replicate weights | `census.pums.pums_regression`, `census.pums_models.fit_pums_model` / `pums_regression` | Ordered logit/probit, multinomial logit, weighted median and probit have dedicated replicate-weight validation; avoid design-blind model SEs |
| ACS 1-year estimates | `product="1-year"` in `plan_extraction`, `batch_download`, `run_batch` | Areas of 65,000+ only (others reported); 2020 skipped (no standard release); 1-year vs 5-year comparisons refused |
| Multilevel models | `census.multilevel.fit_multilevel` / `multilevel_model` | Kenward–Roger intervals; coverage 0.89; reproduces the statsmodels `dietox` reference. Three levels (`groups=["state", "county"]`, Round 73): fixed-effect intervals validated (.904–.913); variance-share intervals exploratory |
| Published-loading indices | `build_index(method="loadings", loadings={...})` | A paper's fixed factor loadings; per-area intervals validated (Round 73, mean .897–.899) |
| Difference-in-differences | `census.did.difference_in_differences` | Non-overlapping periods only; coverage 0.90–0.91; reproduces Card and Krueger (1994) |
| Cost of living between places | `census.rpp.adjust_for_place` / `adjust_for_place` | BEA Regional Price Parities; reproduces BEA real personal income for all states (2008); never applied by default |
| Interactive maps | `census.web_maps.web_choropleth` / `make_web_map` | Self-contained HTML, no external requests |

### Methods accessed through manifests or Python

`smr`, `inequality` and `segregation` are **manifest method names**, not standalone MCP tools: execute them through `create_manifest` / `run_manifest`.

Since Round 75, manifests also have:
- **method `multilevel`**, with two levels (`"groups": "county_fips"`) or three (`["state_fips", "county_fips"]`);
- an **`"indices"` block**, an index built from ACS indicators with weights fixed in every replicate (`"loadings"`, `"pca"` or `"equal"`);
- **person-years expected counts** (`expected_count` with `"person_years"`).

See the [pre-registration recipe](docs/recipes/preregistered.md). They also have Python entry points in `census.standardize`, `census.inequality` and `census.segregation`.

Descriptive Poisson–Gamma event-rate smoothing is Python-only (`census.rate_smoothing.eb_poisson_gamma`); it serves a different purpose from Fay–Herriot smoothing of ACS estimates. Interval-censored NB2 for counts suppressed as 1–9 is `fit_model(model="negbin", exposure=..., censored="<true/false column>")` (validated; hidden counts are never estimated). The `interrupted_series` tool (full profile) estimates level and slope changes in an annual series with AR(1) errors and a linear trend on each side: `method="bootstrap_t_cons"` (the default) is validated from 17 points, `"bootstrap_t_bb"` from 19, `"bootstrap_t_bc"` from 20 and `"bootstrap_t"` from 30; every method failed at 15 points, so shorter series are exploratory. It refuses non-consecutive years: overlapping ACS five-year releases are not annual observations (use `trend_test`). The [method status table](STATUS.md#methods-validation-status) and recipes give the gates and alternatives. [docs/agent_routing.md](docs/agent_routing.md) lists common research questions with the tool, profile and validation flag the engine returns for each; a test runs every row.

## Replications

The engine reproduces five published findings (Rounds 66–69, each registered before its comparison):

| Finding | Outcome |
| :--- | :--- |
| A. County Health Rankings 2025 county Black/White dissimilarity | Replicated exactly (2,055 counties) |
| B. Census state Gini (B19083), from PUMS | Replicated (median difference .0008; 10 of 12 intervals contain it) |
| C. Mitchell et al. 2022, NC tract life expectancy and ICE | Partly replicated (5 of 6 slopes) |
| D. Monnat 2018, county drug-related mortality and economic distress | Replicated (9.95 vs 9.62) |
| E. Boing et al. 2020, tract/county/state shares of life-expectancy variation | Replicated (70.0/10.6/19.4 vs 70.4/10.7/19.0%) |

Each is a spec in `docs/replications/` (published target, pre-set rule, original result, engine route and rerun
tolerance). `scripts/run_replications.py` reruns them through the engine's own routes and checks each against its
original audit; `get_recipe("replications")` explains how. The Round 74 rerun agrees with every original audit
(`docs/audits/replication_suite.md`). D needs the owner's manual CDC WONDER exports, so without them it is skipped.

## Context covariates

County characteristics the ACS does not measure can be joined as **covariates** (Round 72): County Business
Patterns establishment counts by NAICS, ERS 2015 county economic types, ERS rural–urban continuum codes and 2013
metro status, and County Health Rankings additional measures from CHR's calculation repository (pinned commit).
List them with `list_health_sources(kind="context")`. Add them with `build_analysis_frame(context=[...])` or a
manifest `"context"` block. Tract frames get their county's value. Every file is cached with its SHA-256. These are
never outcomes; see the [context recipe](docs/recipes/context_covariates.md).

## External health data

Health outcomes the ACS lacks come from registered external sources (`list_health_sources`, recipe `external_health_outcome`, `docs/agent_protocol.md` section 16), joined to a manifest's ACS frame as outcomes only:

| Source | Level | Kind | Notes |
| :--- | :--- | :--- | :--- |
| CDC PLACES 2025 | tract, county | model-based (BRFSS MRP) | No key; within a county varies only with age, sex, race/ethnicity and education composition |
| USALEEP | tract (2010) | partly model-based | Life expectancy 2010-2015; fully predicted tracts dropped; `apportion_to: 2020` (split tracts left missing) |
| County Health Rankings & Roadmaps 2025 | county | direct (mortality) or PLACES-based | Non-commercial research use; ACS-derived columns refused |
| CDC WONDER exports | county, state; national age/sex references | direct | Manual files pinned by SHA-256; suppressed counts remain censored |

**Circularity rule (enforced by `create_manifest`):** determinant studies keep using the ACS's own measure as the outcome (for disability: B18101), and use external sources for measures the ACS lacks, such as diabetes. Model-input overlap is checked; any permitted exception needs the manifest's explicit circularity justification.

- **Count outcomes:** binomial models use trial counts and validated inference; ordinary external-count models require HC3 or an eligible spatial procedure. For overdispersed death counts, NB2 is preferable to Poisson. New external-count manifests refuse Pearson `scale="X2"`.
- **WONDER is manual-only:** the engine never contacts WONDER, including for national references. Follow the [export guide](docs/data/wonder_exports.md). Suppressed counts remain unavailable, with interval-censoring where supported; never publish county counts of 1–9 or derived county values, raw exports or totals that reveal hidden counts by subtraction.
- **Model provenance matters:** PLACES associations with its own model inputs can be circular. Source agreement studies and determinant studies answer different questions; use [the external-outcome recipe](docs/recipes/external_health_outcome.md).

## 2020 Decennial Census

The 2020 Census P.L. 94-171 redistricting data (`dec/pl`) and the Demographic and Housing Characteristics File (`dec/dhc`) use the same client, cache, extraction pipeline, output formats, codebook and replay as the ACS: pass `dataset="dec/dhc"` (or `"dec/pl"`), or `product="decennial"`, to `plan_extraction`, `batch_download`, `download_table`, `run_batch` or `python -m census extract --product decennial`, with `years=[2020]`. Geography levels are nation, state, county, tract, block group, place and block (block only for P.L. 94-171 and the invariant DHC `H1` housing-unit count). Variable metadata for both files is archived in `metadata/dec/`.

```python
from census import ResearchOptions, build_entities, run_batch

run_batch("P12", build_entities("county", "26"), [2020], "out", "panel",
          ResearchOptions(include_codebook=True), dataset="dec/dhc")
```

**Uncertainty.** Census counts are not sample-based, so they have no sampling margin of error; they are also not error-free. Outputs never carry an MOE or CV of 0: no MOE, SE, CV or reliability columns are written (`compute_reliability` adds none), the codebook's `Uncertainty` column reads "not sample-based (MOE undefined)", and the extraction metadata has `moe_confidence_level: null` and an `uncertainty` record. Every decennial plan carries a disclosure-avoidance advisory:

- the counts carry coverage error (measured by the [Post-Enumeration Survey](https://www.census.gov/newsroom/blogs/random-samplings/2021/12/post-enumeration-measuring-coverage-error.html)), processing error, and noise added by the TopDown differential-privacy algorithm;
- only three counts are invariant (published without noise): state total population, total housing units per block, and the number of occupied group-quarters facilities by type per block ([Census DAS update, 2020-11-25](https://www.census.gov/programs-surveys/decennial-census/decade/2020/planning-management/process/disclosure-avoidance/2020-das-updates/2020-11-25.html));
- small geographies and detailed cells are noisier, and block-level characteristics should be aggregated before use ([fact sheet](https://www.census.gov/content/dam/Census/library/factsheets/2021/protecting-the-confidentiality-of-the-2020-census-redistricting-data.pdf)).

**Statistics.** `z_test`, `calculate_significance`, `batch_significance`, `calculate_cv` and `acs_overlap_years` refuse decennial-only inputs (`product="decennial"`), since a sampling test says nothing about disclosure-avoidance noise. An ACS estimate can be tested against a census count with `product1="5-year", product2="decennial"`: the count is a fixed reference, and the result's `comparison` and `notes` say that only ACS sampling error is measured. `derive_estimate(..., product="decennial")` returns the point estimate with MOE, SE and CV undefined. `build_analysis_frame` gives census counts NaN `_se`/`_cv`, method `not_sample_based`, release `dec_2020` (`acs5_<year>+dec_2020` with a note when mixed with ACS variables). No new estimators are provided for decennial data; validation check F11 compares the files with the Census Bureau's invariants and hierarchy.

## Advisories and known limitations

- **Boundary vintages.** Requests spanning 2019 to 2020 at tract, ZCTA, place, county, or CBSA level produce an advisory. Tract panels can be harmonized with `harmonize_tracts_to=2010|2020` (land-area weights from the Census relationship file, or NHGIS-style population weights you supply); apportioned MOEs assume independent components and exact weights, and boundary slivers produce tiny weights. Other levels are not harmonized.
- **Tract IDs changed in 2020.** Give tract frames a `Year` column so the matching boundary vintage is used. Without one, representative points try 2020 tracts, then 2010 tracts, and say which they used.
- **Medians from coarse brackets.** Household-income medians rebuilt from B19001 are usually within 1% of the published B19013, but can differ by more than 2% because Census interpolates a finer internal distribution.
- **Home values.** Before the 2022 releases, home values were not on the period end-year dollar basis (ACS user note 2023-07), so deflating them is approximate. Plans include an advisory.
- **Subject tables.** Their 2013 and 2017 redesigns changed thousands of labels. Multi-year subject pulls usually need `variables=` and reviewed overrides.
- **2020 Census counts.** No margins of error exist; disclosure-avoidance noise dominates blocks and detailed cells. Aggregate before use; see [2020 Decennial Census](#2020-decennial-census). Cross-release concordance and continuity checks do not apply (one census year), and the 2010 Census is not offered.
- **ZIP codes vs. ZCTAs.** `zip2fips.json` maps each ZIP to one primary county; PO-box-only ZIPs have no ZCTA.

## Repository layout

```
census/
  api.py           Census API client, geography predicates, dataset inference
  cache.py         SQLite response cache
  metadata.py      Per-vintage variable and table metadata (archive, then API)
  concordance.py   Label normalization, concordance, issues, override validation
  continuity.py    National-level continuity check
  review.py        Draft and record reviewed overrides
  pipeline.py      plan_extraction, run_batch, build_entities, ResearchOptions
  inflation.py     Price indexes, deflator, advisories
  stats.py         MOE, SE, CV, Z-tests, aggregation, sentinel cleaning
  variance.py      DerivedEstimate and replicate-variance primitives
  derived.py       Proportions, ratios, products, sums, percent change (Handbook ch. 8)
  replicate.py     Census Variance Replicate Estimate tables: download, parse, exact variances
  medians.py       Medians and MOEs from distribution tables
  aggregate.py     Custom geography aggregation
  multitest.py     Multiple-comparison corrections, batch significance tests
  geo_crosswalk.py 2010/2020 tract apportionment, Connecticut recodes
  validation.py    Checks against Census-published values
  manifest/        Registered analyses, validation gates, execution and methods text
  models.py        Replicate regression, EIV and regression calibration
  spatial_eiv.py, scpc.py, count_models.py   Spatial/corrected slopes and counts
  pums.py, pums_models.py, pums_inference.py, pums_inequality.py   Survey microdata
  inequality.py, standardize.py, segregation.py   Area gradients, SMRs, segregation
  workflows*.py    File-level workflows shared by the MCP server and CLI
  panel.py         Slugs, codebooks, tidy panels, Parquet
  geo.py, tables.py, export.py, errors.py, __main__.py (CLI)
mcp_server.py      MCP server (instructions + 81 tools)
acs_downloader.py  Tkinter GUI (maintenance mode)
metadata/          Per-vintage ACS metadata archive with manifest
crosswalks/        Reviewed concordance overrides and their evidence
data/price_indexes/  R-CPI-U-RS, CPI-U, and C-CPI-U with source sidecars
data/geo_crosswalks/ Census 2010/2020 tract relationships and Connecticut recodes
scripts/           fetch_metadata_archive.py, update_price_indexes.py, audit_concordance.py,
                   fetch_tract_relationships.py, validate_against_census.py
docs/              Setup, agent protocol, task recipes, validation audits and study reports
STATUS.md          Current capabilities, validated ranges, release and remaining limitations
tests/             unittest suite (pytest); tests/test_live.py is opt-in
```

## Testing

```bash
python -m pytest -q                                          # offline, including validation fixtures
CENSUS_LIVE_TESTS=1 python -m pytest -q                      # adds live API and validation tests
python scripts/validate_against_census.py --live             # full live validation report
python -m census validate-crosswalks
```

## Citation and attribution

Created and maintained by [cafeTechne](https://github.com/cafeTechne). If you use this toolkit in research, cite it using [CITATION.cff](CITATION.cff) (GitHub's "Cite this repository" button produces APA and BibTeX) or the concept DOI [10.5281/zenodo.23925301](https://doi.org/10.5281/zenodo.23925301), which always resolves to the latest release (each release also has its own version DOI on Zenodo), and cite the Census Bureau as the source of the data, naming the ACS 5-year release(s) and table(s) used. Forks and derivative works must keep this attribution and the license notice.

### Citing methods

Successful method-tool results carry `method_sources`, which lists the papers that define the method, the textbooks
whose guidance shaped it, the data it reads and the engine audit that validated it. Results bundles write these
sources to `references.md` and `references.bib`. `python -m census cite --tool NAME` prints them for one tool. See
[docs/citing.md](docs/citing.md).

## License

Copyright (C) 2023–2026 cafeTechne.

Licensed under the GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE). Contributions require the [Contributor License Agreement](CLA.md); see [CONTRIBUTING.md](CONTRIBUTING.md).

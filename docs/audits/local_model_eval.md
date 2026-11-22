# Local-model evaluation (PLAN_ROUND_8 J4, Round 10 F1)

- Generated: 2026-11-22 00:38
- Models: `gemma4-e4b-8k`, `qwen3.5-9b-8k` via `http://localhost:11434/v1` (temperature 0, Qwen `/no_think`)
- MCP server: `python mcp_server.py --profile <profile>`: `core` (16 tools), `core_spatial` (17 tools), `full` (71 tools)
- Hardware: x86_64, 16 logical CPUs, 16 logical CPUs, 123 GB RAM, CPU only (no GPU), Ollama 0.40.15, num_ctx 8192 via model copies
- Result: `gemma4-e4b-8k` **8/12**; `qwen3.5-9b-8k` **7/12** (pass = right tool, right arguments, and a final answer containing the expected result)

Tasks need no Census API calls or network; expected answers come from calling the library directly. Map and spatial tasks use the offline DC tract boundary fixture.

Cells read PASS/FAIL then tool/args/answer correctness.

| Task | Profile | Expected | gemma4-e4b-8k | gemma4-e4b-8k (s) | qwen3.5-9b-8k | qwen3.5-9b-8k (s) |
| :--- | :--- | :--- | :--- | ---: | :--- | ---: |
| poverty_rate_with_moe | core | 15.0% +/- 1.09 | **PASS** yes/yes/yes | 55.1 | **PASS** yes/yes/yes | 89.8 |
| two_county_significance | core | yes, difference 2.3, p=0.011 | **PASS** yes/yes/yes | 36.0 | **PASS** yes/yes/yes | 69.1 |
| trend_three_releases | core | slope -0.231/yr, significant | **PASS** yes/yes/yes | 37.3 | **PASS** yes/yes/yes | 71.5 |
| overlapping_trend_refused | core | refused: releases overlap; use non-overlapping releases | **PASS** yes/yes/yes | 62.4 | **PASS** yes/yes/yes | 168.8 |
| minimum_detectable_difference | core | 4.82 points | **PASS** yes/yes/yes | 33.1 | **PASS** yes/yes/yes | 85.3 |
| recipe_tract_trend | core | tract_trend recipe (non-overlapping releases, trend_test) | **PASS** yes/yes/yes | 78.1 | **PASS** yes/yes/yes | 192.1 |
| recipe_custom_geographies | core | custom_geographies recipe (aggregate_geographies: sum counts, then derive the rate) | FAIL no/no/no | 72.4 | FAIL yes/no/yes | 192.4 |
| recipe_dollars | core | dollars recipe (adjust_inflation, adjust_for_place / place_adjust_frame) | FAIL no/no/no | 91.8 | FAIL no/no/no | 126.7 |
| map_with_reliability | core | map written; class separability 1% | **PASS** yes/yes/yes | 70.2 | **PASS** yes/yes/yes | 103.1 |
| spatial_clustering | core_spatial | Moran's I 0.558, significant (p_sim=0.001) | **PASS** yes/yes/yes | 39.2 | FAIL yes/yes/no | 80.9 |
| annual_series_break | full | level change 1.55, validated | FAIL no/no/no | 52.2 | FAIL no/no/no | 129.8 |
| short_series_exploratory | full | exploratory: 15 points; validated methods need 17+ | FAIL no/no/no | 65.9 | FAIL no/no/no | 163.5 |

## Transcripts

### gemma4-e4b-8k: poverty_rate_with_moe

- call `derive_estimate` `{"as_percent": true, "estimates": [12000, 80000], "moes": [900, 1500], "operation": "proportion"}`
- final answer: The poverty rate is **15.0%** with a 90% margin of error of **1.089%**.

### gemma4-e4b-8k: two_county_significance

- call `calculate_significance` `{"confidence_level": 0.9, "est1": 14.2, "est2": 11.9, "moe1": 1.1, "moe2": 1}`
- final answer: Yes, the difference is statistically significant at the 90% confidence level.  The difference between the two rates is **2.3%**, with a p-value of **0.0109**.

### gemma4-e4b-8k: trend_three_releases

- call `trend_test` `{"estimates": [14.1, 13, 11.8], "moes": [0.4, 0.4, 0.3], "years": [2013, 2018, 2023]}`
- final answer: Yes, there is a significant linear trend.  The trend slope is **-0.231** per year (90% CI: -0.280 to -0.181).

### gemma4-e4b-8k: overlapping_trend_refused

- call `trend_test` `{"estimates": [14.1, 13, 11.8], "moes": [0.4, 0.4, 0.3], "years": [2021, 2022, 2023]}`
- final answer: The trend test failed because the 5-year releases for 2021, 2022, and 2023 overlap, which overstates the precision of the trend. For a valid trend test, you must use releases that are at least 5 years apart (e.g., 2013, 2018, 2023).

### gemma4-e4b-8k: minimum_detectable_difference

- call `minimum_detectable_difference` `{"moe1": 2.1, "moe2": 2.4, "power": 0.8}`
- final answer: The smallest difference between the two tract estimates that you could reliably detect (with 80% power) is **4.82 percentage points**.

### gemma4-e4b-8k: recipe_tract_trend

- call `get_recipe` `{"name": "tract_trend"}`
- final answer: The workflow to test whether a tract's poverty rate changed over the last decade involves using the `tract_trend` recipe.  Here are the steps:  1.  **Select Non-Overlapping Releases:** Choose 5-year releases that are at least 5 years apart (e.g., 2013, 2018, 2023). 2.  **Download Data:** Use `download_table` to retrieve the poverty data for the specific tract(s) and chosen years. Ensure you harmonize tracts if necessary (e.g., if using 2020 tracts). 3.  **Compute Rate and MOE:** For each chosen release, use `derive_estimate` to calculate the poverty rate (proportion) and its 90% Margin of Erro

### gemma4-e4b-8k: recipe_custom_geographies

- final answer: The workflow involves finding the correct data, extracting it for your specific tracts, and then preparing it to calculate the estimate and its margin of error.  Here is the step-by-step workflow:  1.  **Search for the Variable:** Use `search_tables` to find the specific ACS table code and variable code for the poverty rate. 2.  **Identify Tract Codes:** Ensure you have the 3-digit FIPS codes for the three census tracts. 3.  **Plan Extraction:** Use `plan_extraction` to confirm that the data for the specified tracts and variable is available. 4.  **Download Data:** Use `download_table` to down

### gemma4-e4b-8k: recipe_dollars

- final answer: To address this complex comparison, you will need a sequence of tools. Since you are comparing income across different groups (metro areas) and controlling for a variable (cost of living), a regression approach is the most appropriate method.  Here is the list of tools and the conceptual steps:  1.  **`search_tables`**: Use this first to find the specific ACS table code for "median household income" and any related variables, such as cost of living or metro area definitions. 2.  **`download_table`**: Download the necessary data for the two years (2013 and 2023) and the relevant geographic unit

### gemma4-e4b-8k: map_with_reliability

- call `make_map` `{"column": "poverty_rate", "input_path": "/tmp/census-eval76/.cache/local_model_eval/dc_tracts_2023.csv", "kind": "estimate", "level": "tract", "se_col": "poverty_rate_se", "year": 2023}`
- final answer: The map of `poverty_rate` for Washington DC census tracts has been generated.  **Class Separability:** 1% (share of adjacent-class area pairs whose 90% confidence intervals do not overlap, Sun and Wong 2010).  The map files are available in `/tmp/census-eval76/downloads/maps/`.

### gemma4-e4b-8k: spatial_clustering

- call `spatial_autocorrelation` `{"column": "poverty_rate", "input_path": "/tmp/census-eval76/.cache/local_model_eval/dc_tracts_2023.csv", "level": "tract", "year": 2023}`
- final answer: Moran's I for poverty_rate across Washington DC census tracts is **0.5581**.  This value is statistically significant (p-value $\approx 0.001$), indicating that poverty_rate is spatially clustered.

### gemma4-e4b-8k: annual_series_break

- final answer: I do not have a tool capable of performing a time-series analysis or a difference-in-differences calculation on a provided list of numbers to estimate a level change with a confidence interval. The available tools are designed for spatial statistics, ACS PUMS microdata analysis, and area-level data processing.

### gemma4-e4b-8k: short_series_exploratory

- final answer: I do not have a tool that can perform a time series analysis or a change-point detection on a list of raw numbers like the one you provided. The available tools are designed for spatial statistics, survey data analysis (ACS PUMS), and specific econometric models that require structured input files (like Parquet or CSV) containing area-level data and standard errors.  To answer your question, you would need to perform a time series regression or a change-point analysis on this data.  If you can provide this data in a structured format (e.g., a CSV or Parquet file) and specify the standard error

### qwen3.5-9b-8k: poverty_rate_with_moe

- call `derive_estimate` `{"operation": "proportion", "estimates": [12000, 80000], "moes": [900, 1500], "as_percent": true}`
- final answer: The poverty rate in Hays County is **15.0%** with a 90% margin of error of **1.09%**.

### qwen3.5-9b-8k: two_county_significance

- call `calculate_significance` `{"est1": 14.2, "moe1": 1.1, "est2": 11.9, "moe2": 1, "confidence_level": 0.9}`
- final answer: Yes, the difference in poverty rates between County A (14.2%) and County B (11.9%) is statistically significant at the 90% confidence level. The difference of 2.3 percentage points has a p-value of 0.0109, which is below the typical significance threshold for 90% confidence (p < 0.10).

### qwen3.5-9b-8k: trend_three_releases

- call `trend_test` `{"years": [2013, 2018, 2023], "estimates": [14.1, 13, 11.8], "moes": [0.4, 0.4, 0.3]}`
- final answer: Yes, there is a **significant linear trend** in the poverty rate across these three ACS releases (p < 0.001).  - **Slope**: **-0.23 percentage points per year** (90% CI: -0.28 to -0.18) - The poverty rate is declining by about 0.23 percentage points each year from 2013 to 2023.

### qwen3.5-9b-8k: overlapping_trend_refused

- call `trend_test` `{"years": [2021, 2022, 2023], "estimates": [14.1, 13, 11.8], "moes": [0.4, 0.4, 0.3]}`
- final answer: The trend test cannot be performed with 2021, 2022, and 2023 ACS 5-year releases because they overlap (share sample years). ACS 5-year releases must be at least 5 years apart to avoid overstatement of precision.  To properly test for a linear trend, you would need non-overlapping releases such as **2013, 2018, and 2023**.   If you have estimates from those non-overlapping releases, I can run the trend test with them. Otherwise, please provide data from releases at least 5 years apart (e.g., 2013, 2018, 2023).

### qwen3.5-9b-8k: minimum_detectable_difference

- call `minimum_detectable_difference` `{"moe1": 2.1, "moe2": 2.4, "power": 0.8}`
- final answer: With 90% margins of error of 2.1 and 2.4 percentage points, the smallest difference you could reliably detect at 80% power is **4.82 percentage points**.

### qwen3.5-9b-8k: recipe_tract_trend

- call `get_recipe` `{"name": "tract_trend"}`
- call `search_tables` `{"query": "poverty rate", "limit": 5}`
- call `search_tables` `{"query": "poverty", "limit": 5}`
- call `search_tables` `{"query": "B17023", "limit": 3}`
- final answer: Based on the `tract_trend` recipe, here's the workflow to test whether a tract's poverty rate changed over the last decade:  **Step-by-step workflow:**  1. **Choose non-overlapping 5-year releases**: Use 2013 (2009-2013), 2018 (2014-2018), and 2023 (2019-2023). Overlapping releases are refused by `trend_test`.  2. **Download tract data**: Use `download_table(table_code="B17023", geography="tract:<county>", state_code=..., years=[2013, 2018, 2023], variables=["B17023_001E", "B17023_002E"])`. Note: Tracts changed in 2020; the tool apportions 2010-tract releases to 2020 tracts.  3. **Compute rate

### qwen3.5-9b-8k: recipe_custom_geographies

- call `get_recipe` `{"name": "combine_estimates"}`
- call `get_recipe` `{"name": "custom_geographies"}`
- final answer: To compute poverty rate and margin of error for a neighborhood made of three census tracts, follow this workflow:  **Step 1: Map units to your area** - Use `custom_area_mapping()` with a GeoPackage/GeoJSON defining the neighborhood polygon, specifying `method="population"` (or "housing_units") to weight partial tract overlaps. - Or manually create `{GEOID: area_id}` mapping for the three tracts.  **Step 2: Download ACS tables for each tract** - Use `download_table()` with `geography="tract:GEOID1,GEOID2,GEOID3"`, `table_code="B17001"` (poverty), and desired years. - Include variables like `"B1

### qwen3.5-9b-8k: recipe_dollars

- final answer: For comparing median household income across time (2013 vs 2023) in constant dollars and between metro areas with different costs of living, here are the relevant tools:  **Core Tools:** - `plan_extraction` - Download data with inflation adjustment (`inflation_base_year`, `price_index`) to convert to constant dollars - `download_table` - Retrieve ACS tables for multiple years (2013, 2023) and metro areas - `build_analysis_frame` - Create model-ready files with SE/CV columns from downloaded data  **Analysis Tools:** - `calculate_significance` - Test if income estimates differ significantly betw

### qwen3.5-9b-8k: map_with_reliability

- call `make_map` `{"input_path": "/tmp/census-eval76/.cache/local_model_eval/dc_tracts_2023.csv", "column": "poverty_rate", "level": "tract", "year": 2023, "se_col": "poverty_rate_se"}`
- final answer: The map of poverty_rate for Washington DC census tracts (ACS 2023) has been created.   **Class separability: 1%** - This represents the share of adjacent-class area pairs whose 90% confidence intervals do not overlap, using the Sun and Wong 2010 method.  The map was written to `/tmp/census-eval76/downloads/maps/choropleth.pdf` (and other formats). The caption also notes that 38 of 206 areas have hatching marks indicating coefficient of variation above 30%.

### qwen3.5-9b-8k: spatial_clustering

- call `spatial_autocorrelation` `{"input_path": "/tmp/census-eval76/.cache/local_model_eval/dc_tracts_2023.csv", "column": "poverty_rate", "level": "tract", "year": 2023}`
- error: `Runtime returned an empty final answer`
- final answer: (no final answer)

### qwen3.5-9b-8k: annual_series_break

- final answer: I cannot use the available ACS tools to analyze this time series data. The tools provided are designed for:  1. **ACS PUMS microdata** - tabulation, regression, and association tests on Census survey data 2. **Area-level geographic estimates** - difference-in-differences across non-overlapping ACS release periods (e.g., 2013 vs 2018 vs 2023)  Your data is a time series of overdose death rates (2005-2022), which doesn't match the ACS PUMS or area-level ACS estimate structure. The `difference_in_differences` function requires: - An input file path (not provided) - Outcome variable name from ACS 

### qwen3.5-9b-8k: short_series_exploratory

- final answer: Based on the overdose death rate data provided (2008-2022), there appears to be a level change from approximately 20.8 deaths per 100,000 in the pre-policy period (2008-2013) to approximately 23.8 in the post-policy period (2014-2022).  However, I cannot use the available ACS PUMS tools to analyze this data because: 1. These tools are designed for ACS PUMS microdata analysis, not overdose death rate time series 2. The data provided is aggregate mortality statistics, not survey microdata  For a confirmatory claim about level change, you would need: - **Statistical significance testing** (e.g., 

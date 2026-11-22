# Local-model evaluation (PLAN_ROUND_8 J4, Round 10 F1)

- Generated: 2026-11-22 00:48
- Models: `gemma4-e4b-8k`, `qwen3.5-9b-8k` via `http://localhost:11434/v1` (temperature 0, Qwen `/no_think`)
- MCP server: `python mcp_server.py --profile <profile>`: `core` (16 tools), `core_spatial` (17 tools), `full` (71 tools)
- Hardware: x86_64, 16 logical CPUs, CPU only; num_ctx 8192; after the get_recipe description fix
- Result: `gemma4-e4b-8k` **1/2**; `qwen3.5-9b-8k` **1/2** (pass = right tool, right arguments, and a final answer containing the expected result)

Tasks need no Census API calls or network; expected answers come from calling the library directly. Map and spatial tasks use the offline DC tract boundary fixture.

Cells read PASS/FAIL then tool/args/answer correctness.

| Task | Profile | Expected | gemma4-e4b-8k | gemma4-e4b-8k (s) | qwen3.5-9b-8k | qwen3.5-9b-8k (s) |
| :--- | :--- | :--- | :--- | ---: | :--- | ---: |
| recipe_custom_geographies | core | custom_geographies recipe (aggregate_geographies: sum counts, then derive the rate) | **PASS** yes/yes/yes | 129.1 | **PASS** yes/yes/yes | 129.7 |
| recipe_dollars | core | dollars recipe (adjust_inflation, adjust_for_place / place_adjust_frame) | FAIL no/no/no | 52.9 | FAIL no/no/no | 154.0 |

## Transcripts

### gemma4-e4b-8k: recipe_custom_geographies

- call `get_recipe` `{"name": "custom_geographies"}`
- final answer: Based on the available tools, you should follow the **Custom Geographies** workflow. This process allows you to combine data from multiple tracts into a single custom area (your neighborhood) and calculate the rate with an accurate margin of error.  Here is the step-by-step workflow:  ### Workflow: Custom Geographies  **Goal:** Calculate the poverty rate (a proportion) for a neighborhood defined by three census tracts.  **Step 1: Define the Custom Area (Mapping)** You must first define your neighborhood as a single entity. Since you have the three tract codes, you will manually create a mappin

### gemma4-e4b-8k: recipe_dollars

- final answer: The most appropriate starting point for handling the "constant dollars" and "different costs of living" requirement is the **`dollars`** recipe.  Here is a list of the tools you would use in a sequence:  1.  **`get_recipe(name="dollars")`**: This tool is designed to handle inflation and cost of living adjustments, which is necessary for comparing income across different years and metro areas with varying costs of living. 2.  **`search_tables(query="median household income")`**: Use this to find the specific ACS table code for median household income. 3.  **`plan_extraction(...)`** and **`downl

### qwen3.5-9b-8k: recipe_custom_geographies

- call `get_recipe` `{"name": "custom_geographies"}`
- final answer: For computing poverty rate for a neighborhood made of three census tracts, follow these steps:  1. **Map tracts to your neighborhood area**    - Use `custom_area_mapping("areas.gpkg", "tract", method="population")` if you have polygon files    - Or create a `{GEOID: area_id}` mapping manually for the three tract GEOIDs  2. **Combine counts and derive poverty rate**    - Use `aggregate_geographies(input_path, groups={GEOID: area_id}, variables=[...], derive=[...])`    - This sums counts from the three tracts, combines their MOEs properly, then derives the poverty rate    - Set `use_replicates=T

### qwen3.5-9b-8k: recipe_dollars

- final answer: For comparing median household income from 2013 and 2023 ACS releases in constant dollars between metro areas with different costs of living, here are the relevant tools:  **Core Tools:** - **search_tables** - Find median household income table codes (e.g., B19013) - **describe_variable** - Check variable details and universe for income measures - **download_table** - Download data with `inflation_base_year` and `price_index` parameters for constant dollar adjustment - **derive_estimate** - Compute percent change or ratios between years in constant dollars  **Statistical Comparison:** - **calc

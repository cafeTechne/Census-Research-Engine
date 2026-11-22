# Local-model evaluation (PLAN_ROUND_8 J4, Round 10 F1)

- Generated: 2026-11-22 01:18
- Models: `gemma4-e4b-40k`, `qwen3.5-9b-40k` via `http://localhost:11434/v1` (temperature 0, Qwen `/no_think`)
- MCP server: `python mcp_server.py --profile <profile>`: `core` (16 tools), `core_spatial` (17 tools), `full` (71 tools)
- Hardware: x86_64, 16 logical CPUs, CPU only; num_ctx 40960 (the full profile's 71 tool definitions are ~28,500 tokens)
- Result: `gemma4-e4b-40k` **2/2**; `qwen3.5-9b-40k` **1/2** (pass = right tool, right arguments, and a final answer containing the expected result)

Tasks need no Census API calls or network; expected answers come from calling the library directly. Map and spatial tasks use the offline DC tract boundary fixture.

Cells read PASS/FAIL then tool/args/answer correctness.

| Task | Profile | Expected | gemma4-e4b-40k | gemma4-e4b-40k (s) | qwen3.5-9b-40k | qwen3.5-9b-40k (s) |
| :--- | :--- | :--- | :--- | ---: | :--- | ---: |
| annual_series_break | full | level change 1.55, validated | **PASS** yes/yes/yes | 177.2 | **PASS** yes/yes/yes | 613.5 |
| short_series_exploratory | full | exploratory: 15 points; validated methods need 17+ | **PASS** yes/yes/yes | 172.4 | FAIL yes/no/no | 870.4 |

## Transcripts

### gemma4-e4b-40k: annual_series_break

- call `interrupted_series` `{"interruption_year": 2014, "values": [20.1, 20.4, 19.8, 20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.9, 24.5], "years": [2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]}`
- final answer: The estimated level change in 2014 is **1.55** (with a 90% confidence interval of **1.10 to 1.99**).  The analysis was performed using the `bootstrap_t_cons` method, which assumes AR(1) errors and a linear trend on both sides of the interruption.

### gemma4-e4b-40k: short_series_exploratory

- call `interrupted_series` `{"interruption_year": 2014, "values": [20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.9, 24.5], "years": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]}`
- final answer: Based on the interrupted time series analysis:  **1. Did the level change?** Yes, the analysis suggests a significant level change after the policy started in 2014. *   **Level Change Estimate:** 1.63 *   **90% Confidence Interval:** [1.113 to 2.142]  The analysis also suggests a change in the rate of change (slope change) of 0.1507.  **2. Can the result be used for a confirmatory claim?** **No.** The result is explicitly labeled as **exploratory** and **not validated** for this method and series length. The tool notes that for confirmatory claims, the method requires 17 or more annual points,

### qwen3.5-9b-40k: annual_series_break

- call `interrupted_series` `{"values": [20.1, 20.4, 19.8, 20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.9, 24.5], "years": [2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022], "interruption_year": 2014, "method": "bootstrap_t_cons"}`
- final answer: Based on the interrupted time series analysis:  **Level change in 2014:** - **Estimate:** 1.55 per 100,000 - **90% interval:** [1.10, 1.99]  The analysis also found a slope change of 0.109 per year (90% CI: 0.030 to 0.189). The result is validated using the bootstrap_t_cons method for an 18-point annual series, assuming AR(1) errors and linear trends on each side of the policy interruption in 2014.

### qwen3.5-9b-40k: short_series_exploratory

- call `interrupted_series` `{"values": [20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.5], "years": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022], "interruption_year": 2014}`
- call `interrupted_series` `{"values": [20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.5], "years": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022], "interruption_year": 2014}`
- call `interrupted_series` `{"values": [20.6, 20.9, 20.3, 21, 21.2, 20.8, 23, 23.3, 22.9, 23.8, 24, 23.6, 24.4, 24.5], "years": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021], "interruption_year": 2014}`
- error: `Runtime returned an empty final answer`
- final answer: (no final answer)

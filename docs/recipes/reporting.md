# Reporting: tables, maps, codebooks and results bundles

Profile: `make_map` and `make_figure` are in core; `make_table`, `generate_codebook` and `make_results_bundle` are full only.

Goal: turn results into publication outputs with their provenance.

1. **Tables:** `make_table(kind="descriptive", input_path=<frame>, variables=[...])` writes LaTeX (booktabs),
   Markdown and CSV. `kind="comparison"` takes a `batch_significance` output.
2. **Maps:** `make_map(...)` writes PDF, SVG, EPS and PNG, with a values CSV, caption and provenance. See recipe
   `spatial_patterns`.
3. **Codebooks:** `generate_codebook(table_code, year)` gives each variable's code, label, concept, universe and
   unit. For panels, use `batch_download(include_codebook=True)`.
4. **Exploratory bundle:**
   - save each tool result with `python -m census tool ... --save PATH`;
   - then call `make_results_bundle(output_dir, results={name: path}, figure_paths=[...], inputs=[...])`;
   - it writes the results JSON, figures, `methods.md` and `bundle.json`, with SHA-256 hashes and the data
     citation;
   - failed steps are refused unless `allow_failed_results=True`, which lists them as failed.
5. **Pre-registered analyses:** these already produce their bundle through `run_manifest` (recipe `preregistered`).
   Label anything else exploratory.
6. In every output, report estimates with 90% MOEs or the interval the tool used, and its validation flag.

## Epidemiologic reporting conventions (Round 82)

Drawn from *Foundations of Epidemiology* (Bovbjerg 2020; `docs/literature/foundations_of_epidemiology.md`).

1. **Say what the measure is.** ACS shares, PLACES and CHR survey measures are **prevalences** (existing cases
   over the survey window); WONDER deaths over person-years are **incidence rates**. Give units and the period
   ("per 100,000 person-years, 2018–2022"; "percent, 2019–2023 ACS"). Compare rates only in the same units and
   period. Manifest methods text lists each outcome's type; external variables may declare `measure_type`.
2. **Say what the design can show.** Area analyses are **ecologic** (they describe areas, not individuals) and
   **cross-sectional** (exposure and outcome share one window, so temporal order is unknown). Use association
   language: "is associated with", "was 1.4 times as high in … compared with …". Do not write "causes", "leads to"
   or "the effect of" for these designs (the causal tools `estimate_effect` and the DiD designs state their own
   assumptions).
3. **Interpretation sentences.** Ratios: "The prevalence of [outcome] was [ratio] times as high in [group] compared
   with [reference] ([level] CI …)." Differences: "… was [d] percentage points higher in …". If an interval includes
   the null, write "no evidence of a difference", never "no difference" (`census.epi_reporting.interpret_ratio`,
   `interpret_difference`).
4. **Intervals.** Tests use the manifest's level (Census convention 90%). Health journals expect 95%:
   `make_table(kind="comparison", confidence_level=0.95)` re-expresses intervals; p-values are unchanged.
5. **Item nonresponse.** `reliability_profile(..., allocation_tables=["B27010"], year=2023)` reports the share of
   answers the Census Bureau allocated (imputed) per area from the B99 tables. Above 5% (common: health insurance
   allocation was about 20% in MI counties for 2019–2023), discuss it as a limitation.
6. **Table 1.** `make_table(kind="table1", exposure=..., variables=[...], population=...)` describes the study areas
   by exposure tertile.
7. **Limitations.** Manifest methods text and results bundles now end with generated design limitations
   (`make_results_bundle(design="area" | "individual" | "none")`); add study-specific ones in `notes`.

## Bias and sensitivity analyses (Round 86)

Bias is systematic and statistics cannot remove it (*Foundations of Epidemiology* chapter 6); a bias analysis shows how
far plausible biases could move an estimate.
1. **Unmeasured confounding:** report the E-value with every ratio: `bias_analysis("e_value", estimate=1.5,
   lower=1.2, upper=1.9)`. `stratified_analysis` and the marginal measures (`fit_model(marginal=...)`,
   `pums_regression(marginal=...)`) include it. It is the minimum confounder strength (risk-ratio scale, with both the
   exposure and the outcome) that would explain the estimate away; it is not a test.
2. **Misclassification:** `bias_analysis("misclassification", table=[a, b, c, d], sensitivity=..., specificity=...,
   misclassified="outcome")` corrects a 2 x 2 table (one value each, or two for differential misclassification).
   `prior_sd` adds a probabilistic analysis whose interval **failed validation** (exploratory). Take sensitivity and
   specificity from a validation study, and say where they came from.
3. **Uncertain causal direction:** for a covariable declared `direction_uncertain` (manifest `covariables`), report
   the estimate with and without adjusting for it (chapter 7 practice).

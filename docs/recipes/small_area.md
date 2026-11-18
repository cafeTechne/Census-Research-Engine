# Small-area estimates (Fay-Herriot)

Goal: more reliable estimates for small areas (tracts, small counties) whose direct estimates are noisy.

1. Download the outcome and covariates for one release (`plan_extraction`, `download_table`).
2. `build_analysis_frame(input_path=<file>)` so the outcome has a `_se` column (e.g. `poverty_rate_se`).
3. `minimum_detectable_difference(moe1=...)` on a typical MOE shows how noisy the direct estimates are.
4. Full profile: `small_area_estimates(input_path=<frame>, formula="poverty_rate ~ unemployment_rate + median_rent", se_col="poverty_rate_se")`. Core profile: `fit_model(..., method="fay_herriot", se_col="poverty_rate_se")` gives the model coefficients.
5. Read `gamma` (shrinkage): near 1 keeps the direct estimate, near 0 relies on the model.
6. Report the EBLUP with its MSE-based interval next to the direct estimate and MOE. Label model-based estimates as such.

## Event counts (deaths)

Use Fay–Herriot for ACS direct estimates with known sampling variances. Use
Poisson–Gamma empirical Bayes for event counts and fixed expected counts. These
are different observation models; a death count is not an ACS estimate with an MOE.

This is a Python-library workflow; it adds no MCP tool or manifest smoothing
method. `get_recipe("small_area")` returns this guidance in either MCP profile.
Download WONDER exports by hand, preserve their bytes and hashes, and read them
with `census.vital_records.read_wonder_export`. Suppressed deaths stay missing,
with integer bounds 1–9. Do not replace them with zero, five, or an exact count.
The parser's equal lower/upper bounds on published counts are accepted as exact.

```python
from census import eb_poisson_gamma
from census.vital_records import read_wonder_export

rows = read_wonder_export(export_path)["rows"].set_index("GEOID")
# Supply a cited reference rate, in deaths per 100,000 population, in the same
# population/time units as the export. E is expected deaths, not population.
expected = rows.population * (reference_per_100000 / 100000)
smoothed = eb_poisson_gamma(
    rows.deaths, expected,
    censored_lower=rows.deaths_lower_bound,
    censored_upper=rows.deaths_upper_bound,
    reference_rate=reference_per_100000,
)
validation_note = smoothed.attrs["validation_note"]
```

`eb_ratio` is posterior mean relative risk; `eb_lower`/`eb_upper` are posterior
interval limits. `eb_rate` and its limits use the optional reference rate's units.
`shrinkage=beta/(beta+E)` approaches one when the prior dominates (the opposite
orientation to Fay–Herriot's `gamma`). Beta is a Gamma **rate**, not scale.
The default posterior interval passed Round 27's fixed 90% area-average coverage
criterion; `interval="laird_louis", n_boot=200, seed=...` also passed. Its 200
hyperparameter refits and posterior-mixture draws are slower and approximate.
Their validation does not establish coverage for every area or population.

Keep `smoothed.attrs` with exported results, especially `validation_note`, fitted
hyperparameters, confidence level and assumptions. CSV drops these attributes;
include the note in the report/sidecar. Other confidence levels or bootstrap
counts are labelled not validated. Expected counts and the reference rate are
fixed; their uncertainty and spatial dependence are not incorporated. Neither
interval is an ACS MOE or a coefficient confidence interval. ML failures raise.

For a descriptive map, join `smoothed.reset_index()` to the boundaries on GEOID
and call the existing `census.maps.choropleth(gdf, "eb_ratio", ...)`, labelling it
as empirical Bayes. Do not invent a `_se` column from these limits. Smoothed
ratios are for maps/tables, never confirmatory outcomes or hypothesis tests.
Do not publish raw suppressed counts or interpret smoothing as recovering them;
WONDER disclosure checks for study outputs remain a separate requirement.

# Regression with sampling error

Goal: a regression whose standard errors include ACS sampling error, not only model error.

1. Download the outcome and predictor tables for one release (`plan_extraction`, then `download_table`) for the same geographies (e.g. all counties in a state). Prefer detailed tables (B...): only tables on the Census Variance Replicate Estimates list for that release have replicates, and not every B table is on it (e.g. B19013 median household income has none for 2024). `build_analysis_frame` reports which variables lack replicates.
2. `build_analysis_frame(input_path=<downloaded file>, use_replicates=true, table_code="B17001", year=2023)`. Keep `output_path` and `replicates_path` from the result.
3. Check `coverage`: variables with many low-reliability rows (CV > 30%) are noisy; consider a larger geography.
4. `fit_model(input_path=<output_path>, formula="poverty_rate ~ median_rent", method="replicate", replicates_path=<replicates_path>)`.
5. No replicates? Use `method="regression_calibration"` with `error_covariates=[...]` (noisy predictors) or `method="fay_herriot"` with `se_col` (noisy outcome). `method="simex"` under-covers (validated coverage about 0.81 for nominal 0.90): use it only as an exploratory sensitivity check, never for confirmatory claims. Replicate refits capture sampling variability of the estimates; they do not remove attenuation bias from noisy predictors.
6. Report each coefficient with the SE named in the result's `interval_se_column` (the SE behind its confidence interval and p-value): `se_model` for `target="population"`, `se_sampling` for `"these_areas"`, `se_total` for `"conservative"` and for the corrected methods. Say which uncertainty sources it includes (sampling, model, or both).
7. Optional: `make_figure` or `fit_model(..., figure_dir="downloads/figures")` for a coefficient plot.

Spatial dependence (Round 26): use the existing manifest tools with analysis
`method: "fit_replicate"` and `args.spatial_clusters: {"k": 8, "method": "im"}`,
then `run_manifest`. This is the only passing spatial-cluster configuration.
IM fits each geographic cluster separately and tests the mean coefficient with
`t(7)`. It reports `se_cluster_mean`, not an additive full-sample model SE.
Only `target: "population"` is supported, and analysed variables with supplied
ACS replicates are refused. **Keep the ACS uncertainty: do not discard replicates
to make this recipe's sampling-error analysis compatible with IM.** A separate
model-only sensitivity requires an explicit change of research specification.
Every fixed geographic cluster needs at least five analysed counties/tracts and
a full-rank design; state fixed effects can be unidentifiable within a cluster.
Assignments use 50 fixed seeded restarts of EPSG:5070 k-means on representative
points, before outcome filtering, and are recorded in the bundle.

`cr1_t` (G=8/12) and `wcr` (G=12) failed the fixed validation and require an
exploratory manifest. CR1 uses `t(G-1)` with the target-specific SE; WCR uses
999 Webb-weight restricted bootstrap tests/inverted intervals with no scalar SE.
IM/WCR cannot combine with ACS replicate uncertainty. Cluster arguments are
mutually exclusive with `spatial_se` and `scale: "robust"`. Only unweighted OLS
and binomial were evaluated; EIV, Poisson and WLS are unsupported. See
`docs/audits/spatial_cluster_validation.md`; no validated cluster method currently
replaces the spatial re-checks of the registered ACS/EIV county studies.

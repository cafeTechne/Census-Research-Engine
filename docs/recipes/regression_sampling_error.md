# Regression with sampling error

Goal: a regression whose standard errors include ACS sampling error, not only model error.

1. Download the outcome and predictor tables for one release (`plan_extraction`, then `download_table`) for the same geographies (e.g. all counties in a state). Prefer detailed tables (B...): only tables on the Census Variance Replicate Estimates list for that release have replicates, and not every B table is on it (e.g. B19013 median household income has none for 2024). `build_analysis_frame` reports which variables lack replicates.
2. `build_analysis_frame(input_path=<downloaded file>, use_replicates=true, table_code="B17001", year=2023)`. Keep `output_path` and `replicates_path` from the result.
3. Check `coverage`: variables with many low-reliability rows (CV > 30%) are noisy; consider a larger geography.
4. `fit_model(input_path=<output_path>, formula="poverty_rate ~ median_rent", method="replicate", replicates_path=<replicates_path>)`.
5. No replicates? Use `method="regression_calibration"` with `error_covariates=[...]` (noisy predictors; validated for `ols`, `wls`, `poisson` and `negbin` slopes, exploratory for `binomial`, Round 46) or `method="fay_herriot"` with `se_col` (noisy outcome). `method="simex"` under-covers (validated coverage about 0.81 for nominal 0.90): use it only as an exploratory sensitivity check, never for confirmatory claims. Replicate refits capture sampling variability of the estimates; they do not remove attenuation bias from noisy predictors.
6. Report each coefficient with the SE named in the result's `interval_se_column` (the SE behind its confidence interval and p-value): `se_model` for `target="population"`, `se_sampling` for `"these_areas"`, `se_total` for `"conservative"` and for the corrected methods. Say which uncertainty sources it includes (sampling, model, or both).
7. Optional: `make_figure` or `fit_model(..., figure_dir="downloads/figures")` for a coefficient plot.

Round 30 C1 passed the fixed ACS-error validation for unweighted OLS, binomial
and Poisson: use fit_replicate with spatial_clusters={"k":8,"method":"im"},
target="population". Keep supplied ACS replicates; independent sampling error
enters between-cluster spread, without adding replicate variance. The IM estimate
is the unweighted mean of eight cluster coefficients; se_cluster_mean and t(7)
drive intervals and p-values. The estimand is the coefficient on ACS estimates
as observed, not a measurement-error-corrected true slope. Sampling error can
attenuate it; noisy controls can bias it in either direction. A zero naive slope
equates to a zero true slope only with a single error-prone covariate and errors
independent of the outcome's error; do not extend that claim to noisy controls.
Poisson exposure/expected-death offsets remain fixed.

C2 IM-EIV failed (unstable corrected moment matrices) and stays refused, even
in exploratory manifests; never substitute C1 for registered EIV without a new
specification. WLS remains unsupported. Only k=8 passed. CR1/WCR refusals remain.
IM still requires population target; scale:robust and spatial_se are mutually
exclusive with spatial_clusters. Labels are fixed before complete-case filtering
(50 seeded EPSG:5070 restarts); every retained group needs >=5 units and full rank.
Whole terms constant within every cluster are absorbed by cluster intercepts,
reported not estimable and cannot be tested. Partial constancy is refused.
R21b EIV re-checks are unavailable; R22 and R29 MI/NY C1 re-checks are post hoc,
author self-review, not independent. OH/PA is outside this validation geometry.
See docs/audits/im_acs_validation.md and docs/studies/r30_posthoc_im_acs.md.

**Spatially correlated areas (Round 35).** For corrected (EIV) slopes when neighbouring areas are
correlated, use `fit_model(method="eiv", spatial="clusters")` (eight fixed clusters, pooled
correction) or `spatial="error"` (spatial-error whitening). Both were validated for linear models
with up to four error-prone covariates (`docs/audits/spatial_eiv_validation.md`, Round 46
`docs/audits/glm_correction_validation.md`).

**Count outcomes (Round 39).** For counts with an exposure, `fit_model(model="negbin", exposure=...)`
uses NB2 with HC3 SEs, validated even with strong overdispersion and excess zeros; Poisson HC3
under-covered (.81) when overdispersion was strong (`docs/audits/manova_counts_validation.md`).

**Shares and skewed outcomes (Round 40).** For a share in 0-1 use `fit_model(model="beta")` (divide
percentages by 100); for skewed outcomes `fit_model(model="median")`. Both validated for the naive
target (`docs/audits/beta_median_validation.md`).

**Missing covariates (Round 42).** If one covariate is missing for some areas, `fit_model(..., impute="w")`
multiply imputes it (validated); `impute=["w", "v"]` imputes two by chained equations (Round 47, validated). Dropping those areas can bias slopes when missingness depends on the outcome.

**In pre-registered manifests (Round 43).** Counts: `fit_replicate` with `"args": {"model": "negbin",
"exposure": "<denominator>"}` (NB2-HC3, population target). Corrected slopes with spatial dependence:
`fit_eiv` with `"args": {"spatial": "clusters"}` (eight fixed clusters, t(7)) or `{"spatial": "error"}`
(spatial-error whitening), up to four error-prone covariates. `validate_manifest` refuses the options
outside their validated range.

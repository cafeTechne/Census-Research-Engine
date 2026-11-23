# Spatial patterns: clustering, hot spots and maps

Profile: `spatial_autocorrelation` is in `core_spatial` and `full`; `make_map` is in core; `make_web_map` is full only.

Goal: describe whether and where a variable clusters in space, and map it with its reliability.

1. **Global clustering:** `spatial_autocorrelation(input_path, column, level, year)` gives Moran's I with queen
   contiguity (`weights="rook"` or `"knn"` also work).
   - With `replicates_path`, the design-based SE of I includes ACS sampling error. It is conservative (validated
     coverage .987 for nominal .90).
2. **Local clusters (LISA):** call the same tool with `local=True`.
   - It uses 9,999 permutations and a Benjamini–Hochberg correction at .10.
   - Under sampling error LISA is characterised only (`docs/audits/lisa_validation.md`). It has little power on
     about 150 areas, and spatially varying SEs create spurious significant areas.
   - Treat local clusters as descriptive, and read the returned notes.
3. **Maps:**
   - `make_map(input_path, column, level, year, se_col=...)` makes a journal map. It hatches low-reliability areas
     and reports class separability.
   - `kind="uncertainty"` maps CVs, and `kind="significance"` maps `batch_significance` results.
   - `make_web_map(...)` makes a self-contained interactive HTML map that shows each area's MOE on hover.
4. **Regression with spatially dependent residuals:** `fit_model` warns about them (Round 71). Use
   `fit_model(spatial="scpc")`, validated for county and tract OLS slopes, as in recipe `regression_sampling_error`.
5. Report I with its interval, which local clusters survive the correction, and their caveats.

## Clusters of high counts: spatial scan (Round 81)

Profile: full (`spatial_scan`).

Use a scan, rather than LISA, for **event counts** (births, deaths, cases) when the question is "is there a group of
neighbouring counties with an unusually high rate?"
1. Call `spatial_scan(input_path, cases="<count column>", population="<denominator>")`, or `expected=` with expected
   counts from indirect standardisation. County GEOIDs only.
2. The primary cluster's p-value (999 Monte Carlo data sets, windows up to 50% of the expected total) is validated:
   false-cluster rate .099–.116 at α .10 on MI/NY and OH/PA. Other maximum windows are exploratory.
3. **Denominators must be exact** (vital records, decennial counts). ACS-estimated denominators with sampling error
   inflate false clusters (.15–.53 at α .10 with 5% error); a `<denominator>_se` column with a median CV above .01
   makes the result exploratory.
4. Many windows are scanned, so report the cluster as descriptive unless the window and α were declared in advance
   (`prespecified=True`). Secondary clusters use the same Monte Carlo p-value (conservative).
5. **WONDER rule:** suppressed counties (counts 1–9 hidden) make the scan refuse; exclude them with
   `exclude=[...]` and a stated `exclude_rule`. No count is imputed or output.

## Local relationships, neighbourhood types and regions (Round 93; Walker 2023 chapter 8)

- **Does a relationship vary over space?** `spatial_model(input_path, "gwr", level, year, outcome=...,
  predictors=[...])` fits a geographically weighted regression (bandwidth by AICc). It writes the local
  coefficients with robust intervals and gives a permutation test of non-stationarity. **Exploratory**: local
  intervals covered only .71 when slopes really varied (smoothing bias), and the test rejected .12–.17 at .10 under
  constant slopes. Report it beside a global model, and treat local collinearity and edge effects as live risks
  (Walker 8.4.3).
- **Neighbourhood types:** `spatial_model(..., "classify", ..., features=[...], k=4)` runs k-means on principal
  components. **Regions:** `"regionalize"` runs SKATER on queen contiguity. Every feature needs `_se` or `_moe`.
  - Fix k before looking at the result.
  - Each area gets a **stability** score: the share of 20 sampling-error replicates that put it in the same group.
  - In validation, areas below .8 were misclassified 39–50% of the time, against 3–16% above it. Map stability with
    the groups, and do not interpret unstable areas' labels.
- **Diversity:** `census.spatial_models.diversity_index` gives entropy (maximum ln G) with replicate intervals. It
  is exploratory: .847 coverage with about 50 respondents per tract, .883 with 200.

## Out-of-sample checks and the modifiable areal unit problem (Round 97; Moraga 2023 chapters 11 and 16)

- `spatial_model(..., "cv", outcome=..., predictors=[...])` gives 5-fold **spatial-block** and random
  cross-validation (MAE, RMSE, 90% coverage, CRPS) for OLS and for OLS with neighbour residual smoothing.
  - Random folds flatter models that borrow from neighbours.
  - In validation, spatial blocks still under-estimated error in a new region by about 20% (random folds by
    33–43%), so treat block CV as a **lower bound** (exploratory).
- `spatial_model(..., "maup", outcome=..., predictors=[x])` recomputes the slope of outcome on x over 100 random
  contiguous zonings of about 10 areas (descriptive). In validation the zone-level slope ranged from −0.2 to 1.4
  times the tract-level slope when residuals were spatially correlated. A result that depends on the zoning is a
  property of the units.


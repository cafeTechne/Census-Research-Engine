# Spatial patterns: clustering, hot spots and maps

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

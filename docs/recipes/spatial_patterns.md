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

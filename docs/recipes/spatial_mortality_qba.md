# Recipe: County Mortality BYM2 Spatial Mapping & E-Value Quantitative Bias Analysis

Use this workflow when analyzing county-level mortality from local manual CDC WONDER exports alongside ACS socioeconomic covariates, pairing validated BYM2 (`B3`) spatial smoothing with E-value sensitivity analysis for unmeasured confounding.

## Data Governance Rules
- Use only local manual CDC WONDER exports in `external_data/wonder/` (never automate WONDER web queries).
- Exclude counties with suppressed (`< 10`) counts; **never** impute or emit raw sub-national counts in `[1, 9]`.

## Steps

1. **Prepare county mortality and ACS covariates:**
   - Load local WONDER county TSV (filtering `deaths >= 10` and `population > 0`) and join ACS 5-year county covariates (e.g., `B17001` poverty rate).
   - Compute indirectly standardized expected deaths (`expected > 0` for every county).
2. **Build a connected spatial graph:**
   - Join county boundaries with `census.boundaries.join_boundaries(df, level="county", year=2022)` and drop unmatched boundary rows.
   - For regions with islands or peninsulas (e.g., NY Long Island, MI UP), build symmetric `k`-nearest-neighbor edges in EPSG:5070 (`spatial_weights(gdf.to_crs(5070), kind="knn", k=5)`) so the graph has a single connected component.
3. **Fit validated BYM2 (`B3`) disease mapping:**
   - Call `census.disease_mapping.disease_map(df, "deaths", "expected", edges, covariates=["poverty_pct"], threshold=1.20, method="B3")`.
   - Report `sigma`, `phi`, `validated`, raw SMR vs. smoothed RR interquartile range, and high-exceedance county counts ($P(\text{RR} > 1.20) \ge 0.80$).
4. **Quantify sensitivity to unmeasured confounding (E-value QBA):**
   - Call `census.bias_analysis.e_value(rr, lower=rr_lo, upper=rr_hi, measure="rr")` (or MCP `bias_analysis`).
   - Report both the point-estimate E-value (`e_value`) and the confidence-interval limit E-value (`e_value_limit`), noting age-structure confounding caveats for crude rates.

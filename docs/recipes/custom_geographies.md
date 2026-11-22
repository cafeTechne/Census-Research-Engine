# Custom geographies: neighborhoods, catchments and combined areas

Profile: these tools are in the **full** MCP profile (`aggregate_geographies`, `custom_area_mapping`, `median_from_distribution`, `apportion_tracts`); the core profile has only `derive_estimate` for a single combined ratio.

Goal: estimates for areas the Census does not publish, built from tracts or block groups, with honest MOEs.

1. **Map units to your areas.**
   - From polygons (GeoPackage, GeoJSON or shapefile):
     `custom_area_mapping("areas.gpkg", "tract", method="population")`.
   - `method="population"` or `"housing_units"` weights partial overlaps by decennial blocks, and `"area"` uses
     the overlap share.
   - Partial overlaps and the allocation assumption are reported.
   - Or write `{GEOID: area_id}` yourself.
2. **Combine counts** with `aggregate_geographies(input_path, groups={GEOID: area_id}, variables=[...], derive=[...])`.
   - It sums counts, combines their MOEs, then derives rates on the combined counts.
   - Never average member rates or medians.
   - `use_replicates=True` (with `table_code`) gives exact replicate MOEs.
3. **Medians of combined areas:** `median_from_distribution(table_code, year, input_path=..., geoids=[...])`
   interpolates from bracket counts such as B19001, B25063 or B25075, as the ACS does.
   - `use_replicates=True` gives the exact MOE.
   - Medians are never averaged.
4. **Tracts across 2010 and 2020:** `apportion_tracts(input_path, target_vintage=2020)` reallocates counts with
   decennial block weights.
   - Medians, means and percentages are refused: apportion counts, then re-derive.
   - For new extractions, prefer `batch_download(harmonize_tracts_to=2020)`.
5. Report the mapping method, any partial-overlap share, and MOEs from the combined counts.

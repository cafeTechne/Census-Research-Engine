# Walker, *Analyzing US Census Data*: guidance mapped to engine work

Source: Walker K. *Analyzing US Census Data: Methods, Maps, and Models in R*. CRC Press, 2023; online edition
https://walker-data.com/census-r/ (read 2026-11-23 from the public web version; a text copy was kept only in the
session scratchpad, not in the repository). Summary and mapping by the maintainer agent to draft Rounds 92–93
(backlog N68–N69). Author self-review, not independent.

| Chapter | Topic | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 2–3 | tidycensus access; derived MOEs; time series cautions (geography changes, overlapping releases, variable changes) | Extraction, concordance, MOE derivation, overlap refusals: covered | — |
| 4 | Visualising MOEs (error bars), ACS time series, **population pyramids from the Population Estimates API** | Figures with intervals; no Population Estimates source | 92: Population Estimates Program (PEP) source (annual county/state population by age and sex) |
| 5–6 | TIGER/Line boundaries, cartographic files, CRS, mapping | `get_boundaries`, `make_map`: covered | — |
| 7 | Spatial overlay and joins; **area- and population-weighted areal interpolation** for small-area time series; distance and travel time; catchments; spatial weights; Moran's I and LISA | Block-weighted apportionment, custom areas, Moran's I and LISA: covered (no travel-time isochrones: needs a routing service) | — |
| 8 | Segregation and diversity indices; regression on census data with PCA; spatial lag and error models; **geographically weighted regression** (exploratory, with collinearity and edge-effect caveats); **geodemographic classification** (k-means on principal components) and **regionalization** (SKATER, contiguity-constrained) | Segregation, PCA indices, spatial regression: covered; no GWR, no classification or regionalization with ACS uncertainty | 93: GWR (exploratory unless validated), geodemographic classification and SKATER regionalization with replicate-based stability; an entropy diversity index |
| 9–10 | PUMS via the API, PUMAs, survey designs with 80 replicate weights, models | Covered (PUMS tools, SDR methods) | — |
| 11 | Historical data (NHGIS, IPUMS full-count), **LEHD LODES** (jobs and commuting by block), BLS, USDA; writing API clients | No LODES, no migration flows; NHGIS requires an account (manual, like WONDER) | 92: LODES (workplace and residence jobs, origin-destination) and ACS county-to-county migration flows; NHGIS left out (account terms) |

Outcome (2026-11-23): Round 92 added PEP, LODES and migration flows; Round 93 added `spatial_model` (GWR exploratory, failed validation; classification and SKATER descriptive with stability; diversity exploratory).

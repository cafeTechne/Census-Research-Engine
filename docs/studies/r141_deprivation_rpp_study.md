# Round 141 Study Report: 4-State County Deprivation Index (PCA) & BEA Regional Price Parity Real Per-Capita Income (2020–2024)

**Pre-registration Protocol SHA-256:** `b679969632ef985b1db3e6517eda0feae863a26dfe9af2be44976c7edce33a1f`  
**Script:** [r141_deprivation_rpp_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r141_deprivation_rpp_study.py)  
**Data:** ACS 5-Year 2020–2024 county VRE tables (`B17001`, `B15002`, `B25003`, `B19025`, `B01003`) across 300 counties in Michigan (`26`), New York (`36`), Ohio (`39`), and Pennsylvania (`42`), paired with BEA 2023 Regional Price Parities (`census.rpp.adjust_for_place`).

## 1. PCA Deprivation Index (`census.composite_index.build_index`, $N = 300$ counties)
- **PC1 Variance Explained:** `53.82%`
- **Standardized Loadings (with `real_pci` reversed):** `real_pci` (`+0.645`), `non_ba_pct` (`+0.608`), `poverty_pct` (`+0.449`), `renter_pct` (`-0.114`)
- **3-Cluster Descriptive Typology (`typology_k = 3`):** Group 0 = `139` counties, Group 1 = `88` counties, Group 2 = `73` counties.

## 2. Nominal vs. BEA RPP Real Per-Capita Income & Mean Deprivation by State

| State | Counties | Median Nominal PCI (\$) | Median Real (RPP-Adjusted) PCI (\$) | Mean Deprivation Score |
| :--- | :---: | :---: | :---: | :---: |
| Michigan (`26`) | 83 | \$34,848 | \$36,956 | `+0.220` |
| New York (`36`) | 62 | \$38,357 | \$35,568 | `-0.358` |
| Ohio (`39`) | 88 | \$34,548 | \$37,592 | `+0.154` |
| Pennsylvania (`42`) | 67 | \$35,718 | \$36,672 | `-0.144` |

## Key Findings
1. **RPP Adjustment Halves the Interstate Income Spread and Reverses Rank Order:** The 4-state spread in median county nominal per-capita income is **\$3,808** (New York highest at \$38,357, Ohio lowest at \$34,548). After adjusting for BEA Regional Price Parities, the spread narrows by **46.8%** to **\$2,025**, and Ohio's median county real purchasing power (\$37,592) surpasses New York's (\$35,568).
2. **Economic & Educational Axis Dominates County Deprivation:** Reversed real per-capita income, non-BA+ attainment, and poverty co-load strongly on PC1 (`53.8%` variance explained), while county renter share loads weakly negatively (`-0.114`) because affluent urban/college counties have higher renter shares than rural counties.

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** State-level BEA 2023 RPP is applied across counties within each state, which does not capture within-state metropolitan vs. rural price dispersion (e.g., NYC metro vs. upstate NY).

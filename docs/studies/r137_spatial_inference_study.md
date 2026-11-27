# Round 137 Study Report: County Spatial Autocorrelation & SCPC vs. HC3 Inference (MI/NY & OH/PA, 2020–2024)

**Pre-registration Protocol SHA-256:** `fa9d7bbdc35dfe02b1c22faff42500d4b45377ea9588888d6b500168b7461e2c`  
**Script:** [r137_spatial_inference_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r137_spatial_inference_study.py)  
**Data:** ACS 5-Year 2020–2024 county VRE tables `B17001` (poverty rate) and `B15002` (BA+ attainment among ages 25+) across two 2-state regions: MI + NY (`145` counties, primary) and OH + PA (`155` counties, replication).

## Empirical Results (90% Confidence Level, SCPC $\bar{\rho} = 0.05$)

| Region | Counties | Validated Spearman $\rho$ (90% CI) | OLS `ba_plus` Slope (pp poverty / pp BA+) | HC3 SE | SCPC 90% CI (`rho_bar = 0.05`) | CI Width Ratio (SCPC / HC3) | SCPC Validated |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + NY (`26`, `36`) | 145 | `-0.298` (`-0.421`, `-0.163`) | `-0.1211` | `0.0387` | (`-0.2142`, `-0.0281`) | `1.463×` | Yes |
| OH + PA (`39`, `42`) | 155 | `-0.398` (`-0.507`, `-0.277`) | `-0.1503` | `0.0317` | (`-0.2294`, `-0.0712`) | `1.515×` | Yes |

## Key Findings
1. **HC3 Substantially Understates County-Level Uncertainty:** Accounting for spatial correlation via Müller–Watson SCPC (`rho_bar = 0.05`) widens 90% confidence intervals by **46.3%** in MI/NY and **51.5%** in OH/PA relative to heteroskedasticity-robust HC3 intervals.
2. **Robust Inverse Education–Poverty Gradient:** Even after SCPC spatial widening, higher county BA+ attainment remains significantly associated with lower county poverty in both primary (`-0.121` pp/pp) and replication (`-0.150` pp/pp) regions, corroborated by validated Spearman correlations (`-0.298` and `-0.398`).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** Cross-sectional ecologic county regression with state fixed effects; causal interpretation is not warranted.

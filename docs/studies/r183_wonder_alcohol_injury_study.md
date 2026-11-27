# Round 183 Study Report: WONDER 2018–2022 County Alcohol-Induced & Unintentional Injury Mortality — BYM2 (`B3`) Mapping & E-Value QBA

**Pre-registration Protocol SHA-256:** `baaa5796d09cd2dbd2e4ceaa60696b5d0c2dd4cad0eb882e7e11fae50f1b11fb`  
**Script:** [r183_wonder_alcohol_injury_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r183_wonder_alcohol_injury_study.py)  
**Data:** Local manual CDC WONDER Underlying Cause of Death 2018–2022 county exports (`alcohol_induced.tsv`, `unintentional_injury.tsv`; counties with suppressed `< 10` deaths excluded) merged with ACS 2020–2024 county poverty (`B17001`) across MI+OH (primary) and NY+PA (replication).

## Empirical Results

| Region & Cause | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH Alcohol-Induced | 159 | `0.264` / `0.65` | Yes | `0.464` → `0.467` | 40 | `1.172` (`1.128`, `1.218`) | `1.62` / `1.51` |
| MI + OH Unintentional Injury | 171 | `0.264` / `0.80` | Yes | `0.339` → `0.302` | 21 | `1.539` (`1.514`, `1.565`) | `2.45` / `2.40` |
| NY + PA Alcohol-Induced | 120 | `0.264` / `0.95` | Yes | `0.428` → `0.343` | 28 | `1.123` (`1.086`, `1.162`) | `1.50` / `1.39` |
| NY + PA Unintentional Injury | 129 | `0.264` / `0.95` | Yes | `0.456` → `0.432` | 36 | `1.056` (`1.042`, `1.070`) | `1.30` / `1.25` |

## Key Findings
1. **Cross-Regional Positive Poverty Gradient Across Both Causes:** Unlike older-age chronic causes in NY+PA, both alcohol-induced mortality (`RR = 1.172` MI+OH, `1.123` NY+PA) and unintentional injury mortality (`RR = 1.539` MI+OH, `1.056` NY+PA) are significantly elevated in top-quartile poverty counties in **both** primary and replication regions.
2. **Validated Spatial Clustering ($\phi = 0.65$–$0.95$):** All 4 BYM2 (`B3`) fits are validated, with strong spatial smoothing in NY+PA alcohol-induced mortality (`0.428` → `0.343`, `-19.8%` IQR).
3. **Publication Bundle Verified:** `verify_bundle("studies_output/r183_wonder_alcohol_injury/bundle")` returned `ok: true` (`checked_files: 6`, `errors: []`).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Data governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.

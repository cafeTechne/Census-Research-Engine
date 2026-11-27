# Round 178 Study Report: WONDER 2018–2022 County Kidney Disease & Firearm Mortality — BYM2 (`B3`) Mapping & E-Value QBA

**Pre-registration Protocol SHA-256:** `7f29a3d35cae9e9a7c36f8d851f9bf61942b763dc61bf4207555934462f10e05`  
**Script:** [r178_wonder_kidney_firearm_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r178_wonder_kidney_firearm_study.py)  
**Data:** Local manual CDC WONDER Underlying Cause of Death 2018–2022 county exports (`kidney_disease.tsv`, `firearm.tsv`; counties with suppressed `< 10` deaths excluded) merged with ACS 2020–2024 county poverty (`B17001`) across MI+OH (primary) and NY+PA (replication).

## Empirical Results

| Region & Cause | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH Kidney Disease | 163 | `0.407` / `0.95` | Yes | `0.576` → `0.461` | 38 | `1.558` (`1.511`, `1.606`) | `2.49` / `2.39` |
| MI + OH Firearm | 151 | `0.171` / `0.05` | Yes | `0.436` → `0.274` | 10 | `2.075` (`2.000`, `2.153`) | `3.57` / `3.42` |
| NY + PA Kidney Disease | 125 | `0.264` / `0.80` | Yes | `0.515` → `0.456` | 56 | `0.833` (`0.813`, `0.854`) | `1.69` / `1.62` |
| NY + PA Firearm | 121 | `0.407` / `0.95` | Yes | `0.745` → `0.683` | 45 | `1.410` (`1.361`, `1.462`) | `2.17` / `2.06` |

## Key Findings
1. **Robust Cross-Regional Firearm Poverty Gradient (`RR = 2.075` MI+OH, `1.410` NY+PA):** Firearm mortality is strongly elevated in top-quartile poverty counties in both primary (`E-value = 3.57`, CI limit `3.42`) and replication (`E-value = 2.17`, CI limit `2.06`) regions.
2. **Large Spatial Shrinkage on Sparse Firearm Counts:** MI+OH firearm SMR IQR shrinks **37.1%** (`0.436` → `0.274`) under validated BYM2 (`B3`) smoothing.
3. **Publication Bundle Verified:** `verify_bundle("studies_output/r178_wonder_kidney_firearm/bundle")` returned `ok: true` (`checked_files: 6`, `errors: []`).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Data governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.

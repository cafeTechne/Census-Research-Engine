# Round 173 Study Report: WONDER 2018–2022 County CLRD & Chronic Liver Disease Mortality — BYM2 (`B3`) Mapping & E-Value QBA

**Pre-registration Protocol SHA-256:** `5f41a94bce7cfbef8f804c0b33de514f0c0dde2ef2674ace165792e822ff7cdf`  
**Script:** [r173_wonder_clrd_liver_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r173_wonder_clrd_liver_study.py)  
**Data:** Local manual CDC WONDER Underlying Cause of Death 2018–2022 county exports (`clrd.tsv`, `liver_disease.tsv`; counties with suppressed `< 10` deaths excluded) merged with ACS 2020–2024 county poverty (`B17001`) across MI+OH (primary) and NY+PA (replication).

## Empirical Results

| Region & Cause | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH CLRD | 170 | `0.407` / `0.95` | Yes | `0.511` → `0.481` | 84 | `1.324` (`1.300`, `1.348`) | `1.98` / `1.93` |
| MI + OH Liver Disease | 164 | `0.264` / `0.80` | Yes | `0.417` → `0.366` | 41 | `1.308` (`1.264`, `1.353`) | `1.94` / `1.84` |
| NY + PA CLRD | 129 | `0.264` / `0.80` | Yes | `0.531` → `0.507` | 94 | `0.882` (`0.868`, `0.897`) | `1.52` / `1.47` |
| NY + PA Liver Disease | 124 | `0.264` / `0.95` | Yes | `0.477` → `0.375` | 67 | `0.896` (`0.867`, `0.926`) | `1.48` / `1.37` |

## Key Findings
1. **Strong Spatial Clustering Across Both Causes ($\phi = 0.80$–$0.95$):** All 4 BYM2 (`B3`) fits are validated, with consistent shrinkage from raw SMRs to smoothed RRs (e.g., NY+PA liver disease IQR shrinks `21.4%` from `0.477` to `0.375`).
2. **Consistent MI+OH Poverty Gradient (`RR = 1.324` CLRD, `1.308` Liver Disease):** Top-quartile poverty counties experience ~31–32% higher crude CLRD and liver disease mortality in MI+OH (`E-value = 1.98` and `1.94`), while NY+PA again exhibits crude urban–rural age/smoking inversion (`RR = 0.882` / `0.896`).
3. **Publication Bundle Verified:** `verify_bundle("studies_output/r173_wonder_clrd_liver/bundle")` returned `ok: true` (`checked_files: 6`, `errors: []`).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Data governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.

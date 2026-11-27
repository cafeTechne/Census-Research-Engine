# Round 168 Study Report: WONDER 2018–2022 County Suicide & Diabetes Mortality — BYM2 (`B3`) Mapping & E-Value QBA

**Pre-registration Protocol SHA-256:** `ecdc4b305a19d47cafb8f56afcb1d4f7a008eef395f26618dfa949fc601a070c`  
**Script:** [r168_wonder_suicide_diabetes_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r168_wonder_suicide_diabetes_study.py)  
**Data:** Local manual CDC WONDER Underlying Cause of Death 2018–2022 county exports (`suicide.tsv`, `diabetes.tsv`; counties with suppressed `< 10` deaths excluded) merged with ACS 2020–2024 county poverty (`B17001`) across MI+OH (primary) and NY+PA (replication).

## Empirical Results

| Region & Cause | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH Suicide | 164 | `0.171` / `0.50` | Yes | `0.362` → `0.244` | 31 | `1.110` (`1.071`, `1.151`) | `1.46` / `1.35` |
| MI + OH Diabetes | 169 | `0.407` / `0.80` | Yes | `0.469` → `0.416` | 54 | `1.458` (`1.425`, `1.492`) | `2.28` / `2.20` |
| NY + PA Suicide | 125 | `0.264` / `0.95` | Yes | `0.442` → `0.420` | 63 | `0.849` (`0.823`, `0.876`) | `1.63` / `1.54` |
| NY + PA Diabetes | 129 | `0.407` / `0.95` | Yes | `0.609` → `0.560` | 67 | `1.163` (`1.141`, `1.186`) | `1.60` / `1.54` |

## Key Findings
1. **Substantial BYM2 Variance Shrinkage:** Every fit is validated under `B3`. MI+OH county suicide SMR dispersion shrinks by **32.7%** (`0.362` → `0.244`) under spatial smoothing, while diabetes exhibits strong spatial clustering ($\sigma = 0.407$, $\phi = 0.80$–$0.95$) in both regions.
2. **Consistent Diabetes Poverty Gradient (`RR = 1.458` MI+OH, `1.163` NY+PA):** Top-quartile poverty counties experience significantly elevated diabetes mortality in both primary (`E-value = 2.28`, CI limit `2.20`) and replication (`E-value = 1.60`, CI limit `1.54`) regions.
3. **Urban–Rural Suicide Inversion in NY+PA:** NY+PA crude suicide mortality is lower in high-poverty counties (`RR = 0.849`), reflecting low suicide rates in high-poverty urban NYC boroughs compared to rural upstate NY and PA counties.
4. **Publication Bundle Verified:** `verify_bundle("studies_output/r168_wonder_suicide_diabetes/bundle")` returned `ok: true` (`checked_files: 6`, `errors: []`).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Data governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.

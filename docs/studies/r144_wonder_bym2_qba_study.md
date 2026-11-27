# Round 144 Study Report: WONDER 2018–2022 County Heart Disease & Drug Overdose Mortality — BYM2 (`B3`) Mapping & E-Value QBA

**Pre-registration Protocol SHA-256:** `2c8315c3ef9f31e3785a6b331e97deccb752656277633d1556c7794553aba31c`  
**Script:** [r144_wonder_bym2_qba_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r144_wonder_bym2_qba_study.py)  
**Data:** Local manual CDC WONDER Underlying Cause of Death 2018–2022 county exports (`heart_disease.tsv`, `drug_overdose.tsv`; counties with suppressed `< 10` deaths excluded) merged with ACS 2020–2024 county poverty (`B17001`) across two contiguous 2-state regions: MI + OH (`26`, `39`, primary) and NY + PA (`36`, `42`, replication), using symmetric 5-nearest-neighbor spatial graphs in EPSG:5070 and validated BYM2 (`B3`) smoothing (`threshold = 1.20`).

## Empirical Results

| Region & Cause | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH Heart Disease | 171 | `0.264` / `0.95` | Yes | `0.288` → `0.279` | 44 | `1.309` (`1.299`, `1.320`) | `1.95` / `1.92` |
| MI + OH Drug Overdose | 159 | `0.407` / `0.65` | Yes | `0.561` → `0.542` | 25 | `2.313` (`2.252`, `2.375`) | `4.06` / `3.93` |
| NY + PA Heart Disease | 129 | `0.264` / `0.95` | Yes | `0.308` → `0.300` | 37 | `0.982` (`0.975`, `0.988`) | `1.16` / `1.12` |
| NY + PA Drug Overdose | 125 | `0.407` / `0.95` | Yes | `0.497` → `0.465` | 18 | `1.339` (`1.314`, `1.364`) | `2.01` / `1.96` |

## Key Findings
1. **Strong Spatial Clustering & Validated BYM2 Shrinkage:** Every regional model is validated under `B3` with high spatial mixing ($\phi = 0.65$–$0.95$) and consistent variance shrinkage from raw SMRs to smoothed RRs. Drug overdose exhibits substantially larger inter-county dispersion ($\sigma = 0.407$) than heart disease ($\sigma = 0.264$) in both regions.
2. **Robust Poverty Gradient for Drug Overdose (`E-value = 4.06` MI+OH, `2.01` NY+PA):** Top-quartile poverty counties experience `2.31×` higher crude drug overdose mortality in MI+OH and `1.34×` in NY+PA; an unmeasured confounder would need associations of at least `3.93×` (MI+OH) or `1.96×` (NY+PA) with both poverty and overdose mortality to explain away the 90% CI.
3. **Age-Composition Confounding in NY+PA Crude Heart Disease:** While MI+OH shows a clear crude heart-disease poverty gradient (`RR = 1.309`, `E-value = 1.95`), NY+PA shows a slightly inverted crude ratio (`RR = 0.982`, `E-value = 1.16`), reflecting younger age distributions in high-poverty NYC boroughs relative to older, lower-poverty rural counties — illustrating why crude ecologic mortality ratios require age standardization.

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Data governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.
- **Limitations:** Expected deaths use regional crude rates rather than age-specific indirect standardization; Q4 vs. Q1 E-values assess sensitivity of crude ecologic ratios to unmeasured confounding (including age structure).

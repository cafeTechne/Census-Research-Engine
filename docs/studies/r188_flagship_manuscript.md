# Spatial Dependence, Small-Area Shrinkage, and Ecologic Confounding in US County Mortality Surveillance: An 11-Cause Pre-Registered Analysis Across Four Industrial-Midwest and Northeast States, 2018–2022

**Study Status:** Pre-registered Layer A confirmatory synthesis (`Round 188`, offline reproducible; zero automated WONDER access; zero raw sub-national 1–9 counts emitted).

## Abstract

**Background:** County-level mortality surveillance routinely links American Community Survey (ACS) socioeconomic indicators to vital statistics, yet standard workflows often ignore spatial autocorrelation, small-area instability, ranking uncertainty, ecologic aggregation bias, and regional price differences.

**Methods:** Using a pre-registered, cryptographically verified Layer A statistical engine, we analyzed 2018–2022 CDC WONDER county mortality across **11 leading causes of death** (`heart_disease`, `drug_overdose`, `stroke`, `suicide`, `diabetes`, `clrd`, `liver_disease`, `kidney_disease`, `firearm`, `alcohol_induced`, and `unintentional_injury`) in Michigan and Ohio (primary, up to 171 counties) with out-of-region replication in New York and Pennsylvania (up to 129 counties), linked to 2020–2024 ACS 5-year estimates and 2023 BEA Regional Price Parities. We fit validated Besag-York-Mollié (BYM2, `B3`) spatial models, computed Q4/Q1 poverty crude rate ratios (90% CIs) and VanderWeele–Ding E-values, and quantified four methodological pitfalls (SCPC vs. HC3 spatial inference, KWW county ranking sets, PUMA microdata ecologic decomposition, and BEA RPP income adjustment).

**Results:** In MI+OH, all **11/11** mortality causes showed elevated mortality in high-poverty (Q4) versus low-poverty (Q1) counties, led by drug overdose (`RR = 2.31`, 90% CI `2.25–2.37`, `E_CI = 3.93`) and firearm mortality (`RR = 2.08`, 90% CI `2.00–2.15`, `E_CI = 3.42`). In NY+PA replication, **5/11** causes remained positively associated with poverty (including drug overdose `RR = 1.34`, firearm `RR = 1.41`, diabetes `RR = 1.16`, alcohol-induced `RR = 1.12`, unintentional injury `RR = 1.06`), whereas **6/11** chronic/suicide causes inverted (`RR < 1.0`), reflecting dense, high-poverty but lower-mortality urban counties (e.g., NYC boroughs) versus older rural counties. BYM2 spatial mixing $\phi$ was high (`0.50–0.95` in 21/22 cause-region models), and BYM2 smoothing shrank raw SMR IQRs across causes. Methodological benchmarks showed SCPC widens 90% CIs by `1.46x–1.52x` over HC3, KWW joint rank widths span `45–64` ranks (only `2/300` counties certifiably top-decile), between-PUMA ecologic slopes inflate individual microdata slopes by `~10x`, and BEA RPP compresses 4-state median income spread by `-46.8%`.

**Conclusions:** Robust county health surveillance requires paired out-of-region replication, BYM2 small-area smoothing, spatial-correlation-robust inference, explicit rank uncertainty, and microdata validation against ecologic confounding.

## 1. Eleven-Cause County Mortality Atlas (Table 1)

| Cause of Death | MI+OH RR (90% CI) | MI+OH E-val | MI+OH phi | NY+PA RR (90% CI) | NY+PA E-val | NY+PA phi |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| Drug Overdose | 2.31 (2.25-2.37) | 3.93 | 0.65 | 1.34 (1.31-1.36) | 1.96 | 0.95 |
| Firearm | 2.08 (2.00-2.15) | 3.42 | 0.05 | 1.41 (1.36-1.46) | 2.06 | 0.95 |
| Kidney Disease | 1.56 (1.51-1.61) | 2.39 | 0.95 | 0.83 (0.81-0.85) | 1.62 | 0.80 |
| Unintentional Injury | 1.54 (1.51-1.56) | 2.40 | 0.80 | 1.06 (1.04-1.07) | 1.25 | 0.95 |
| Diabetes | 1.46 (1.42-1.49) | 2.20 | 0.80 | 1.16 (1.14-1.19) | 1.54 | 0.95 |
| CLRD | 1.32 (1.30-1.35) | 1.93 | 0.95 | 0.88 (0.87-0.90) | 1.47 | 0.80 |
| Heart Disease | 1.31 (1.30-1.32) | 1.92 | 0.95 | 0.98 (0.98-0.99) | 1.12 | 0.95 |
| Liver Disease | 1.31 (1.26-1.35) | 1.84 | 0.80 | 0.90 (0.87-0.93) | 1.37 | 0.95 |
| Alcohol-Induced | 1.17 (1.13-1.22) | 1.51 | 0.65 | 1.12 (1.09-1.16) | 1.39 | 0.95 |
| Suicide | 1.11 (1.07-1.15) | 1.35 | 0.50 | 0.85 (0.82-0.88) | 1.54 | 0.95 |
| Stroke | 1.08 (1.06-1.10) | 1.32 | 0.80 | 0.78 (0.77-0.80) | 1.82 | 0.65 |


*Figures:* `figures/fig1_mortality_poverty_forest.pdf` (paired forest plot with E-values) and `figures/fig2_bym2_shrinkage_spatial.pdf` (BYM2 IQR shrinkage and spatial mixing $\phi$).

## 2. Empirical Methodological Pitfalls Benchmark (Table 2)

| Methodological Domain | Naive Practice | Validated Layer A Method | Empirical Finding |
| --- | --- | --- | --- |
| Spatial autocorrelation (R137) | HC3 robust SEs | SCPC spatial CIs (\bar{\rho}=0.05) | CIs widen 1.46x (MI+NY) and 1.52x (OH+PA) |
| County ranking (R139) | Unadjusted point ranks | KWW individual & joint rank sets | Median joint width 45--64 ranks; only 2/300 certifiably top-decile |
| Ecologic aggregation (R136) | PUMA-level ecologic logit | Within- vs. between-PUMA PUMS logit | Between-PUMA slope (11.83, 12.56) ~10x within (1.18, 1.26) |
| Regional cost of living (R141) | Nominal ACS per-capita income | BEA 2023 RPP-adjusted real PCI | 4-state spread narrows from $3,808 to $2,025 (-46.8%) |


*Figure:* `figures/fig3_methodological_pitfalls.pdf` (4-panel naive vs. validated comparison).

## 3. Reproducibility & Governance

- All inputs derive from local, manually exported CDC WONDER 2018–2022 tables and cached 2020–2024 ACS 5-year / 2019–2023 PUMS extracts.
- Zero raw sub-national counts of 1–9 are printed or stored in any table, figure, or narrative.
- Bundle cryptographic verification (`verify_bundle`) seals SHA-256 digests of all tables, methods text, and `references.bib`.

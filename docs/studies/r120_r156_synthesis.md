# Cross-Study Empirical Synthesis (`Rounds 120–156`), Layer B SSD Benchmark & N39 Preflight Status

This synthesis consolidates all pre-registered empirical studies executed across Rounds 120–156, the Samsung 850 EVO SSD Layer B corpus benchmark, and the live N39 (ACS 2021–2025) release preflight check.

## 1. Pre-Registered Empirical Studies (`Rounds 120–156`)

| Round | Study & Report | Geography / Sample | Core Validated Method(s) | Headline Empirical Finding |
| :---: | :--- | :--- | :--- | :--- |
| 120 | [r120_cancer_surveillance_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r120_cancer_surveillance_study.md) | 4 states (MI, NY, OH, PA; 300 counties) | BYM2 disease mapping, Kulldorff scan, HKSJ pooling | Validated spatial clusters & multi-state pooling on WONDER cancer mortality |
| 121 | [r121_medicare_rdd_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r121_medicare_rdd_study.md) | MI + OH PUMS ($N = 325{,}216$) | Sharp RDD at age 65 (80 SDR replicates) | Large discrete Medicare coverage jump at age 65 replicated across MI & OH |
| 122 | [r122_multi_release_disparity_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r122_multi_release_disparity_study.md) | MI/NY + OH/PA (2015–2019 vs. 2020–2024) | Two-group DiD, HKSJ meta-analysis | Nonmetro vs. metro poverty trends pooled across 4 states |
| 126 | [r126_demography_ypll_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r126_demography_ypll_study.md) | US National WONDER 2018–2022 | Chiang II life tables, exact Arriaga, YPLL-75 | Exact female–male $e_0$ gap `+5.446` years; cause-specific YPLL-75 ranked |
| 127 | [r127_pums_decomposition_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r127_pums_decomposition_study.md) | MI + OH PUMS ($N = 524{,}618$) | Oaxaca–Blinder & Fairlie (80 replicates) | Disability earnings & poverty gaps tightly replicated across MI & OH |
| 131 | [r131_segregation_5state_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r131_segregation_5state_study.md) | AZ, GA, MI, NY, TX (525 counties, `B03002`) | Bias-corrected $D$, isolation, Theil $H$ | Validated tract-level segregation profiles across 5 diverse states |
| 132 | [r132_sae_temporal_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r132_sae_temporal_study.md) | MI/NY + OH/PA (300 counties, 3 releases) | Arcsine & Rao–Yu temporal Fay–Herriot | Temporal borrowing cut median MSE by `26.3%` (MI/NY) and `31.8%` (OH/PA) |
| 134 | [r134_who_inequality_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r134_who_inequality_study.md) | MI, NY, OH, PA (300 counties) | WHO monitoring (PAR vs. best) & quadrants | Priority quadrant classification with 80-replicate CIs |
| 136 | [r136_pums_inequality_ecologic_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r136_pums_inequality_ecologic_study.md) | MI + OH PUMS ($N = 524{,}618$) | `pums_inequality`, `ecologic_check` (Fuller) | Gini `0.450`/`0.440`; between-PUMA poverty–disability log-OR ~10× within-PUMA |
| 137 | [r137_spatial_inference_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r137_spatial_inference_study.md) | MI/NY (145) + OH/PA (155) counties | Spatial Spearman, SCPC ($\bar{\rho}=0.05$) vs. HC3 | SCPC 90% CIs are `1.46×`–`1.52×` wider than naive HC3 |
| 139 | [r139_county_ranking_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r139_county_ranking_study.md) | MI, NY, OH, PA (300 counties) | KWW individual/joint ranks & Holm reference | Only `2/300` counties certifiably top-decile; `129/300` differ from state mean (Holm) |
| 141 | [r141_deprivation_rpp_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r141_deprivation_rpp_study.md) | MI, NY, OH, PA (300 counties) | PCA deprivation index & BEA 2023 RPP | RPP cuts 4-state PCI spread by `46.8%` (\$3,808 → \$2,025) and flips OH above NY |
| 142 | [r142_pums_causal_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r142_pums_causal_study.md) | MI + OH PUMS ($N = 25{,}000$ each) | AIPW, IPW, Overlap ATO & positivity | BA+ ATE on poverty: `-8.84` pp (MI) / `-8.89` pp (OH), `0.00%` overlap violations |
| 144 | [r144_wonder_bym2_qba_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r144_wonder_bym2_qba_study.md) | MI+OH & NY+PA WONDER (2018–2022) | BYM2 (`B3`) & E-value QBA | Drug overdose Q4/Q1 poverty RR `2.31` (E-value `4.06`) MI+OH / `1.34` (`2.01`) NY+PA |
| 156 | [r156_layer_b_to_layer_a_study.md](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/docs/studies/r156_layer_b_to_layer_a_study.md) | MI+OH (171) & NY+PA (129) stroke | Live Layer B SSD → Layer A BYM2 + `verify_bundle` | Validated BYM2 shrinkage (`0.391` → `0.308` NY+PA); bundle verified (`ok: true`) |

## 2. Samsung 850 EVO SSD Layer B Corpus & BM25 Benchmark
- **Literature FTS5 Index:** `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/index.sqlite` — **130 deduplicated papers** (`multi(openalex+epmc)` across 5 core epidemiology/demography topics).
- **Passage Citation Index:** `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/passages.sqlite` — **188 passages across 15 local study reports** (`docs/studies/r1*.md`).
- **5-Query BM25 Benchmark:** All 5 queries (`Q1–Q5`) returned 30 FTS candidates each with high-relevance top-1 hits (scores `2.68–10.08`). Note: `torch`/`transformers` are intentionally kept out of Layer A's `.venv`; installing them in a separate Layer B venv activates neural `OpenScholar/OpenScholar_Reranker` reranking without altering Layer A dependencies.

## 3. N39 (ACS 2021–2025 Release Refresh) Preflight Status
- Live run of `scripts/acs_release_preflight.py --target-year 2025` on **2026-11-27**: `ready: false` (`has_target_metadata: false`, price indexes & RPP through `2024`, `crosswalk_error_count: 0`). Round 125 / N39 remains parked until the Census Bureau publishes the 2021–2025 5-year release (~mid-December 2026).

## Review Note
- Author self-review, not independent.

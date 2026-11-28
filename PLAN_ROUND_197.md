# Plan — Round 197 (N128): Age-Structure (`% 65+`) & Urban-Rural Stratified County Mortality Confounding Study (`v0.193.0`)

## 1. Strategic Objective
Directly test and quantify the confounding mechanism identified in the Round 188 11-cause county mortality atlas: why 6 chronic/suicide causes inverted (`Q4/Q1 crude RR < 1.0`) in NY+PA while remaining strongly positive in MI+OH. Using 100% offline cached ACS `B01001` (county `% age 65+`), `B17001` (county poverty), county population-size / density urbanicity strata, and all 11 local CDC WONDER 2018–2022 county exports, compare **crude Q4/Q1 poverty RRs** against **age-structure-adjusted (`% 65+`) and urban-rural-stratified Poisson/GLM poverty rate ratios (HC3 robust SEs)**.

## 2. Exact File Contracts
1. `scripts/r197_age_urban_mortality_confounding.py`:
   - Loads all 11 WONDER causes across MI+OH (`26, 39`) and NY+PA (`36, 42`), joined with ACS `B17001` poverty, `B01001` `% age 65+`, and county urbanicity (`metro_large >= 250k`, `mid_small 50k–250k`, `rural < 50k` / log-population-density).
   - Fits offset Poisson GLM (`log(deaths) ~ poverty_q4_vs_q1 + pct_65_plus + log_pop_density + offset(log(population))`, HC3 SEs) and rural-vs-urban stratified Q4/Q1 RRs for every cause in both regions.
   - Writes `studies_output/r197_age_urban_confounding/summary.json`, `docs/studies/r197_age_urban_confounding_study.md`, and a `verify_bundle`-sealed bundle.
2. `tests/test_round197.py` & `docs/audits/round197_compatibility.md`.

## 3. Governance
- 100% offline reproducible; zero automated WONDER access; zero raw sub-national counts 1–9 emitted.

## 4. Iteration Log
- *2026-11-27:* Plan drafted from roadmap item `N128`.
- *2026-11-27:* Built and ran `scripts/r197_age_urban_mortality_confounding.py` across all 11 CDC WONDER causes using cached 2024 ACS `B17001` (`% age 65+` + poverty) and TIGER `log(population density)`, wrote `docs/studies/r197_age_urban_confounding_study.md`, and sealed bundle via `verify_bundle`.

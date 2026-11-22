# Round 92 plan: data sources: Population Estimates, LEHD LODES, ACS migration flows

**Goal.** Backlog N68 (Walker, *Analyzing US Census Data*, chapters 4 and 11; mapping in
`docs/literature/walker_analyzing_us_census_data.md`).

| Source | What it gives | Why we need it |
| :--- | :--- | :--- |
| Census Population Estimates Program (PEP) | Annual July 1 population for states and counties, by age, sex, race and Hispanic origin (Census API `pep` endpoints, or the vintage files where the API has no endpoint) | Denominators for annual rates (joinpoint, MSMs, ITS) and population pyramids |
| LEHD Origin-Destination Employment Statistics (LODES) | Jobs by workplace (WAC) and residence (RAC) by block, and origin-destination flows (OD), with sectors, earnings and age bands | Access to jobs and commuting, aggregated to tracts and counties |
| ACS county-to-county migration flows (Census API `acs/flows`) | In-, out- and net flows with MOEs, by characteristic | Population churn as a covariate and as an outcome |

Version 0.88.0. Branch `phase92/sources`. No new statistics.

## 1. Engine

- **Source registry entries** (`census/context_sources.py` pattern, Round 72) with cached downloads, SHA-256
  provenance, vintage handling and a generic User-Agent.
- **PEP:** state and county totals and age × sex detail for 2010–2024 vintages. Each vintage is labelled because
  estimates are revised every year, so a vintage must never be mixed silently.
- **LODES:** a block-to-tract and block-to-county aggregation, with the LODES version (LODES8) and job type (JT00
  all jobs, …) recorded. LODES uses noise infusion, not sampling: no MOE. That is said in the output and in methods
  text, like decennial counts.
- **Flows:** MOEs carried; net-flow MOEs derived by the ACS approximation.
- **Context covariates:** `build_analysis_frame(context=[...])` and the manifest `context` block (Round 72) accept
  the new sources.
- **Circularity:** PEP populations as denominators are not outcomes; LODES and flows are covariates or outcomes per
  rules R1/R2.

## 2. Checks (numeric)

- **PEP:** state totals equal the sum of county totals for each vintage. MI and NY 2023 values match published
  numbers.
- **LODES:** tract aggregates equal county aggregates. MI 2021 total jobs match the LODES state summary.
- **Flows:** in minus out equals net for every county pair within rounding, and MOEs are present.

## 3. Docs and acceptance

- Recipe `context_covariates` sections; `README` data-sources table; protocol rules.
- STATUS, CHANGELOG, compatibility audit, tests (offline fixtures), goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| PEP | done | vintages 2019, 2024; totals and age/sex |
| LODES | done | WAC/RAC/OD; block, tract, county |
| Flows | done | 2010–2020 county-to-county; later refused |
| Checks | pass | `r92_source_checks.md` |
| Goldens, suite | pass | goldens byte-identical; 2336 passed, 42 skipped |
| Exceptions | 3 | see audit |

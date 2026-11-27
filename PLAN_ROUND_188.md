# Plan — Round 188 (Track 2): Flagship Publishable Manuscript — 10-Cause County Mortality Spatial Atlas & Methodological Pitfalls Study (`v0.183.0`)

## 1. Strategic Objective
Synthesize our validated Layer A empirical work into a **complete, journal-ready research manuscript package** (*"Spatial Dependence, Small-Area Shrinkage, and Ecologic Confounding in US County Mortality Surveillance: A 10-Cause Pre-Registered Analysis Across Four Industrial-Midwest and Northeast States, 2018–2022"*) complete with publication-grade vector figures (PDF/SVG/PNG), LaTeX booktabs tables, a compilable `manuscript.tex` + `manuscript.md`, `references.bib`, and a cryptographically verified publication bundle (`verify_bundle`).

## 2. Scientific Design & Scope
- **Data Sources (100% offline, reproducible):**
  - Local manual CDC WONDER 2018–2022 county exports across **10 leading causes of death** (`heart_disease`, `drug_overdose`, `stroke`, `suicide`, `diabetes`, `clrd`, `liver_disease`, `kidney_disease`, `firearm`, `alcohol_induced` + `unintentional_injury` = **11 causes** across 300 counties in MI+OH primary and NY+PA replication!).
  - ACS 5-Year 2020–2024 county VRE (`B17001` poverty, `B15002` education, `B19025`/`B01003` per-capita income) + BEA 2023 Regional Price Parities.
  - Cross-referenced empirical pitfall benchmarks from our pre-registered studies: SCPC vs. HC3 spatial widening (`R137`: `1.46×–1.52×`), KWW county rank uncertainty (`R139`: only `2/300` certifiably top-decile), PUMA ecologic fallacy (`R136`: ~10× between- vs. within-PUMA log-OR), and BEA RPP income-spread compression (`R141`: `-46.8%`).
- **Governance:** Zero automated WONDER access; zero raw sub-national 1–9 counts emitted anywhere in tables, figures, or text.

## 3. Exact Deliverables & File Contracts
1. `scripts/r188_flagship_manuscript_builder.py`:
   - Aggregates all verified JSON summaries (`r136`, `r137`, `r139`, `r141`, `r144`, `r156`, `r168`, `r173`, `r178`, `r183`) deterministically.
   - Generates **3 publication-grade matplotlib figures** (300 DPI PNG + vector PDF/SVG, clean typography, colorblind-safe palette):
     - `fig1_mortality_poverty_forest.{pdf,svg,png}`: Paired MI+OH vs. NY+PA forest plot of Q4/Q1 poverty crude RRs (90% CIs) and E-value sensitivity bounds across all 11 mortality causes.
     - `fig2_bym2_shrinkage_spatial.{pdf,svg,png}`: Raw SMR IQR vs. validated BYM2 (`B3`) smoothed RR IQR shrinkage + spatial mixing ($\phi$) across all 11 causes and both regions.
     - `fig3_methodological_pitfalls.{pdf,svg,png}`: 4-panel summary comparing naive vs. validated inference (HC3 vs. SCPC CI width, point ranks vs. KWW rank widths, within- vs. between-PUMA log-OR, nominal vs. RPP-adjusted state income spread).
   - Emits **2 LaTeX booktabs tables** (`table1_11cause_atlas.tex`, `table2_methodological_pitfalls.tex`) + Markdown equivalents.
   - Emits `manuscript.tex`, `manuscript.md`, `references.bib`, and runs `results_bundle(...)` + `verify_bundle(...)` on `studies_output/r188_flagship_manuscript/bundle/`.
2. `docs/studies/r188_flagship_manuscript.md`: Clean permanent manuscript copy linked in `docs/studies/`.
3. `tests/test_round188.py` & `docs/audits/round188_compatibility.md`: Verifies all 3 figure sets exist (PDF/SVG/PNG), both `.tex` tables have balanced booktabs environments, `references.bib` is non-empty, and `verify_bundle` returns `ok: true` with 0 errors.

## 4. Acceptance Gates
1. `scripts/r188_flagship_manuscript_builder.py` exits `0` offline.
2. `verify_bundle("studies_output/r188_flagship_manuscript/bundle")` exits with `ok: true`, `errors: []`.
3. `pytest -q tests/test_round188.py` passes with 0 failures.

## 5. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Built `scripts/r188_flagship_manuscript_builder.py`, generated all 3 PDF/SVG/PNG figures, 2 booktabs `.tex`/`.md` tables, `manuscript.tex`, `manuscript.md`, `references.bib`, permanent `docs/studies/r188_flagship_manuscript.md`, and verified `studies_output/r188_flagship_manuscript/bundle` via `verify_bundle` and `tests/test_round188.py`.

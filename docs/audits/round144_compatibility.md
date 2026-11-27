# Round 144 Compatibility Audit (`v0.139.0`)

- **Scope:** Pre-registered WONDER 2018–2022 county heart disease & drug overdose mortality BYM2 (`B3`) disease mapping (`census.disease_mapping.disease_map`) and Quantitative Bias Analysis (`census.bias_analysis.e_value`) study across MI/NY and OH/PA.
- **Data Governance:** Uses local manual CDC WONDER exports only; zero automated WONDER access; counties with suppressed (<10) counts excluded and zero raw sub-national 1–9 counts emitted.
- **Backward Compatibility:** Additive study script, report, and unit test only; zero modifications to `census/` library modules or manifest schemas.
- **Review Note:** Author self-review, not independent.

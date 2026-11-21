# Round 69 plan: replication D (Monnat 2018, county drug-related mortality)

**Goal.** The last shortlisted target (`docs/studies/replication_shortlist.md`; N44, N45): an association across
the national county geometry with suppressed counts. Version 0.65.0. Branch `phase69/monnat`. Criterion before any
association is computed.

## Target (verified from the NIH author manuscript, `literature_pdfs/nihms-979496.pdf`)

Appendix Table D.2: sensitivity models with ACS 2010–2014 covariates, spatial error, state fixed effects and
standardized covariates. The outcome is ln(age-adjusted drug-related mortality, 2006–2015); coefficients are 100 ×
β (≈ % per SD).
- **Model 4 (primary):** complete cases (counties with ≥ 10 deaths, n = 2,484). Economic distress index 9.62
  (SE 1.47).
- **Model 3:** all 3,106 counties, with suppressed rates multiply imputed. Economic distress index 12.55 (SE 1.60).
- Other Model 4 coefficients are reported beside ours, with no rule: family distress 8.73 (1.22), rent > 30%
  3.31 (1.08), vacant 2.79 (1.11), mining 12.77 (3.69), public sector −7.37 (2.29).

## Data

- **Deaths:** owner's WONDER Part G exports (multiple cause, Appendix Table A.1 codes, 2006–2015). These give
  county deaths, population and age-adjusted rates (2000 standard), and the national age × sex rates.
- **ACS 2010–2014** county tables:
  - **Economic distress components:** poverty 25–54 (B17001); unemployed or not in the labour force 25–54
    (B23001); disability 18–64 (B18101; the ACS has no work-disability item, a stated substitute); < 4-year degree
    25+ (B15002); SSI (B19056); public assistance (B19057); Gini (B19083); uninsured 18–64 (B27001);
  - housing: vacant (B25002), rent ≥ 30% of income (B25070);
  - family: separated or divorced 15+ (B12001), single-parent families with children (B11003);
  - population: moved from another county (B07003), age 65+ (B01001), veterans (B21001), non-Hispanic Black,
    Hispanic and American Indian (B03002).
- **Indices:** the paper's CFA loadings (Appendix Table F.1) applied to the standardized components, then
  standardized.
- **Non-ACS covariates:**
  - ERS 2015 county economic types and 2013 metro status (ERS GIS portal). The paper used the ERS typology
    edition with "services", which is not available; the 2015 edition has "recreation" instead (stated
    difference);
  - social capital from County Business Patterns 2012 per 10,000 (religious 813110; membership 8134 + 8139;
    sports 713910 + 713940 + 713950), as quartiles.
- **Omitted, as stated:** nonprofit organizations (NCCS) and the health-care environment (AHRF: physicians,
  shortage areas). In the paper's models these were small or not significant.
- **Exclusions as in the paper:** Alaska, Hawaii, Loving TX, Broomfield CO, Bedford City VA.

## Models

- **Primary (Model 4 analogue):** counties with an unsuppressed age-adjusted rate. ln(AAMR) on all covariates
  above plus state fixed effects. Spatial error model, ML (`spatial_regression(model="error")`), queen contiguity
  on 2014 cartographic county boundaries; islands dropped.
- **Secondary (Model 3 analogue, descriptive):** all counties, interval-censored NB2 counts with the expected
  deaths from national age × sex rates (`fit_model(model="negbin", censored=...)`). Coefficient 100 × β. This is a
  different estimator from the paper's imputation.

## Rule (primary, economic distress coefficient)

- **Replicated:** same sign, our 90% interval contains 9.62, and our estimate ÷ 9.62 lies in [0.67, 1.5].
- **Partly replicated:** the sign matches.
- **Not replicated:** otherwise.

## Simulation S (national county geometry)

- β coverage of the spatial error ML model on the same queen weights, with spatially correlated x.
- y = 1 + .5x + u, u = (I − λW)⁻¹ε, λ ∈ {.3, .55}; x from the same SAR at ρ = .5.
- 1,000 draws per cell. Pass ≥ .86 in both cells.
- If S fails, the primary interval is labelled not validated in the report; the rule does not change.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Data and criterion | done | counts match the paper (3,106; 2,484); criterion `20a4c13` |
| S run | done | .908 / .881: passes |
| Result | done | replicated: 9.95 vs 9.62 |
| Report, tests | done | `r69_replication_monnat.md`; 1 test |
| Goldens, final suite | done | identical; 2163 passed, 37 skipped |
| Exceptions | none | first run stopped by a shell timeout; rerun unchanged |

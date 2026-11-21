# Round 69 criterion: replication D (Monnat 2018) and simulation S

Committed before any association between drug-related mortality and a covariate was computed, and before the full
simulation. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/r69_monnat_replication.py` and `scripts/r69_county_sem_validation.py`;
- `census/spatial.py`, `census/missing_censored_its.py`, `census/count_repairs_core.py`;
- this file.

The ERS extract is pinned by SHA-256 `58a41927…f96d51bdeef`. The WONDER exports are the owner's Part G files,
checked for structure only: the 126 Appendix Table A.1 codes, years 2006–2015, county and national age × sex.

**Seen before this commit:**
- counts only (`--build-only`): 3,106 counties after the paper's exclusions (paper: 3,106); 2,484 counties with at
  least 10 deaths (paper's Model 4: 2,484); 556 suppressed;
- WONDER withholds the age-adjusted rate when deaths ≤ 20 (472 of the unsuppressed counties);
- one 4-draw smoke run of S.

No coefficient, correlation or rate comparison was computed.

## Target (NIH author manuscript, Appendix Table D.2, Model 4)

Spatial error model, state fixed effects, ACS 2010–2014 covariates, complete cases (counties with ≥ 10 deaths,
n = 2,484). The outcome is ln(age-adjusted drug-related mortality rate, 2006–2015); coefficients are 100 × β for a
one-SD change.
- **Economic distress index: 9.62 (SE 1.47).** This is the judged coefficient.
- Reported with no rule: family distress 8.73 (1.22); rent > 30% 3.31 (1.08); vacant 2.79 (1.11); mining
  12.77 (3.69); public sector −7.37 (2.29).

## Our specification (differences from the paper stated)

- **Outcome:** 100 × ln(deaths / expected deaths) for the 2,484 counties with ≥ 10 deaths.
  - Expected deaths = Σ over age × sex of the national 2006–2015 rate (owner's national file) × the county's ACS
    2014 age × sex share × the county's WONDER person-years.
  - This is an indirectly standardized rate. The paper used WONDER's directly age-adjusted rate, which WONDER no
    longer reports for counties with ≤ 20 deaths.
- **Economic distress index:** the paper's CFA loadings (Appendix Table F.1) times the standardized ACS 2010–2014
  components, then standardized:
  - poverty 25–54 (B17001);
  - unemployed or not in the labour force 25–54 (B23001, civilian);
  - **any disability 18–64** (B18101; the ACS has no work-disability item);
  - < 4-year degree 25+ (B15002);
  - SSI (B19056) and public assistance (B19057) households;
  - Gini (B19083);
  - uninsured 18–64 (B27001).
- **Family distress index:** loadings .728 × the standardized separated-or-divorced 15+ (B12001) and single-parent
  share of families with own children (B11003).
- **Other covariates, standardized:**
  - vacant units (B25002) and rent ≥ 30% of income (B25070);
  - moved from another county, state or abroad **in the past year** (B07003; the ACS has no 5-year mobility
    item);
  - age 65+ (B01001) and veterans (B21001; veterans only, as in the paper's ACS model).
- **Quartile dummies:**
  - non-Hispanic Black, Hispanic and non-Hispanic American Indian shares (B03002);
  - CBP 2012 religious (813110), membership (8134, 8139) and sports (713910, 713940, 713950) establishments per
    10,000.
- **Typology:** ERS **2015** economic types (farming, mining, manufacturing, government, recreation;
  nonspecialized reference), where the paper's edition had "services" instead of "recreation"; and 2013
  nonmetro status.
- **Omitted:** nonprofit organizations (NCCS) and the health-care environment (AHRF physicians, shortage areas).
- **State fixed effects.**
- **Model:** spatial error ML (`spatial_regression(model="error")`), queen contiguity on 2014 cartographic counties
  among the analysis counties, islands dropped. Interval: model-based 90%.

## Rule (economic distress coefficient)

- **Replicated:** estimate > 0, our 90% interval contains 9.62, and estimate ÷ 9.62 lies in [0.67, 1.5].
- **Partly replicated:** estimate > 0.
- **Not replicated:** otherwise.

## Secondary (descriptive, no rule)

- The same model with 100 × ln(published AAMR) on the counties with > 20 deaths.
- All 3,106 counties with interval-censored NB2: counts hidden as 1–9 enter as intervals, exposure = expected
  deaths, same covariates. Coefficient 100 × β, beside Model 3's 12.55; this is a different estimator from the
  paper's multiple imputation.

## S: spatial error slope coverage on national counties

- Queen weights for the 48 contiguous states and DC (minus the three excluded counties, islands dropped).
- x = (I − .5W)⁻¹z; y = 1 + .5x + (I − λW)⁻¹e, λ ∈ {.3, .55}; spreg `ML_Error`, 90% normal interval.
- 1,000 draws per cell; seeds `[20281101 + cell, draw]`. **Pass:** coverage ≥ .86 in both cells.
- If S fails, the report labels the primary interval as not validated. The rule above does not change.

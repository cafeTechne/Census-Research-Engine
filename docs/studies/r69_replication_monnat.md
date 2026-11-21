# Replication D: county economic distress and drug-related mortality (Monnat 2018)

**Status: registered association replication (criterion `20a4c13`). Author self-review, not independent.**
Audits: `docs/audits/r69_monnat_replication.md` (replication) and `docs/audits/r69_county_sem_validation.md`
(simulation S).

## Target

Monnat SM (2018), "Factors Associated With County-Level Differences in U.S. Drug-Related Mortality Rates",
*Am J Prev Med* 54(5):611–619. The target values were verified from the NIH author manuscript's appendices:
- **Appendix Table A.1:** the ICD-10 list. A death counts when any of its causes is listed (multiple cause), and
  drug homicide (X85) is excluded.
- **Appendix Table D.2, Model 4:** ACS 2010–2014 covariates, spatial error, state fixed effects, the 2,484
  counties with at least 10 deaths. The economic distress index is 9.62 (SE 1.47) per SD (≈ % change in the
  age-adjusted rate).

## Data

- **Deaths:** the owner's manual WONDER exports (Multiple Cause of Death 1999–2020, 2006–2015, the 126 Table A.1
  codes, county and national age × sex). Our counts match the paper exactly: 3,106 counties after its exclusions,
  and 2,484 with at least 10 deaths.
- **Covariates:**
  - ACS 2010–2014 county tables, with the paper's factor loadings for the economic and family distress indices;
  - ERS 2015 county economic types and 2013 metro status;
  - County Business Patterns 2012 social-capital counts.

## Result: replicated

| Covariate | Published (SE) | Ours (90% CI) | Ratio |
| :--- | :--- | :--- | ---: |
| **Economic distress index (judged)** | **9.62 (1.47)** | **9.95 (7.77 to 12.12)** | **1.03** |
| Family distress index | 8.73 (1.22) | 8.10 (6.47 to 9.73) | 0.93 |
| Rent > 30% of income | 3.31 (1.08) | 1.47 (0.17 to 2.77) | 0.44 |
| Vacant housing | 2.79 (1.11) | 0.82 (−0.90 to 2.55) | 0.29 |
| Mining-dependent | 12.77 (3.69) | 4.91 (−0.01 to 9.83) | 0.38 |
| Public sector (government)-dependent | −7.37 (2.29) | −9.03 (−12.43 to −5.64) | 1.23 |

2,459 counties entered the spatial model: 24 counties without contiguous neighbours were dropped. λ = 0.52.

**Simulation S** checked the spatial error model's slope interval on this national county geometry. It covered
.908 at λ = .3 and .881 at λ = .55, so the interval above is validated for this design.

## Secondary results (descriptive)

- **Published age-adjusted rates** (counties with > 20 deaths, n = 2,047): economic distress 12.92 (10.70 to
  15.14). Larger, as expected when the smallest counties drop out.
- **All 3,105 counties, interval-censored NB2** (556 suppressed counts used only as "between 1 and 9"): 14.69
  (12.14 to 17.24), beside the paper's Model 3 (multiple imputation) 12.55. This is a different estimator, so the
  comparison is only indicative.

## Differences from the paper, all fixed before the run

- **Outcome:** an indirectly age-standardized rate (deaths / expected). WONDER no longer reports age-adjusted
  rates for counties with 20 or fewer deaths.
- **Substitute ACS items:**
  - "any disability 18–64" for the work-disability item;
  - past-year mobility for 5-year mobility.
- **Typology:** ERS 2015 economic types instead of the paper's edition (which had "services" where 2015 has
  "recreation"). This is the likely reason the mining coefficient is smaller.
- **Omitted:** nonprofit organizations and the health-care environment.

## What this establishes

With public data and the owner's manual WONDER exports, the engine reproduces the paper's headline county
association. A one-SD increase in economic distress goes with about 10% higher drug-related mortality, holding
family distress, housing, labour market, social capital, demographics and state constant. This is the first
replication on the national county geometry, and the first using the engine's suppressed-count handling.

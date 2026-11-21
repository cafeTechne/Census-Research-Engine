# Replication shortlist (Round 65, for owner approval)

**Status: proposal. Nothing is registered until the owner chooses the set. Author self-review, not independent.**
Drafted 2026-11-20 for backlog issues N44 (validation rests on two county geometries) and N45 (no registered study
uses a method added after Round 30).

## Why pair replications with simulations

A replication shows whether the engine reproduces a published answer from the same public data: extraction,
variable choice, derived measures and the model. It cannot show whether our intervals are honest on that geography,
because a single real dataset has no known true value. So each replication comes with a simulation on its own
geometry, reusing the existing generators.

## Rule for "replicated" (fixed before any run; per target, in the registration)

- **Numeric checks (A, B):** a target passes when our 90% interval contains the published value in at least 90% of
  units, and the median absolute difference is within a tolerance stated in advance. Each tolerance reflects known
  method differences: CHR's group definitions, and PUMS top-coding against Census internal microdata.
- **Associations (C, D, E):** a target passes when all three hold:
  1. our estimate has the same sign;
  2. our 90% interval contains the published point estimate;
  3. the ratio of our estimate to theirs lies between 0.67 and 1.5.
  
  "Partly replicated" means the sign matches but condition 2 or 3 fails. "Not replicated" means the sign differs or
  the interval contains zero.

## Candidates

| | Target | Published finding | Our data spec | Geometry tested | Engine route | Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A | County Health Rankings 2025, "Residential segregation – Black/White" | County dissimilarity index (0–100) from ACS 2019–2023 tract counts; counties with ≥ 100 Black residents (about 65% of counties) | ACS 2019–2023 tract race counts (B03002, assuming CHR uses non-Hispanic groups; to verify in CHR's technical notes) | All US counties, incl. GA/TX (many small counties) and large Western counties | manifest `segregation` (naive D to match CHR; bias-corrected D reported beside it) | CHR data file (already a registered source) |
| B | Census-published Gini index (B19083) | State household-income Gini with MOE, 2019–2023 five-year | 2019–2023 PUMS household income (HINCP), household weights and 80 replicates | 50 states + DC | `test_association(kind="inequality")` | Census API / PUMS |
| C | Mitchell et al. 2022, *Family & Community Health* 45(2):77–90, NC tract life expectancy and ICE ([accepted manuscript, NSF PAR](https://par.nsf.gov/biblio/10394037)) | Log life expectancy on ICE Income: OLS slope 0.13 (adjusted R² 48.19%); spatial error model 0.12 (pseudo R² 53.40%); ICE Race 0.045 (OLS); ICE Income + Race 0.13; 1,970 NC tracts | USALEEP 2010–2015 tract life expectancy; ACS 2014–2018 B19001 (households < $25k vs ≥ $100k), B19001B/B19001H (Black < $25k vs non-Hispanic White ≥ $100k), B03002 | NC tracts (100 counties): first tract-level and first southern geometry | `fit_model` (OLS, SCPC), `spatial_regression` (error model), ICE derived with replicate MOEs | Open accepted manuscript |
| D | Monnat 2018, *Am J Prev Med* 54(5):611–619, county drug mortality ([PMC author manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC6080628/)) | Spatial error model with state fixed effects, 3,106 counties: an SD of economic distress → +6.4% in age-adjusted drug mortality (2000 covariates). Appendix Table D.2 Model 3 with ACS 2010–2014 covariates: 12.55 (SE 1.60) (verified 2026-11-20 from the author manuscript) | CDC WONDER multiple-cause drug deaths 2006–2015 by county (**your manual export**; 20% of counties suppressed). ACS 2010–2014: an 8-item distress index (poverty, unemployment/not in labour force, work disability, no 4-year degree, SSI, public assistance, Gini, uninsured) | All US counties except AK/HI | `fit_model` NB2 with `censored` (hidden counts) and SCPC; the published log-rate model for comparison | Open author manuscript; needs your WONDER export |
| E | Boing et al. 2020, *PNAS* 117(30):17688–17694, tract/county/state variance in life expectancy | 70.4% of geographic variation at tract level, 19.0% state, 10.7% county; 65,662 tracts | Probably USALEEP and ACS tract covariates (not confirmed) | All US tracts | `multilevel_model` (three levels; support to check) | **Not open access** (Europe PMC); only if you supply the PDF |

## Matching simulations (Round 66+)

| Target | Simulation |
| :--- | :--- |
| A | Round 52/57 segregation design on GA and TX tract geometry. Checks whether county noise gates hold where counties are small |
| B | None needed beyond Round 56 (PUMS designs do not depend on geography) |
| C | Round 58 SCPC and Round 35 spatial-error designs on NC tract geometry (1,970 units). This is the first tract-level test of SCPC and the spatial-error model |
| D | Round 45 censored-NB2 and Round 58 SCPC designs on national county geometry |
| E | Multilevel coverage with three nested levels, if E is chosen |

## Recommendation

Start with **A, B and C**: they need no new data access, and between them they cover counties nationally, PUMS and
a tract geometry. Add **D** when you can export the WONDER file (one export, 2006–2015, multiple cause of death,
county level, drug codes as in the paper's Appendix A). Include **E** only if you want to supply the PDF.

## Open checks before registration

- A: CHR's exact group definitions and whether its D uses all tracts or excludes empty ones.
- D: resolved 2026-11-20 from the author manuscript (Appendix Tables A.1 and D.2): the ICD-10 list (any cause, no X85) and Model 3's 12.55 (1.60).
- C: the USALEEP release used. The paper cites the 2010–2015 NCHS estimates, so the outcome period differs from the
  ACS period (2014–2018). We follow the paper.

Sources: [CHR measure page](https://www.countyhealthrankings.org/health-data/community-conditions/social-and-economic-factors/safety-and-social-support/residential-segregation-blackwhite);
[Mitchell et al. 2022](https://par.nsf.gov/biblio/10394037); [Monnat 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6080628/);
[Boing et al. 2020 press release](https://news.harvard.edu/gazette/story/2020/07/disparities-in-life-expectancy-found-at-census-tract-level/);
[Census B19083](https://censusreporter.org/tables/B19083/).

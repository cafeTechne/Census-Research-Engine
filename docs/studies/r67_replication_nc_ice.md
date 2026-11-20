# Replication C: North Carolina tract life expectancy and the Index of Concentration at the Extremes

**Status: registered association replication (plan `e75a41b`; criterion text `14b78b2`, see deviation 2). Author
self-review, not independent.** Audits: `docs/audits/r67_nc_ice_replication.md` (replication) and
`docs/audits/r67_nc_tract_validation.md` (simulation S).

## Target

Mitchell, Runkle, Andersen, Shay and Sugg (2022), "Inequalities in Life Expectancy Across North Carolina",
*Family & Community Health* 45(2):77–90 ([accepted manuscript](https://par.nsf.gov/biblio/10394037)). The paper
regresses log tract life expectancy (USALEEP 2010–2015) on three Index of Concentration at the Extremes (ICE)
measures from ACS 2014–2018, across 1,970 NC tracts, with OLS and a spatial error model (Table 3).

## Result: partly replicated (5 of 6 slopes)

| ICE | Model | Published | Ours (90% CI) | Ratio | Replicated |
| :--- | :--- | ---: | :--- | ---: | :--- |
| Race | OLS | 0.045 | 0.0454 (0.0420–0.0489) | 1.01 | yes |
| Race | spatial error | 0.054 | 0.0540 (0.0496–0.0585) | 1.00 | yes |
| Income | OLS | 0.13 | 0.1260 (0.1207–0.1312) | 0.97 | yes |
| Income | spatial error | 0.12 | 0.1219 (0.1161–0.1277) | 1.02 | yes |
| Income + Race | OLS | 0.13 | 0.1465 (0.1402–0.1527) | 1.13 | no (interval misses 0.125–0.135) |
| Income + Race | spatial error | 0.13 | 0.1418 (0.1345–0.1490) | 1.09 | yes |

We analysed 1,971 tracts (paper: 1,970). Adjusted R² agrees exactly for ICE Race (19.60%) and ICE Income (48.19%);
for Income + Race it is 45.13% against 45.07%.

## Reading the result

- **Same data, same answer.** For ICE Race and ICE Income the engine reproduces the paper's slopes and R² to the
  printed digit, from public USALEEP and ACS files.
- **The one miss is a definition question.** The combined index is the only measure whose R² differs, and the OLS
  slope is 13% larger. The paper's Table 1 lists the income cut-points and the race-specific tables. Its text
  defines the combined index over "total population", while the households total (B19001) is the standard ICE
  denominator; we pre-registered the households total. A different denominator would move the slope by about this
  much. The pre-set rule counts the slope as not replicated. We did not try other definitions after seeing the
  result.
- **Spatial dependence.** Simulation S shows that on NC tract geometry:
  - HC3 intervals are far too narrow when the fields correlate (coverage .12–.26 at 20–100 km);
  - SCPC holds at 0–20 km (.91–.94) but under-covers at 100 km (.75 at ρ̄ .05).
  
  By the pre-set rule, the OLS intervals above are HC3, so they are too narrow. That makes the overlap rule
  stricter, not easier. The spatial error model's λ was .37–.61.
- **Sampling error in ICE barely matters here.** The EIV-corrected slopes are close to the naive ones (Income
  0.133, Race 0.046).

## Engine change

Tract-level SCPC is now exploratory (`validated: false` with a note), because simulation S failed at 100 km on NC
tracts. County-level SCPC is unchanged.

# Round 67 plan: replication C (North Carolina tract life expectancy and ICE)

**Goal.** Replication target C, chosen by the owner on 2026-11-20 (`docs/studies/replication_shortlist.md`; N44,
N45). This is the first registered association replication, the first tract-level geometry and the first southern
state. Version 0.63.0. Branch `phase67/nc-ice`. Criterion before any association is computed.

## Target

Mitchell, Runkle, Andersen, Shay and Sugg (2022), *Family & Community Health* 45(2):77–90 (NSF PAR accepted
manuscript), Table 3:
- log tract life expectancy on each Index of Concentration at the Extremes (ICE) separately, across 1,970 NC
  tracts;
- OLS slopes: ICE Race 0.045, ICE Income 0.13, ICE Income + Race 0.13 (adjusted R² 19.60%, 48.19%, 45.07%);
- spatial error model (GeoDa): 0.054, 0.12, 0.13.

## Data (as in the paper)

- **Outcome:** USALEEP 2010–2015 `e(0)` for NC (every tract with a value), on 2010 tracts.
- **Covariates:** ACS 2014–2018 tracts (2010 tracts):
  - ICE Income = (B19001 households ≥ $100k − households < $25k) / B19001 total;
  - ICE Race = (B03002 non-Hispanic White − non-Hispanic Black) / B03002 total;
  - ICE Income + Race = (B19001H ≥ $100k − B19001B < $25k) / B19001 total.
- Tracts with no population or no life expectancy are excluded; the paper reports 1,970.

## Models and rule

- OLS of ln(e0) on each ICE. The interval is SCPC (ρ̄ .05) if simulation S validates it on NC tracts; otherwise
  HC3 (pre-set).
- Spatial error model with queen contiguity (2018 cartographic tract boundaries), ML, engine
  `spatial_regression(model="error")`; model-based interval.
- **Per slope (6), replicated if all three hold:**
  1. same sign;
  2. our 90% interval overlaps the published value's rounding interval (± half a unit of the last published
     digit);
  3. our estimate ÷ published lies in [0.67, 1.5].
- **Overall:** "replicated" if all six slopes replicate; "partly replicated" if all signs match.
- Adjusted R² is reported against the published value (descriptive).
- **Secondary (descriptive):** EIV-corrected slopes for ICE Income and ICE Race, using the 2018 VRE files B19001
  and B03002; B19001B/H have none.

## Simulation S (NC tract geometry)

- 1,970 tract centroids. Round 22/58's linear field generator with error-free x (target .5), at ranges
  {0, 20, 100} km.
- Procedures: OLS slope with SCPC ρ̄ .05 and .10, and HC3. 2,000 draws per cell; seeds `[20281001 + cell, draw]`.
- SCPC (per ρ̄) is validated on NC tracts if it covers ≥ .86 in every cell.

## Engine and docs

- No method change unless S fails for SCPC. In that case `fit_scpc` notes that it is untested at tract density.
- Report `docs/studies/r67_replication_nc_ice.md`; STATUS, CHANGELOG, version, compatibility audit, tests;
  goldens byte-identical.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Data and criterion | | |
| S run | | |
| Replication result | | |
| Report, tests | | |
| Goldens, final suite | | |
| Exceptions | | |

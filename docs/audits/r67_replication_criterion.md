# Round 67 criterion: replication C (NC tract life expectancy and ICE) and simulation S

Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/r67_nc_ice_replication.py`, `scripts/r67_nc_tract_validation.py` and
  `docs/audits/nc_tract_geometry.json`;
- `census/scpc.py`, `census/scpc_core.py`, `census/spatial.py`, `census/models.py` and the Round 22 generator;
- this file.

## Deviation 2: this file was a placeholder at the first criterion commit

At commit `daa1d15` this file held only a placeholder line, because a tool error kept the drafted text from being
written. S ran against `daa1d15`. Its rule had been committed before the run in two places:
- the plan (`PLAN_ROUND_67.md`, commit `e75a41b`): "SCPC (per ρ̄) is validated on NC tracts if it covers ≥ .86 in
  every cell";
- the frozen script's docstring.

S's result was:

| Range | SCPC .05 | SCPC .10 | HC3 |
| ---: | ---: | ---: | ---: |
| 0 km | .9145 | .9240 | .9095 |
| 20 km | .9240 | .9380 | .2625 |
| 100 km | .7535 | .8145 | .1215 |

The text below is the criterion as drafted before S ran, unchanged except for this section. It is committed
**before any association between life expectancy and ICE has been computed**. Replication C runs against this
commit.

**What was looked at before replication C:**
- the data build, as counts only: 1,971 analysis tracts against the paper's 1,970, and no missing ICE values;
- one 20-draw smoke run of S;
- S's result above.

No slope, correlation or R² was computed.

## Target

Mitchell, Runkle, Andersen, Shay and Sugg (2022), *Family & Community Health* 45(2):77–90, Table 3. The
dependent variable is log life expectancy. Each ICE enters separately.

| ICE | OLS estimate | OLS adjusted R² | Spatial error estimate |
| :--- | ---: | ---: | ---: |
| Race | 0.045 | 19.60% | 0.054 |
| Income | 0.13 | 48.19% | 0.12 |
| Income + Race | 0.13 | 45.07% | 0.13 |

## Our specification

- **Outcome:** USALEEP 2010–2015 `e(0)`, NC A file, including tracts whose life table is fully predicted (the paper
  kept every tract with an estimate); ln(e0).
- **ICE** (ACS 2014–2018, 2010 tracts; Krieger's definitions as listed in the paper's Table 1):
  - Income = (B19001 014–017 − 002–005) / 001, i.e. households ≥ $100k minus households < $25k, over all
    households;
  - Race = (B03002 003 − 004) / 001, i.e. non-Hispanic White minus non-Hispanic Black, over total population;
  - Income + Race = (B19001H 014–017 − B19001B 002–005) / B19001 001.
- **Exclusions:** tracts with zero population, zero households or no `e(0)`.
- **OLS interval:** SCPC with ρ̄ .05 if S validates it on NC tracts; otherwise HC3. S did not validate it, so HC3
  applies.
- **Spatial error model:** the engine's `spatial_regression(model="error")` (spreg ML) with queen contiguity on
  2018 cartographic tracts. Tracts without neighbours (islands) are dropped from this model only, and their number
  is reported.

## Rule

**Per slope (3 ICE × 2 models), replicated if all three hold:**
1. the estimate has the same sign as the published one;
2. our 90% interval overlaps the published value ± half a unit of its last printed digit (0.045 → ±.0005;
   0.13 → ±.005);
3. our estimate ÷ the published estimate lies in [0.67, 1.5].

**Overall:** "replicated" when all six slopes replicate; "partly replicated" when all six signs match; otherwise
"not replicated". Adjusted R² is reported beside the published value, with no rule.

**Secondary (descriptive):** EIV-corrected slopes for ICE Income and ICE Race from the 2018 VRE files B19001 and
B03002. ICE Income + Race has no replicate files (B19001B/H).

## S: SCPC on NC tract geometry

- All 2,192 NC tract representative points; Round 22's linear generator (x and error fields with exponential
  covariance at the cell's range; y = 1 + .5x + error; target .5).
- Ranges {0, 20, 100} km; 2,000 draws per cell; seeds `[20281001 + cell, draw]`.
- Procedures: SCPC ρ̄ .05 and .10, and HC3.
- **SCPC passes** (per ρ̄) when it covers ≥ .86 in every cell.
- **If ρ̄ .05 fails,** the replication uses HC3 for OLS, and the engine notes that SCPC is untested at tract density.

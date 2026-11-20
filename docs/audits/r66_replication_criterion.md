# Round 66 criterion: numeric replications A and B, simulation S

Committed before any comparison with a published value and before the full simulation. Author self-review, not
independent. Frozen with `validate_pins`:
- `scripts/r66_numeric_replication.py`;
- `scripts/r66_segregation_geometry_validation.py` and the Round 50/52 scripts it imports;
- `scripts/r66_segregation_counts.py` and its output `docs/audits/segregation_r66_counts.csv.gz`;
- `census/segregation.py`, `census/pums_inequality.py`, `census/pums_inequality_core.py`;
- this file.

The inputs were downloaded beforehand (`scripts/r66_fetch.py`), and no comparison was computed. The CHR county
values were read once to confirm their format (header and three rows), not compared.

## A. CHR 2025 "Residential Segregation – Black/White" (county dissimilarity, 0–100)

**Published values.** `measure_datasets/v141_r2025.csv` from CHR's own calculation repository
(`countyhealthrankings/county_health_measure_calculations`, commit `a516395`, SHA-256 `2c737ea8…05636fe`).

**CHR's definition, read from its code** (`calculations/v141_residential_segregation.qmd`):
- ACS 2019–2023 tract counts from B11002 (population in households): Black = `B11002B_001E` (Black alone) and
  White = `B11002A_001E` (White alone, Hispanic included; the code comment says "not Hispanic", but the table it
  pulls is A, not H);
- D = 50 Σ |bᵢ/B − wᵢ/W| over the county's tracts;
- counties with B < 100 are missing, and so are counties where D equals 0;
- Suffolk and Ulster (NY) are suppressed;
- Connecticut is reported on the old counties through a tract crosswalk.

**Our values.** The same tables, tracts and rules through the engine's API client and its index function
(`census.segregation._indices`). A county with a missing tract value is missing, as in CHR's code. Connecticut is
excluded: the 2023 ACS uses planning regions, and CHR's crosswalk file is not public.

**Replicated if** the median absolute difference over counties both sides report is ≤ 0.5 points **and** at least
90% of them are within 1.0 point. With identical inputs we expect near-exact agreement; any county more than 2
points apart is listed.

**Interval part (descriptive, no pass/fail).** B11002A/B have no Census replicate files, so the replicate
intervals use the engine's standard definition instead: B03002 non-Hispanic Black alone (004) against
non-Hispanic White alone (003), with VRE replicates for GA, TX, AZ, MI and NY. We report:
- how many counties the noise gates validate;
- the bias-corrected D beside CHR's value.

This is a different definition (all persons, non-Hispanic), so no agreement rule applies.

## B. Census state Gini index (B19083, households)

**Published values.** `B19083_001E` and `_001M`, ACS 2019–2023, for 12 states fixed here: WY, VT, DE, NM, MS, AZ,
GA, MI, NY, TX, CA, NC.

**Our values.**
- 2019–2023 PUMS housing records: households only (`TYPEHUGQ` = 1, `NP` > 0), income `HINCP` × `ADJINC` / 10⁶,
  weight `WGTP` with its 80 replicates;
- `pums_inequality` Gini with its validated 90% interval;
- primary analysis: negative incomes set to 0. The engine refuses negatives, and the Census treatment is not
  documented in what we read;
- secondary analysis (reported, not judged): negative incomes dropped.

**Replicated if** the median |difference| over the 12 states is ≤ .005 **and** the 90% interval contains the
published value in at least 10 of 12 states.

**Expected direction, stated in advance:** PUMS top-codes high incomes and is a subsample, so our Gini may be
slightly lower. A miss explained only by that bias is reported as "not replicated (top-coding)". The rule does not
change after the run.

## S. Segregation coverage on GA, TX and AZ county geometry

- Round 52's frozen observation model and judging rules on 2019–2023 tract counts of GA (159 counties), TX (254)
  and AZ (15). Designs: black/nonblack (B03002) and below/above poverty (B17001) per state.
- Two rho cells (0, −.3); 2,000 draws per cell; per-draw seeds `[20280901 + cell, draw]`.
- **Pass:** for each two-group procedure the engine validates (bias-corrected D, isolation and H), every judged
  noise bin inside its current validated range passes in every design.
- **A failure** gives the engine a geometry note for that procedure and range; earlier MI/NY and OH/PA results
  stand.

## Smoke run

One 20-draw smoke run of S checked that the script runs. It is not judged.

## Deviation 1 (before any outcome was seen)

The first run (criterion `dd48bf6`) stopped in A's descriptive interval part. One county had a replicate refit
with an undefined index (a group total of zero in a replicate), which raised `IncompleteReplicatesError`. The run
wrote nothing to the audit. It did write the per-county comparison file just before stopping; that file was not
opened, and it is overwritten by the rerun.

Fix: the interval part now runs county by county and lists the counties that fail. Nothing else changed: A's and
B's rules, inputs and comparison code are the same. The rerun uses the commit that records this deviation.

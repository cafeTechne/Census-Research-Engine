# Round 52 exploratory example: race/ethnicity segregation and the 2019–2024 change in poverty segregation, MI/NY

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r52_segregation_groups_example.py` reads cached tract VRE files with HTTP blocked:
- 2024 B03002 for MI and NY, downloaded to the cache for this round;
- B17001 for 2015–2019 (2010 tracts) and 2020–2024 (2020 tracts).

It runs `census.segregation_replicate` with its defaults (bias-corrected; negative replicates clipped). Only
county rows are written. Outputs are archived at `/tmp/r52_example_outputs.tar.gz` (sha256
`d5f2bd6c…1e6e92ad`).

**Designs.**
- **Black vs non-Black:** B03002_004 against the sum of every other component.
- **Hispanic vs non-Hispanic:** B03002_012 against B03002_002.
- **Four groups:** non-Hispanic White, non-Hispanic Black, Hispanic, all other non-Hispanic (lines 005–009).
- **Poverty change:** below vs at or above poverty, 2024 minus 2019, per county (`segregation_test` with
  `release`/`compare_release`; independent samples, variances added).

## How many counties are validated (145 MI/NY counties)

| Design | Validated (H) | Infinite noise | Noise ≥ 1 (finite) | Clipped and noise ≥ .50 | Fewer than five tracts |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Black vs non-Black | 102 | 9 | 16 | 14 | 8 |
| Hispanic vs non-Hispanic | 126 | 1 | 0 | 11 | 8 |
| Four groups | 88 | 9 | 1 | 32 | 8 |

Before Round 52 none of these race designs had a validated county above noise .50, and the four-group index
was exploratory everywhere. Black–non-Black isolation (any finite noise level) validates 117 counties.

The largest single cause of unvalidated race rows is now **clipping**. A county with a negative replicate is
validated only below .50, because Round 51 tested clipping only there. B03002 has many negative replicates in
small cells, and race groups usually have noise above .50, so these counties stay exploratory. This is
recorded as backlog issue N30.

## Highest validated Theil H

| Design | County | H (90% CI) |
| :--- | :--- | :--- |
| Black vs non-Black | Wyoming County, NY (36121) | 0.519 (0.459–0.579) |
| Black vs non-Black | Wayne County, MI (26163) | 0.500 (0.487–0.513) |
| Black vs non-Black | Greene County, NY (36039) | 0.426 (0.373–0.479) |
| Hispanic vs non-Hispanic | Montgomery County, NY (36057) | 0.222 (0.183–0.260) |
| Hispanic vs non-Hispanic | New York County, NY (36061) | 0.217 (0.205–0.228) |
| Four groups | Wyoming County, NY (36121) | 0.225 (0.189–0.260) |
| Four groups | Chippewa County, MI (26033) | 0.202 (0.183–0.221) |

Several of the highest rural values are probably **group-quarters artefacts**: Wyoming, Greene and Chippewa
counties contain state or federal prisons, whose tracts hold most of the county's Black residents. Segregation
indices on household-plus-group-quarters counts describe that concentration correctly. It is not residential
segregation in the usual sense; a study would need to exclude group-quarters tracts or use a household universe.

## Poverty segregation, 2015–2019 to 2020–2024

| Index | Validated contrasts | 90% CI above zero | 90% CI below zero | Median change |
| :--- | ---: | ---: | ---: | ---: |
| D (bias-corrected) | 133 | 14 | 9 | +0.004 |
| H (bias-corrected) | 136 | 9 | 10 | +0.001 |

There is no general trend: changes are small and go both ways. The counts of intervals excluding zero are not
multiplicity-adjusted; about 13 of 133 would exclude zero by chance at 90%. The two releases use different
tract boundaries (2010 and 2020), so part of any change is a change of partition.

## Limits

- The race validation used 2024 MI/NY and OH/PA only. Within that, the engine applies one range to all group
  types: a bin counts only if every design judging it passed.
- Group quarters are not separated (see above).
- Clipped counties above noise .50 are not validated (N30).

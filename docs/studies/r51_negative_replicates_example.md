# Round 51 exploratory example: counties with negative replicate estimates

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r51_negative_replicates_example.py` reads the cached 2024 five-year tract VRE files for
B17001 and B19001 (MI and NY) with HTTP blocked, using the Round 50 example's loader. It keeps only the
counties that Round 50 refused because a tract had a negative replicate estimate, and runs
`census.segregation_replicate` with its defaults: bias-corrected indices and, since Round 51,
`negative_replicates="clip"`. Only county rows are written. The outputs are archived at
`/tmp/r51_example_outputs.tar.gz` (sha256 `9789ac82…2dfe69ee`).

**Comparison.** For each county the clipped result (all tracts) is compared with a naive workaround that
drops the affected tracts. Dropping changes the county being described, so it is shown for comparison only.

## Results

| Design | County | Clipped cells | Noise level | Index | Clipped: estimate (SE) | Validated | Drop tracts: estimate (SE) |
| :--- | :--- | ---: | ---: | :--- | :--- | :--- | :--- |
| Poverty | Albany (36001) | 6 | 0.34 | D | 0.403 (0.019) | yes | 0.401 (0.019) |
| Poverty | Bronx (36005) | 30 | 0.26 | D | 0.260 (0.014) | yes | 0.260 (0.014) |
| Poverty | Dutchess (36027) | 1 | 0.37 | D | 0.268 (0.027) | yes | 0.266 (0.027) |
| Poverty | Kings (36047) | 9 | 0.33 | D | 0.262 (0.019) | yes | 0.262 (0.019) |
| Poverty | Sullivan (36105) | 3 | 0.31 | D | 0.326 (0.036) | yes | 0.346 (0.035) |
| Income | Genesee (26049) | 2 | 0.23 | three-group H | 0.088 (0.008) | yes | 0.087 (0.008) |
| Income | Kalamazoo (26077) | 4 | 0.24 | three-group H | 0.073 (0.008) | yes | 0.072 (0.008) |
| Income | Wayne (26163) | 11 | 0.26 | three-group H | 0.101 (0.008) | yes | 0.100 (0.008) |
| Income | Bronx (36005) | 27 | 0.27 | three-group H | 0.062 (0.009) | yes | 0.061 (0.009) |
| Income | Kings (36047) | 8 | 0.27 | three-group H | 0.072 (0.009) | yes | 0.072 (0.009) |

Isolation and H for the five poverty counties behave the same way (all validated; the CSV has every row).

## Findings

- All ten county-designs that Round 50 refused are now estimated and validated: 137 of 145 MI/NY counties
  per design (Round 50: 132 of 140 estimated); the other eight have fewer than five populated tracts.
- Clipping touches few cells: 1 to 30 replicate values per county, out of 80 per tract and group. The
  income design has far fewer affected tracts than the band-level file (9 against 585 MI/NY tracts in B19001)
  because summing bands cancels most negative band replicates.
- Clipped SEs and the drop-tract SEs agree (median ratio 1.000). Point estimates agree in the large
  counties, but dropping two of Sullivan's 31 tracts moves its D from .326 to .346, larger than half its
  SE. That is why the engine clips instead of dropping tracts.

## Limits

- The Round 51 validation used Gaussian replicates, which produce negative counts far more often than the
  real files. The real files' negatives come from the Census Bureau's replicate weighting, which was not
  modelled.
- Naive isolation and H failed with clipped cells; only the bias-corrected defaults are validated there.
- Poverty and income groups only; race and ethnicity groups are Round 52 (N21).

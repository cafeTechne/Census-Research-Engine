# Round 36 example: an MI/NY county deprivation index (exploratory)

**Exploratory; author self-review, not independent. Not registered.**

Data: the 145 MI/NY counties' ACS measures from Round 21b (poverty rate, households without a
vehicle, housing cost burden, and bachelor's degree attainment reversed), with their 80 VRE
replicates; cached, checksum-verified inputs. The study outcome (premature mortality) is not an
indicator. Reproduce: `scripts/r36_index_example.py STUDIES_ROOT OUT_DIR`.

## What the index shows, and why it is a warning

| | Value |
| :--- | :--- |
| PCA loadings | no vehicle 0.61, cost burden 0.64, poverty 0.25, bachelor's (reversed) 0.39 |
| Variance explained by the first component | 51% |
| Cronbach's α (Feldt 90% interval) | **0.40 (0.25–0.52)** |
| Correlation of PCA and equal-weight scores | 0.66 |
| Highest scores | Manhattan, Bronx, Brooklyn, Queens, Richmond (NY), Tompkins (NY) |

- The first component is driven by **no vehicle** and **cost burden**, which in New York City reflect
  dense, transit-rich, high-cost housing markets rather than deprivation; poverty carries little
  weight. The index ranks Manhattan as the most "deprived" county.
- α = 0.40 says the four measures do not behave as one scale here. Equal weights give a different
  ordering (correlation 0.66).
- Score uncertainty is small (median SE 0.17 on a scale whose areas span −1.6 to 8.0); 74% of
  counties keep their quintile in at least 80% of replicates. The problem is construct validity,
  not sampling error, and no interval fixes it.
- The 4-group typology isolates the NYC outliers (groups of 1 and 3) and is unstable (median
  replicate adjusted Rand index 0.60).

**Lesson for users (now in the recipe):** check the loadings and α before using an index; an
indicator such as "no vehicle" can measure urban form, not hardship, in a state with a large city.
A registered study would fix the indicator set and weights in advance with that rationale.

## Limits

Exploratory. Counties treated as independent (α's interval under-covers with spatial dependence).

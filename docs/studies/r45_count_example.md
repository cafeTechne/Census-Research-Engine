# Round 29 counts with the Round 45 count repairs (exploratory example)

**Exploratory example, not a registered study; author self-review, not independent.** Script
`scripts/r45_count_example.py`; input the released `r29_study_outputs.tar.gz` (verified checksums, network
blocked). Coefficients only; the WONDER disclosure audit passed for both regions. Slopes of log mortality
on poverty (percentage points), 90% intervals.

| Region | H2 hidden counties | H2 censored NB2 (validated) | H2 censored Poisson (exploratory) |
| :--- | ---: | :--- | :--- |
| MI/NY | 13 | 0.0327 (0.0186 to 0.0469) | 0.0383 (0.0196 to 0.0571) |
| OH/PA | 3 | 0.0701 (0.0565 to 0.0837) | 0.0587 (0.0518 to 0.0655) |

IM-8 NB2 (eight fixed clusters, t(7); MI/NY is the validated geometry, OH/PA uses state-respecting
clusters and is exploratory):

| Region | H1 premature | H2 drug overdose | H3 heart disease |
| :--- | :--- | :--- | :--- |
| MI/NY | 0.0292 (0.0199 to 0.0384) | 0.0202 (-0.0147 to 0.0552) | 0.0196 (0.0104 to 0.0289) |
| OH/PA | 0.0332 (0.0253 to 0.0412) | 0.0532 (0.0324 to 0.0739) | 0.0247 (0.0177 to 0.0318) |

**Reading.** Using the hidden overdose counts as interval information (instead of dropping those
counties) leaves the H2 slope positive in both regions. Under spatial clustering the MI/NY overdose slope
is no longer distinguishable from zero, matching the Round 30 post hoc IM-8 Poisson result; premature and
heart-disease mortality stay positive. The registered Round 29 results are unchanged; a confirmatory
spatial claim would need a new registration.

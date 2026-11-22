# Round 93 example: GWR, neighbourhood types and regions, Wayne County tracts (exploratory)

Author self-review, not independent; not a registered study. ACS 2019-2023, 585 Wayne County, MI tracts with complete estimates. Percent below poverty, unemployment rate, percent with a bachelor's degree (25+), each with its MOE.

**GWR (exploratory)** of poverty on unemployment and education: bandwidth 3.7 km, 51.5 effective parameters. Local unemployment slopes -0.29 to 2.39 (median 0.54); local education slopes -0.92 to 0.06 (median -0.35); non-stationarity p = 0.010 (unemployment). Local intervals under-covered in validation when slopes vary; read the spread descriptively.

**Neighbourhood types** (k-means, k = 4): mean stability 0.76; 40% of tracts unstable (< .8).

| Type | Poverty % | Unemployment % | Bachelor's % |
| ---: | ---: | ---: | ---: |
| 1 | 43.0 | 23.7 | 11.2 |
| 2 | 6.7 | 4.7 | 58.9 |
| 3 | 29.7 | 10.6 | 14.3 |
| 4 | 10.3 | 5.2 | 25.2 |

**SKATER regions** (k = 6, queen contiguity): mean stability 0.85; 28% of tracts unstable.

| Region | Poverty % | Unemployment % | Bachelor's % |
| ---: | ---: | ---: | ---: |
| 1 | 33.6 | 15.2 | 15.2 |
| 2 | 13.5 | 6.3 | 24.5 |
| 3 | 4.2 | 4.6 | 69.4 |
| 4 | 4.1 | 4.1 | 54.3 |
| 5 | 17.3 | 4.7 | 51.1 |
| 6 | 25.3 | 8.5 | 56.7 |

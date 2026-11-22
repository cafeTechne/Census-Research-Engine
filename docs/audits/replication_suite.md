# Replication suite (Round 74)

Replication reruns, not new registered studies: the registered results stay those of Rounds 66-69. Each row reruns one published replication through the engine's own routes and compares it with the original audit (`docs/replications/<id>.json` gives the route, rule and tolerance).

| Replication | Status | Max \|difference\| | Tolerance |
| :--- | :--- | :--- | :--- |
| `chr_segregation` | agrees | 2.84e-14 over 2055 (tolerance 1e-06) | exact: every county's D within 1e-6 points of CHR, and the same 2,055 counties |
| `state_gini` | agrees | 4.8e-06 over 12 (tolerance 0.0005) | each state's Gini within .0005 of Round 66 |
| `nc_ice` | agrees | 0 over 6 (tolerance 0.001) | each of the 6 slopes within .001 of Round 67 |
| `le_variance` | agrees | 1.14e-10 over 3 (tolerance 0.1) | each share within 0.1 point of Round 68 |
| `monnat_d` | agrees | 2.13e-14 over 1 (tolerance 0.05) | the economic distress coefficient within .05 of Round 69 |

Replication C with the Round 71 tract interval (descriptive):

| ICE | OLS slope | SCPC 90% CI | Validated |
| :--- | ---: | :--- | :--- |
| ice_race | 0.0454 | 0.0252 to 0.0657 (rho_bar 0.2) | True |
| ice_income | 0.1260 | 0.1089 to 0.1431 (rho_bar 0.2) | True |
| ice_income_race | 0.1465 | 0.1316 to 0.1613 (rho_bar 0.2) | True |

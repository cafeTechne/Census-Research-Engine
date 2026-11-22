# Round 71 example: replication C slopes with the tract interval

Descriptive; Round 67's registered result is unchanged. OLS slopes of ln(e0) on each ICE, NC 2014-2018 tracts.

| ICE | Slope | HC3 90% CI | SCPC rho_bar .20 90% CI | Residual Moran's I (p) |
| :--- | ---: | :--- | :--- | :--- |
| ice_race | 0.0454 | 0.0420 to 0.0489 | 0.0252 to 0.0657 (validated True) | 0.405 (0.001) |
| ice_income | 0.1260 | 0.1207 to 0.1312 | 0.1090 to 0.1430 (validated True) | 0.173 (0.001) |
| ice_income_race | 0.1465 | 0.1402 to 0.1527 | 0.1316 to 0.1613 (validated True) | 0.216 (0.001) |

Spatial dependence in the residuals widens the honest interval; every slope stays clearly positive.

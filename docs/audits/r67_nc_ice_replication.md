# Round 67 replication C: NC tract life expectancy and ICE

Criterion commit: `14b78b2`. Tracts: 1,971 (paper: 1,970). OLS interval: HC3. Islands dropped from the spatial error model: 1.

| ICE | Model | Published | Ours (90% CI) | Ratio | Replicated |
| :--- | :--- | ---: | :--- | ---: | :--- |
| ice_race | ols | 0.045 | 0.0454 (0.0420 to 0.0489) | 1.01 | True |
| ice_race | spatial_error | 0.054 | 0.0540 (0.0496 to 0.0585) | 1.00 | True |
| ice_income | ols | 0.13 | 0.1260 (0.1207 to 0.1312) | 0.97 | True |
| ice_income | spatial_error | 0.12 | 0.1219 (0.1161 to 0.1277) | 1.02 | True |
| ice_income_race | ols | 0.13 | 0.1465 (0.1402 to 0.1527) | 1.13 | False |
| ice_income_race | spatial_error | 0.13 | 0.1418 (0.1345 to 0.1490) | 1.09 | True |

| ICE | Adjusted R2 ours | Published |
| :--- | ---: | ---: |
| ice_race | 19.60% | 19.60% |
| ice_income | 48.19% | 48.19% |
| ice_income_race | 45.13% | 45.07% |

**Outcome: partly replicated.**

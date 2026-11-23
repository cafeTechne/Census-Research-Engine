# Round 97 example: spatial vs random cross-validation and MAUP, Wayne County tracts (exploratory)

Author self-review, not independent; not a registered study. ACS 2019-2023, 585 Wayne County tracts; poverty (%) ~ unemployment (%) + bachelor's degree (%).

| Model | RMSE, spatial blocks | RMSE, random folds | 90% coverage, blocks | Coverage, random | CRPS, blocks | CRPS, random |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| OLS | 12.28 | 11.48 | 0.87 | 0.91 | 6.92 | 6.39 |
| OLS + neighbour residuals | 12.10 | 10.22 | 0.84 | 0.91 | 6.80 | 5.58 |

Random folds look better for the model that borrows from neighbours; spatial blocks are the more honest (and still optimistic) guide to error in areas without nearby data.

**MAUP:** tract-level slope of poverty on unemployment 1.13; over 100 random contiguous zonings of about 10 tracts the zone-level slope ranged 1.81 to 2.00 (5th-95th percentile; mean 1.90).

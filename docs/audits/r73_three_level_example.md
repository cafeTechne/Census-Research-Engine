# Round 73 example: replication E through `multilevel_model`

Descriptive; Round 68's registered result is unchanged. `multilevel_model(input, "e0 ~ 1", ["state", "county"], share_intervals=False)` on the USALEEP tracts of Round 68.

65,662 tracts, 3,020 counties, 49 top units (48 states and DC).

| Level | Round 68 (hand script) | Engine route | Published |
| :--- | ---: | ---: | ---: |
| tract | 69.99% | 69.99% | 70.4% |
| county | 10.60% | 10.60% | 10.7% |
| state | 19.41% | 19.41% | 19.0% |

Intercept 78.18 years (90% CI 77.74 to 78.61).

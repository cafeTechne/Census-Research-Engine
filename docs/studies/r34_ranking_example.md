# Round 34 example: ranking Michigan counties by poverty (exploratory)

**Exploratory; author self-review, not independent. Not registered.**

Data: Michigan's 83 counties, ACS 2018–2022 poverty rate (B17001) with its 80 VRE replicates, from
the v0.26.0 attachment `r29_study_outputs.tar.gz` (ACS columns only; checksums verified). The state
rate is the county rates weighted by their poverty-universe populations (13.1%). Reproduce:
`scripts/r34_ranking_example.py r29_study_outputs.tar.gz OUT_DIR`.

## Rank intervals (rank 1 = highest poverty; 90%)

| County | Rate | Point rank | Individual interval | Joint interval |
| :--- | ---: | ---: | :--- | :--- |
| Isabella (26073) | 23.6% | 1 | 1–5 | 1–8 |
| Clare (26035) | 22.1% | 2 | 1–11 | 1–21 |
| Lake (26085) | 20.3% | 3 | 1–30 | 1–43 |
| Wayne (26163) | 20.2% | 4 | 2–12 | 1–21 |
| Montmorency (26119) | 18.5% | 5 | 1–49 | 1–65 |
| Luce (26095) | 18.3% | 6 | 1–64 | 1–78 |
| … | | | | |
| Ottawa (26139) | 7.6% | 81 | 66–82 | |
| Leelanau (26089) | 6.7% | 82 | 71–83 | |
| Livingston (26093) | 4.9% | 83 | 81–83 | |

- The median individual interval spans 55 of 83 ranks (joint: 66). Only **Isabella** is surely in
  the top 10%; Livingston is surely among the lowest three.
- Small counties with large MOEs (Lake, Montmorency, Luce) have point ranks near the top but
  intervals reaching the middle of the state: their point ranks say little. Wayne, with a small
  SE, is confidently in the top 12.

## Counties that differ from the state rate (13.1%)

With the state value built from the same counties (so it shares their errors; joint replicate
covariance): **34 of 83** differ after Holm adjustment (14 higher, 20 lower); 30 with simultaneous
intervals.

## Limits

Exploratory. Counties are treated as independent samples. A county-level rate describes the county,
not its residents' risks; rankings of rates with large MOEs should always be shown with intervals.

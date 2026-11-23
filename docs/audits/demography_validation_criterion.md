# Round 101 life-table intervals: pre-set criterion

Frozen with `scripts/demography_validation.py` and `census/demography_core.py` before the full run (tag
`criterion-r101`). Author self-review, not independent.

## Design

- **Age bands:** the WONDER ten-year bands. Start ages 0, 1, 5, 15, 25, …, 75, 85 (85+ open).
- **Death rates per 100,000:** 550, 24, 13, 80, 130, 200, 380, 850, 1700, 4000, 13000 (US-like all-cause).
- **Person-years:** the total × the 2000 US standard shares of the bands, with totals 50,000, 500,000 or 5,000,000.
- **Deaths:** Poisson(rate × person-years) per band, redrawn when a band has zero deaths in the open band.
- **Target:** e₀ and e₆₅ of the life table at the true rates.
- **Cells and draws:** 3 cells; 2,000 draws each; seed [20283011, cell, draw].

## Estimator

L1: the abridged life table with Chiang II standard errors and 90% normal intervals.

## Acceptance

- **Pass:** coverage of e₀ and of e₆₅ ≥ .86 in every cell.
- **Range gate:** a failure only at 50,000 means the intervals are validated from 500,000.

## Exact checks (in tests, not simulated)

- Whipple: 100 for uniform ages, 500 for ages on 0 and 5 only.
- Myers: 0 for uniform ages.
- Arriaga band contributions sum to the e₀ difference.
- Census-survival net migration is zero when census 2 equals the survived census 1.

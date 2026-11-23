# Round 95 YPLL and aberration detection: pre-set criterion

Frozen with `scripts/surveillance_validation.py`, `census/surveillance_core.py` and `census/standardize.py` before the
full run (tag `criterion-r95`). Author self-review, not independent.

## Y1: age-adjusted YPLL-75 rate

| Part | Specification |
| :--- | :--- |
| Age bands | WONDER ten-year bands below 75: <1, 1–4, 5–14, 15–24, …, 65–74 |
| Populations | Total × the 2000 US standard shares of those bands; totals 30,000, 200,000 or 5,000,000 |
| All-cause rates per 100,000 | 550, 24, 13, 80, 130, 200, 380, 850, 1700 |
| Overdose-like rates per 100,000 | 0.5, 0.3, 0.3, 10, 35, 40, 35, 25, 8 |
| Deaths | Poisson(rate × population) per band (unsuppressed) |
| Target | The age-adjusted YPLL rate at the expected counts |

- **Cells and draws:** 6 cells (3 sizes × 2 causes); 2,000 draws each.
- **Pass:** 90% Fay–Feuer interval coverage ≥ .86 in every cell.
- **Range gate:** a failure only at 30,000 means the interval is validated from 200,000.

## A1 historical limits and A2 EARS C2

| Part | Specification |
| :--- | :--- |
| Series | 15 annual counts with population 100,000 or 1,000,000 and a baseline rate of 20 per 100,000 |
| Trend | 0 or +3% a year |
| Overdispersion | None (Poisson), or gamma-mixed Poisson with an extra CV of .10 |
| Last-year multiplier | 1, 1.5 or 2 |
| Rates | count / population; current SE √count / population |

- **Cells and draws:** 24 cells; 2,000 draws each; seed [20282951, cell, draw].
- **Pass** (each of A1 and A2): the rate of "high" flags is ≤ .05 in both null cells (no trend, no overdispersion,
  multiplier 1).
- **Reported:** false-alarm rates under trend and overdispersion, and detection rates (power) at 1.5 and 2.
- A failing method is labelled descriptive.

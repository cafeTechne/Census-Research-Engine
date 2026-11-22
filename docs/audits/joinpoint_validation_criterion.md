# Round 77 criterion: joinpoint regression and rate ratios of age-adjusted rates

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/joinpoint_validation.py`;
- `census/joinpoint_core.py` (new);
- this file.

**Seen before this commit:**
- one smoke run (4 draws per joinpoint cell, 100 per ratio cell), which only checked that the script runs;
- a noiseless check that the grid search recovers the true joinpoints, APCs and AAPC exactly in all five
  scenarios at n = 20;
- one timing probe: model selection with K = 3 and 499 permutations took 0.2 s for a 25-point series.

## Methods (`census/joinpoint_core.py`)

- **Model.** Log-linear segments, fitted by WLS with weights equal to the event count (Poisson variance of the log
  rate). Joinpoints sit at observed years, with at least two observations between a joinpoint and either end, and
  between joinpoints (the Joinpoint defaults). Locations come from a grid search.
- **J1.** Kim et al. (2000) sequential permutation tests: 0 against K, then 1 against K, and so on, each at α/K.
  K = 3 and α = .05.
- **J2.** Per-segment APC with t intervals on n − 2k − 2 df.
- **J3.** Whole-window AAPC with a delta-method SE and the same t df.
- **J2b/J3b.** Empirical-quantile residual bootstrap of the selected model, with locations re-searched in each
  refit. Percentile intervals for the last segment's APC and the AAPC.
- **R1.** Tiwari et al. (2006) F interval for the ratio of two directly age-adjusted rates (Fay–Feuer modified
  shapes).
- **R1b.** Log-ratio delta method with the gamma variances.

## Designs

- **Joinpoint (45 cells, 1,000 draws each).** Series of 15, 20 and 25 annual points, with 50, 500 and 5,000
  expected events in the first year. Five scenarios:
  - no joinpoint (APC 1%);
  - one joinpoint at the midpoint, with slope change +2 or +5 APC points;
  - two joinpoints at one third and two thirds, with changes +d and then −d.
  - Counts are Poisson with a known population.
- **Rate ratio (4 cells, 2,000 draws each).** Ten age strata, two areas with different age structures and a
  standard population.
  - Expected counts per stratum: [5, 50] (small) or [500, 5,000] (large).
  - True ratio 1 or 1.5.
- **Deviations from the plan, made before any run:**
  - **Permutations.** The validation uses 999 permutations and 999 bootstrap fits per draw rather than 4,999. The
    engine default stays at 4,999.
  - **Slope change.** The plan's slope change of 0 is the no-joinpoint scenario, so it is not run as a separate
    cell.

## Pass rules

- **J1:** false-joinpoint rate ≤ .10 in every no-joinpoint cell. Power is reported.
- **J2 and J3:** coverage ≥ .86 in every cell, for every segment's APC and for the AAPC, given the true number of
  joinpoints.
- **J2b and J3b:** the same rule, with model selection. Judged separately.
- **R1 and R1b:** coverage ≥ .86 in every cell. Judged separately.

Seeds: `[20281701 + cell, draw]` for joinpoint; `[20281751 + cell, chunk]` for the ratio. A series with a zero
count is a failed draw (the log rate is undefined), reported per cell. Coverage uses only draws that ran.

## Engine (only what passes)

- **If J2b/J3b pass,** the engine reports the empirical-quantile intervals, which include selection and location
  uncertainty.
- **If only J2/J3 pass,** the t intervals are reported as validated conditional on the selected number of
  joinpoints, with a note.
- **If J1 passes,** the permutation selection is validated. If it fails, the number of joinpoints is
  exploratory.
- **Validated ranges:** 15 or more points and 50 or more events per year. Shorter or sparser series are
  exploratory.
- **Rate ratio:** the passing interval (R1 preferred) is the engine default.
- **Refused:**
  - overlapping ACS five-year releases;
  - WONDER-suppressed values (1–9 hidden).

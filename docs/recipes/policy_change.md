# Policy change: difference-in-differences and interrupted series

Profile: `difference_in_differences` and `interrupted_series` are in the **full** MCP profile; `trend_test` is in core.

Goal: estimate the effect of a policy or event that began at a known time.

1. Check the data. ACS five-year releases overlap: consecutive releases share four of their five years.
   - Area panels must use **non-overlapping** releases, for example 2013, 2018 and 2023.
   - Annual series need a source with **one value per year**, such as WONDER deaths or administrative counts, not
     consecutive ACS releases.
2. **Area panel with treated and comparison areas:** call
   `difference_in_differences(input_path, outcome, treated, treatment_period, se="<outcome>_se")`.
   - `treated` is a 0/1 column, and `treatment_period` is the first treated release.
   - `design="event"` gives release-by-release effects, and `reference` fixes the baseline release.
   - Overlapping releases are refused.
   - Validated: coverage .90–.91.
   - With three or more pre-periods, report the parallel-trends test the tool returns.
3. **Policies starting in different years across states (staggered adoption; Round 78):** two-way fixed effects
   are biased when effects differ by cohort or grow over time. Use an annual panel (ACS 1-year state estimates with
   `product="1-year"`, 2020 excluded, or another annual source) and call
   `difference_in_differences(input_path, outcome, None, design="staggered", first_treated="<first year column>",
   product="1-year")`.
   - The default Sun–Abraham event study is validated (.881–.899 with 51 units). `method="callaway_santanna"` is
     validated only with `se="<outcome SE column>"` (the ACS variance is added); without it, it is exploratory.
   - Report the overall ATT, the event study and the pre-trend check. Uniform event-study bands are descriptive.
   - **A single treated unit** (one state): synthetic control (`census.staggered.synthetic_control`, library only)
     failed validation and is exploratory.
4. **One annual series with a break:** call
   `interrupted_series(values=[...], years=[...], interruption_year=2014)`.
   - It reports the level and slope changes, with AR(1) errors.
   - The default method `bootstrap_t_cons` is validated from 17 points. `bootstrap_t_bb` is validated from 19,
     `bootstrap_t_bc` from 20 and `bootstrap_t` from 30.
   - Every method failed at 15 points, so a shorter series is exploratory.
   - Years must be consecutive.
5. **An annual series with no known break date (Round 77):** `joinpoint(years=[...], counts=[...],
   population=[...])` (full profile; or `rates` with `se`) finds where the trend changed (NCI Joinpoint style).
   - The number of joinpoints is validated (permutation tests; false-joinpoint rate .01–.02 at α .05).
   - The APC and AAPC intervals failed validation (they ignore uncertainty about where the joinpoints are):
     report them as exploratory.
   - Complete years only (suppressed years refused); not for overlapping ACS five-year releases.
   - `joinpoint(rate_ratio={...})` gives the ratio of two directly age-adjusted rates with the Tiwari interval
     (validated .90–.92).
6. **Several releases without a comparison group:** use `trend_test` with non-overlapping releases (recipe
   `tract_trend`). It tests a trend, not an effect.
7. Report:
   - the effect with its 90% interval and the validation flag;
   - the pre-period check;
   - the assumption that untreated areas show what would have happened, which is not testable from these data
     alone.

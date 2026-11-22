# Policy change: difference-in-differences and interrupted series

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
3. **One annual series with a break:** call
   `interrupted_series(values=[...], years=[...], interruption_year=2014)`.
   - It reports the level and slope changes, with AR(1) errors.
   - The default method `bootstrap_t_cons` is validated from 17 points. `bootstrap_t_bb` is validated from 19,
     `bootstrap_t_bc` from 20 and `bootstrap_t` from 30.
   - Every method failed at 15 points, so a shorter series is exploratory.
   - Years must be consecutive.
4. **Several releases without a comparison group:** use `trend_test` with non-overlapping releases (recipe
   `tract_trend`). It tests a trend, not an effect.
5. Report:
   - the effect with its 90% interval and the validation flag;
   - the pre-period check;
   - the assumption that untreated areas show what would have happened, which is not testable from these data
     alone.

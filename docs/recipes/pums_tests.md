# Tests and intervals on PUMS microdata

1. Decide the universe (`where`, e.g. `"AGEP >= 19 and AGEP <= 64"`) and the weight
   (`person` or `housing`). Use PUMS codes; check them with the PUMS data dictionary.
2. Pick the kind:
   - `independence`: are two categorical variables related? (`row`, `col`); first-order
     Rao-Scott test. Tables up to 3 x 4 are validated; larger ones are exploratory.
   - `two_by_two`: a yes/no outcome by a yes/no exposure (`exposure`, `outcome`):
     difference of proportions, odds ratio and relative risk with 90% intervals.
   - `means`: a numeric variable by groups (`var`, `by`): differences from the first group;
     z test for two groups, design Wald F for three or more.
   - `medians`: a numeric variable by exactly two groups.
   - `proportion`: one share (`var` a condition) with a Korn-Graubard interval, which stays
     valid for rare outcomes in small areas; the Wald interval does not (`method="wald"` is
     exploratory).
3. Call `test_association(state, year, kind, ...)`. All standard errors use the 80 replicate
   weights (Var = 4/80 sum of squared replicate deviations), as Census recommends for PUMS.
4. Report the estimate with its interval and the design effect for tables. Never report the
   design-blind Pearson test: it rejected 13-53% of true nulls at nominal 10% in validation.
5. Records under 30 in a group are flagged, not suppressed. Empty 2 x 2 cells are refused (no
   continuity correction). PUMA is the smallest PUMS geography.
6. Validation: `docs/audits/pums_tests_validation.md` (Round 32).

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

## Income inequality (Round 56)

`test_association(state, year, kind="inequality", var="HINCP", weight="housing")` (household income) or
`var="PINCP"` with a universe such as `where="PINCP >= 0 and AGEP >= 25"` (person income; negative incomes are
refused). Each measure comes with the SDR replicate interval:

- **Validated** (`docs/audits/pums_inequality_validation.md`, Round 56): the Gini coefficient, log P90/P10, log
  P80/P20 and, with `by` defining two groups, the difference in Gini (second minus first).
- **Round 60 repairs** (`docs/audits/pums_inequality_repair_validation.md`): with logit-transformed SDR
  intervals, Atkinson (ε = 1) is validated; Atkinson (ε = .5) and the top-decile share are validated with at least
  7,000 records (they under-covered in samples of about 2,000). The `interval` column names the method.
- **Exploratory:** Theil T (under-covered with heavy-tailed incomes even with a log transform, also with 8,000
  households in Round 62; a bias correction made it worse). Use the Gini or Atkinson instead.
- Zero incomes stay in the Gini. Theil, Atkinson and the ratios use positive incomes only (noted). Quantile
  ratios of heaped dollar amounts are flagged exploratory, as medians are.

## Models on PUMS records (Round 49)

`pums_regression(state, year, formula, model=...)` with `model` one of:

- `ordered_logit` / `ordered_probit`: an ordered outcome (codes sorted ascending; e.g. income-to-poverty
  bands). No intercept; thresholds are reported separately.
- `mnlogit`: an unordered outcome; the lowest code is the baseline, and each slope is "[k vs base]".
- `median`: weighted median regression (e.g. log earnings), robust to heavy tails.
- `probit`: a 0/1 outcome.

Each model is refitted with the 80 replicate weights; the intervals use Var = 4/80 sum of squared
deviations. All five passed validation (90% coverage .875–.915 with household clustering and weight CV
up to 1; `docs/audits/pums_models_validation.md`). Model-based SEs that ignore the design covered only
.62–.887: do not use them. Library: `census.pums_models.fit_pums_model(formula, df, model)`.

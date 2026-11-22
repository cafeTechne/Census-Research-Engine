# Tests and intervals on PUMS microdata

For a plain custom tabulation (count, mean, proportion, median or ratio by group, with replicate-weight SEs) use
`pums_tabulate(state, year, statistic, var=..., by=..., where=...)`; it reproduces Census PUMS verification
estimates and flags estimates from fewer than 30 records or with CV above 30%. The tests below compare groups.

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

## Decomposing a gap (Round 79)

Profile: full (`decompose_gap`).

How much of a gap between two groups (for example, uninsured rates of Black and White adults) is explained by
differences in the groups' characteristics?

1. Define two **mutually exclusive** groups as PUMS conditions, e.g. `group_a="RAC1P == 2 and HISP == 1"`,
   `group_b="RAC1P == 1 and HISP == 1"`, and the universe with `where` (e.g. `"AGEP >= 19 and AGEP <= 64"`).
2. Call `decompose_gap(state, year, outcome, group_a, group_b, covariates=[...], categorical=[...], model=...)`:
   - `model="linear"`: Oaxaca–Blinder (twofold, pooled reference) for a numeric outcome such as `WAGP`;
   - `model="logit"`: Fairlie for a 0/1 condition such as `"HICOV == 2"` (uninsured);
   - `categorical` code columns (e.g. `SCHL`, `ESR`) are normalised so results do not depend on the reference code.
3. Validated (`docs/audits/decomposition_validation.md`; SDR replicate-weight intervals):
   - Oaxaca–Blinder explained and unexplained totals from 300 records in the smaller group;
   - Oaxaca–Blinder detailed contributions and every Fairlie quantity from 1,000 records (they under-covered at 300).
   Rows below the gate carry `validated=False`.
4. **Interpretation rule:** "explained" is statistical composition (differences in the covariates'
   distributions), not a causal effect, and the unexplained part is not a measure of discrimination; it also
   absorbs omitted characteristics.

## Risk ratios and prevalence ratios from PUMS (Round 84)

For a common 0/1 outcome, `pums_regression(state, year, "I(HICOV == 2) ~ dis + AGEP", model="logit",
marginal="dis")` adds the standardized risk ratio and risk difference for the binary exposure, the attributable
fraction and the modified-Poisson prevalence ratio, all with replicate-weight intervals (validated). Odds ratios from
the logit overstate the risk ratio for outcomes above about 10%.

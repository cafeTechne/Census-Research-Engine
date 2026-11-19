# Rank and partial correlations, and rank comparisons of groups (area data)

1. Build an analysis frame with `build_analysis_frame` and its replicates.
2. Correlations: `correlation_matrix(input_path, variables, method=..., replicates_path=...)`.
   Read `validated_intervals` (one row per pair):
   - `spearman` and `kendall`: the standard Fisher-type intervals passed (Round 33); replicates
     are not needed for them, and they suit skewed ACS estimates;
   - `pearson`: valid only with replicates (the interval adds the ACS replicate variance); without
     replicates it is labelled exploratory (the plain Fisher-z interval under-covered);
   - `partial` (Pearson, `controls=[one variable]`): needs replicates, as Pearson.
3. Estimand: the correlation of the ACS estimates as observed. Sampling error attenuates it; do
   not read it as the correlation of the true values (`disattenuate=True` reports a corrected
   value alongside, never instead).
4. Rank comparison of groups: `compare_groups(..., method="rank")`: two groups give the
   probability that an area in the second group has a higher value (Brunner-Munzel interval);
   three or more give a Kruskal-Wallis test and epsilon-squared. No covariates.
5. Areas are assumed independent. With spatially correlated areas every correlation interval
   under-covered badly in validation (0.60-0.89 at nominal 0.90); say so when reporting.
6. Model diagnostics (OLS `fit_model` and `compare_groups`): variance inflation factors, the five
   most influential areas (Cook's distance), Breusch-Pagan and RESET p-values, residual
   skewness. Information only, never a reason to switch methods after seeing results.
7. Validation: `docs/audits/rank_validation.md` (Round 33).

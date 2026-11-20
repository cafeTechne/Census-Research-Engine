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
5. Areas are assumed independent unless you pass coordinates. With spatially correlated areas
   every independent-area correlation interval under-covered badly in validation (0.60-0.89 at
   nominal 0.90). Pass `spatial=True` (`correlation_matrix`) or `coords` (library) for the
   effective-sample-size intervals: validated for Spearman, Kendall and Pearson with replicates
   (Round 48) and, since Round 59, for partial correlations with one control and replicates
   (effective n of the residual series). All replicated on OH/PA (Round 59).
6. Model diagnostics (OLS `fit_model` and `compare_groups`): variance inflation factors, the five
   most influential areas (Cook's distance), Breusch-Pagan and RESET p-values, residual
   skewness. Information only, never a reason to switch methods after seeing results.
7. Validation: `docs/audits/rank_validation.md` (Round 33).

**In pre-registered manifests (Round 43).** Add `"interval": "validated"` to a `correlation_matrix`
analysis's `args` (with `"method"`: spearman, kendall, pearson or partial plus one `"controls"` variable).
Pearson and partial need declared ACS replicates. The default (`"fisher"`) keeps the older interval for
registered manifests; new manifests should use `"validated"`.

# Compare an area outcome across groups of areas (t-test, ANOVA, ANCOVA)

1. Build an analysis frame with `build_analysis_frame` (use replicates so ACS sampling
   error is included). Add a categorical group column to it, or use `group="state"`.
   Groups must be fixed classifications (for example metro/nonmetro), not cut points of
   a noisy ACS estimate. Every group needs at least 5 areas.
2. Choose the design:
   - `two_group`: two groups (a t-test on the group indicator);
   - `oneway`: three or more groups (one-way ANOVA);
   - `ancova`: groups adjusted for `covariates`;
   - `twoway`: tests whether the group difference depends on `group2` (interaction).
3. Call `compare_groups(input_path, outcome, group, design=..., replicates_path=...)`.
   Model `ols` for rates and percentages; `binomial` with `trials`, or `poisson` with
   `exposure`, for external counts.
4. Read the joint test first, then the pairwise differences:
   - **Validated** (Round 31, `docs/audits/omnibus_validation.md`; n = 145 areas):
     - joint test without spatial clusters: OLS one-way, ANCOVA and interaction tests;
     - joint test with `spatial=True` (8 fixed clusters): OLS and Poisson group tests;
     - pairwise: Holm for OLS, binomial and Poisson; simultaneous intervals for OLS only.
   - Everything else is returned but labelled **exploratory** in `notes` and
     `validation`; binomial/Poisson joint group tests were oversized (up to .17 at .10).
   - Fewer than 145 areas: exploratory only.
5. Areas are assumed independent unless `spatial=True`. Neighbouring areas are usually
   correlated, which makes non-spatial p-values too small; with `spatial=True` the test
   targets the coefficients on the ACS estimates as observed (attenuated, not corrected).
   A group missing from any of the 8 clusters makes the spatial test unavailable.
6. Effect sizes: OLS reports partial eta-squared and omega-squared as descriptive point
   estimates (they ignore sampling error). GLM differences are log odds or log rate ratios.
7. In a manifest, use `fit_replicate` with a group term in the formula and the hypothesis
   statistic `joint_test` with `term` (for example `"C(metro)"`) or `variable`; one-sided
   directions are refused. The Round 27 `joint_wald` (chi-squared) stays exploratory.

8. **Several outcomes at once (Round 39):** `compare_groups(..., outcomes=[a, b, c])` gives one joint
   test (MANOVA/MANCOVA; multivariate wild score bootstrap, validated) before the per-outcome tests.

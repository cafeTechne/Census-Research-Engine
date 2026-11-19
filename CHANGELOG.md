# Changelog

All notable changes, by development round. Versions follow `census.__version__`;
each tagged release (`v<version>`) is archived on Zenodo with its own DOI (see
[Releasing](#releasing)). Plans and acceptance criteria for each round are in
`PLAN_ROUND_<n>.md`.

## 0.38.0 (Round 41): treatment effects, instrumental variables and mediation

- Freeze procedures, script and criterion at `b7464e5` before the run.
- Passed: IPW/AIPW/regression-adjustment treatment effects with precise confounders; 2SLS with an
  independent second measurement as instrument (removes covariate attenuation); Sobel and bootstrap
  mediation with an exact mediator. Mediator sampling error broke mediation coverage. Design
  limitation recorded: the treatment cells did not test residual confounding.
- New `census.causal_core` (frozen), `census.causal`, MCP tool `estimate_effect`, recipe `causal`.

## 0.37.0 (Round 40): beta and median regression

- Freeze procedures, script, criterion and targets at `d5c9b02` before the run.
- Passed and selected: beta regression with the HC0 sandwich; median regression with the kernel SE.
  Failed: beta model-based SEs. Replicate-augmented variants over-cover and are not used.
- New `census.beta_median_core` (frozen), `census.regression_families`; MCP `fit_model(model="beta"|"median")`.
- Deferred: PUMS ordinal/multinomial/weighted quantile regression and GEE.

## 0.36.0 (Round 39): multivariate tests and count models

- Freeze procedures, script, criterion and targets at `0686bc0` before the run.
- Passed: multivariate wild score bootstrap (MANOVA/MANCOVA); NB2 with HC3 for count slopes. Failed:
  Poisson HC3 under strong overdispersion; zero-inflated Poisson.
- New `census.manova_counts_core` (frozen) and `census.count_models`; MCP `compare_groups(outcomes=...)`
  and validated `fit_model(model="negbin")`.
- Exploratory MANOVA example (poverty and share 65+ by metro class).

## 0.35.0 (Round 38): combining evidence

- Freeze procedures, script and criterion at `3edd5f4` before the run.
- Passed: Paule–Mandel + Hartung–Knapp–Sidik–Jonkman pooling for 2–4 estimates; fixed effect only
  without heterogeneity; TOST equivalence; z-test power and minimum detectable effects. Failed:
  DerSimonian–Laird with heterogeneity; HKSJ at 8 studies with heterogeneity (.855).
- New `census.evidence_core` (frozen), `census.evidence`, MCP tool `combine_estimates`, recipe
  `combine_estimates`.
- Exploratory example: pooling Round 29's replications.

## 0.34.0 (Round 37): agreement between sources

- Freeze procedures, script, criterion and targets at `e6d4be6` before the 8-cell run.
- Passed: bias with a t interval, Cohen's kappa of quintile classes. Failed (estimates only):
  Bland–Altman limits of agreement (observed and error-free) and Lin's concordance correlation (plain
  and error-corrected) intervals.
- New `census.agreement_core` (frozen), `census.agreement.check_agreement`, MCP tool `check_agreement`,
  recipe `agreement`.
- Exploratory example: ACS vs Census population estimates for MI/NY counties.

## 0.33.0 (Round 36): composite indices

- Freeze procedures, script, criterion and α targets at `e86907d` before the 8-cell run.
- Passed: per-area index-score intervals with fixed full-sample standardisation and weights (PCA and
  equal); Feldt α interval for independent areas.
- New `census.index_core` (frozen) and `census.composite_index.build_index` (scores with intervals,
  quintile stability, α, optional typology with replicate adjusted Rand index; circularity guard);
  MCP tool `build_index`; recipe `composite_index`.
- Exploratory MI/NY example exposed a construct-validity problem (NYC's car-free housing drives the
  index; α 0.40), recorded in the recipe.

## 0.32.0 (Round 35): corrected EIV slopes under spatial dependence

- Freeze candidates, script and criterion at `46fab40` before the 8-cell run (Round 30's linear design
  plus outcome error correlated 0/0.3 with a covariate's error).
- Passed: G1 (eight fixed clusters, pooled within-cluster reliability correction, t(7)) and G2
  (spatial-error λ̂ by ML, whitening, Fuller EIV). Closes the corrected-slope part of backlog item 1
  for linear models.
- New `census.spatial_eiv_core` (frozen) and `census.spatial_eiv.fit_spatial_eiv`; MCP
  `fit_model(method="eiv", spatial="clusters"|"error")`. Manifests unchanged.
- Post hoc R21b: H1 and H4 hold under both (`docs/studies/r35_posthoc_spatial_eiv.md`).

## 0.31.0 (Round 34): ranking areas

- Freeze procedures, script and criterion at `6286ad9` before the 8-cell run (K 40/145, SNR 0.5/2,
  ties or none).
- Passed: Klein–Wright–Wieczorek individual and joint rank intervals; Holm and simultaneous
  comparisons of each area with a weighted reference that shares their errors. Failed and not
  offered: parametric-bootstrap percentile rank intervals.
- New `census.ranking_core` (frozen), `census.ranking` (API; suppressed values excluded), MCP tool
  `rank_areas`, recipe `rank_areas`.
- Exploratory example: Michigan counties ranked by poverty (`docs/studies/r34_ranking_example.md`).

## 0.30.0 (Round 33): rank methods and model diagnostics

- Freeze procedures, script, criterion and 400,000-area reference targets at `f660e9c` before the
  8-cell run (correlation 0/0.4 × reliability 0.9/0.7 × independent/spatial fields).
- Passed: Spearman and Kendall Fisher-type intervals; Pearson and partial (one control) intervals
  with the ACS replicate variance added; Brunner–Munzel superiority; Kruskal–Wallis. Failed: plain
  Fisher-z Pearson and partial intervals (.84). All correlation intervals under-cover with spatial
  dependence.
- New `census.rank_methods`, `correlation.validated_correlations` (methods pearson, spearman,
  kendall, partial; `validated_intervals` in the MCP correlation tool), `compare_groups(method="rank")`,
  `census.diagnostics.model_diagnostics` (attached to OLS `fit_model` and `compare_groups`), recipe
  `rank_methods`. Manifests unchanged.
- Exploratory MI/NY example (`docs/studies/r33_rank_methods_example.md`).

## 0.29.0 (Round 32): design-based PUMS tests

- Freeze procedures, script, criterion and 2,000,000-household reference targets at `d65d034` before
  the 8-cell run (household ICC 0.1/0.4, weight CV 0.3/1.0, 800/3,000 households; SDR replicate
  weights from a Paley order-80 Hadamard matrix, as the ACS).
- Passed and selected: first-order Rao–Scott independence tests (tables up to 3 × 4), design F and
  z tests for group means, differences of proportions, odds ratios, relative risks, differences of
  means and medians, Korn–Graubard proportions. Failed: design-blind Pearson, Wald proportions,
  design Wald F for 3 × 4 tables.
- New `census.pums_tests` (frozen procedures), `census.pums_inference` (PUMS wrappers), MCP core tool
  `test_association` (core cap 16), recipe `pums_tests`.
- Exploratory Michigan PUMS example; it showed that medians of heaped amounts get zero replicate SEs,
  now detected (`heaping_share`) and labelled exploratory.

## 0.28.0 (Round 31): omnibus tests and group comparisons

- Freeze candidates, script and criterion at `3e3094a` before the 36-cell run (6 designs × 3
  models × 2 fields; 2,000 null and 500 alternative draws per cell).
- F references (W1, HTZ W2) failed everywhere. The wild score bootstrap (W3) passed OLS factor
  tests and binomial/Poisson spline tests; IM-8 Hotelling T² (W4) passed OLS/Poisson factor tests.
  Holm pairwise passed all models; simultaneous max-|t| passed OLS only.
- New manifest statistic `joint_test` (variable or term; two-sided) with confirmatory refusals for
  unvalidated combinations and fewer than 145 areas. `joint_wald` unchanged and exploratory.
  Binomial/Poisson splines are confirmatory with `joint_test` hypotheses.
- New `census.group_compare.compare_groups` and MCP tool `compare_groups` (core profile; cap 15):
  t-test, one-way ANOVA, ANCOVA and two-way interactions with ACS replicates, adjusted means,
  Holm or simultaneous pairwise differences, partial η²/ω², Brown–Forsythe and classical
  comparison diagnostics. Recipe `group_comparison`.
- Exploratory MI/NY example (county poverty by metro class); outputs in `r31_example_outputs.tar.gz`.

## 0.27.0 (Round 30): IM-8 with ACS sampling error

- Freeze script, criterion and twelve 400,000-area beta-star references at `2774140`
  and push before the 2,000-draw/cell run. C1 passed all linear/binomial/Poisson
  cells (.8690–.9235); C2 EIV failed (.0695–.9035), with unstable corrected moments.
  No criterion, seed, target, draw count or cluster count changed afterwards.
- Enable C1 via existing `spatial_clusters` for unweighted OLS/binomial/Poisson,
  population target and fixed Poisson offsets. Independent ACS error enters the
  between-cluster spread; no additive ACS variance or measurement-error correction.
  Report `se_cluster_mean`, t(7), unweighted cluster-mean coefficients. Uniformly
  constant nuisance terms are absorbed/not estimable; partial constancy is refused.
  Failed C2 remains refused, including exploratory manifests; no naive fallback.
- Post hoc, cached/hash-verified R21b/R22/R29 MI/NY checks with HTTP blocked:
  R21b unavailable; R22 H1/H2 retained, H3 unsupported; R29 H1/H3 retained,
  overdose H2 not retained (Holm p=.169). Registered manifests/results unchanged.
  Report is author self-review, not independent. OH/PA not re-checked.
- Acceptance: 1886 passed, 37 skipped, 4 warnings and 50 subtests; zero failures,
  26 new tests. Both goldens byte-identical (640 snapshots; 29 scenarios).
- R29 coefficient-only outputs pass disclosure audit; local output archive
  key-scanned. No new MCP tools/dependencies, WONDER/private-export access,
  GitHub CI, merge into defaultBranch, tag or release.

## 0.26.0 (Round 29): manual WONDER mortality studies

- Remove the WONDER API client, fetch script, API tests and XML fixture. All inputs
  are owner-supplied, pinned manual exports; no WONDER network access.
- Inventory all 62 files, including wrapped footers, optional population/rate
  columns, older unreliable markers, cause-code equivalence and MCD filters.
- Read national age × sex references, combine the two youngest groups, refuse
  suppressed reference cells and check hashes/periods. Add a disjoint B01001
  template and expected-count derivations with all 80 ACS replicates.
- Separate geographic join failures from suppressed outcomes and unsuppressed
  missing values. Mask protected county values throughout bundles/snapshots/maps;
  reject unverifiable complementary totals and scan study outputs before archiving.
- Register MI/NY and geography-only OH/PA mortality manifests together at
  `150e172`, before outcomes. All three poverty coefficients are positive and
  supported after Holm correction; all replicate. The overdose conclusion holds
  under both registered endpoint-assignment sensitivities. Reports distinguish
  fixed-offset model inference, reference-aware SMR intervals, descriptive EB
  maps and exploratory SII/RII; spatial dependence remains unresolved.
- Acceptance: 1860 passed, 37 skipped, 4 warnings and 50 subtests; zero failures.
  Twenty new synthetic tests; all legacy schema snapshots and all non-WONDER
  execution scenarios unchanged (`docs/audits/round29_compatibility.md`).
- No new dependencies or MCP tools. Version prepared on the branch; no tag or release.

## 0.25.0 (Round 28): segregation indices and reference-aware SMR

- Fixed, committed-and-pushed validations: segregation `4791763` (8,000 draws;
  audit `43cbedf`), SMR reference uncertainty `134bf7f` (12,000 draws; audit
  `8335199`). No seeds or criteria retuned after results.
- Add county D, isolation and Theil H from tract counts, strict 80-replicate
  uncertainty and the preset I-4(mean(Ir)-I) correction. Defaults selected by
  passing coverage: naive D, corrected isolation and corrected H. Failed
  variants and multigroup H remain exploratory. No negative clipping/dropping;
  zero tracts and undefined absent groups are noted.
- Register `segregation` through one MethodSpec; within-release county contrasts
  preserve shared replicate covariance, non-overlapping releases add variances.
  Explicit one-area nulls and release selectors prevent silent comparison choices.
  One-sided tests center on estimate-null. Add a recipe and matching agent/MCP rules.
- Extend SMR with hashed period_years and reference_counts. Rates per person-year
  scale expected counts by period; combined intervals add Poisson reference-rate
  variance. Shared band contributions are pooled before squaring. Internal-reference
  conservatism is noted. Fixed-E exact limits still exclude uncertainty in E.
- Reference-aware SMR passed coverage 0.8995–0.9105; omitting the reference term
  reached 0.7240 in the sparse-reference E=100 cell. Reference person-years remain
  fixed. Existing SMR defaults and execution golden remain unchanged.
- Range gate (review fix): a county with any tract group-count CV above .15, the
  validated simulation range, is marked not validated (`max_count_cv` reported);
  confirmatory hypotheses on it are refused (`hypothesis_not_tested`), exploratory
  manifests still test it. No 2018-2022 MI/NY county's white/Black tract counts
  meet the range, so segregation is effectively exploratory pending a
  realistic-error validation.
- No new dependencies or MCP tools (63); version 0.25.0.

## 0.24.0 (Round 27): descriptive EB rates and exploratory nonlinear tests

- Commit and push both fixed protocols before their full simulations: EB criterion
  `d4dec47` (8,000 datasets, 200 bootstrap refits each), joint criterion `376ce69`
  (16,000 null datasets plus fixed-alternative power draws). Audits retain all results.
- Poisson–Gamma ML includes interval-censored count probabilities. Both 90% procedures
  passed the six required cells: posterior coverage 0.8813–0.9000, Laird–Louis
  0.8718–0.8914. Posterior remains default. Outputs preserve suppression and GEOID,
  expose shrinkage, posterior ratios/limits, optional rates and validation metadata.
  This is descriptive only; fixed expected counts/rates, independent areas.
- Natural splines and full-covariance joint chi-squared tests **failed** the preset
  size criterion (0.1055–0.1825; four cells above 0.13). Both remain exploratory;
  confirmatory manifests refuse them. Do not retune the frozen experiment.
- Centered cr(df=3/4/5) bases freeze full-sample knots in replicate refits and influence
  checks. Joint hypotheses select standalone columns by variable, apply R2 and reject
  singular covariance. W reports df and has no coefficient CI or odds ratio.
- Expose term-labelled full sampling covariance and HC3 joint-model covariance.
  These additive diagnostic fields and dependent bundle hashes are the documented
  golden exception; existing numerical coefficient/hypothesis results stay unchanged.
- Mirror usage and restrictions in the small-area recipe and agent/MCP guidance.
  Existing maps accept eb_ratio. No new dependencies or MCP tools (63).

## 0.23.0 (Round 26): spatial-cluster inference and validation

- Pre-register and run 12,000 datasets on the unchanged Round 22 spatial design. IM with
  eight clusters passed all six cells (coverage 0.886–0.912); CR1-t at 8/12 clusters and
  999-Webb-weight restricted bootstrap at 12 clusters failed and remain exploratory.
- Add fixed geographic clustering (50 seeded EPSG:5070 restarts, >=5 analysed units/group),
  recorded assignments, and per-method/count manifest gates without new MCP tools.
- IM reports cluster-mean coefficients and t(7) intervals using `se_cluster_mean`; it has
  no additive full-sample model SE. IM/WCR require population target and refuse analysed
  variables with ACS replicates. Unweighted OLS/binomial only; EIV/Poisson/WLS unsupported.
- Cache-only post hoc report preserves original results and records the requested IM
  re-checks as unavailable under the retained protocol. The additional authorized R21b
  OLS sensitivity keeps ACS replicates with conservative combined SEs and is unclustered.
  Original residual Moran I: 0.195464 / 0.183552. Cluster map remains a release artifact.
- Mirror restrictions in recipes and agent/MCP guidance. Existing schema/run goldens
  remain byte-identical for old arguments; no unrelated bug fixes or registered-manifest edits.

## 0.22.1 (Round 25): staged manifest execution

- Split `run_manifest` into a 7-line driver over named stages sharing a typed `RunState`,
  retaining stage functions and monkeypatch lookups in `census.manifest.run`. The longest
  stage is 77 lines; `run.py` remains 896 lines. Public signature/docstring and `run_variant`
  are unchanged; no statistical method, test file, dependency or MCP change.
- Capture offline execution before refactoring: 29 deterministic run-golden scenarios,
  returned results and normalised text-artifact SHA-256s, covering all 19 blocking
  deviation kinds. Both this corpus and the 516 schema snapshots remain byte-identical.
  Execution-build stamps, output paths and wall-clock creation times are documented
  exclusions; scientific values and registered manifest hashes are retained.
- Full suite unchanged: 1703 passed, 37 skipped, 49 subtests. Existing suppression/join
  and saturated-fit plotting observations are recorded in the plan, without fixes.

## 0.22.0 (Round 24): method registry and public-health inequality

- Centralize manifest execution, method-specific validation, statistics and methods text in
  `MethodSpec`; preserve all 478 refactor snapshots and the existing public constant ordering.
- Add weighted area ridits, SII, log RII and concentration with independent-area HC3 and strict
  ACS replicate uncertainty; concentration ranks from least to most deprived (the reverse of
  the usual income-ranked sign). Warn about rank-error attenuation above median CV 15%.
- Add indirect SMR, pooled counts/expected counts, fixed-E Garwood intervals and combined
  Poisson/ACS log intervals; require explicit per-person reference rates and a hashed citation.
  Negative ACS band replicates are refused under the fixed validation domain, even with positive E.
- Both pre-specified validations passed: inequality conservative coverage 0.876–0.905 in
  required CV<=15% cells; SMR combined coverage 0.893–0.909. High-error inequality cells
  remain outside the validated range (coverage as low as 0.638 at rank CV 30%).
- Register both manifest methods without adding MCP tools (63). Extend circularity to ranked
  external outcomes, add log-scale ratio columns, explicit complete-case exclusion records,
  public library exports and the `health_inequality` recipe across agent guidance.
- Cache-only exploratory MI/NY LBW example: 144 complete counties, rank CV 6.63%; all
  conservative intervals include their null. Outputs remain a separate local archive.

## 0.21.1 (Round 23): internal package split

Internal: `census.manifest` split into a package (no behaviour change; golden snapshot identical)

## 0.21.0 (Round 22): count outcomes and spatial standard errors

- Label registered exploratory manifests and their analysis provenance explicitly.
- Add Bartlett Conley standard errors for EIV and binomial/Poisson replicate GLMs;
  fixed coverage validation FAILED, so spatial SEs remain exploratory only.
- Support external count/proportion outcomes with explicit trials/exposure,
  Pearson dispersion scaling and binomial odds ratios; register CHR v037.
- `fit_replicate(scale="robust")`: HC3 sandwich SEs for binomial/Poisson GLMs, valid under between-area
  overdispersion. Fixed pre-registered validation PASSED (coverage 0.879-0.897 at nominal 0.90; Pearson X2
  0.689-0.899). Manifests with external count outcomes now require `scale: "robust"`; `"X2"` is refused except
  for the three registered Round 22 manifests (`LEGACY_X2_MANIFESTS`).
- Held-out OH/PA apportionment re-test PASSED (ratio 0.9128); add opt-in dominant
  parent share >=0.95, preserving the missing default.
- Study: `docs/studies/r22_mi_ny_county_low_birth_weight.md`, MI/NY county low birth weight (CHR&R 2025,
  NCHS natality 2017-2023) against the Round 20 determinants. As registered: poverty (H1) and cost burden (H2)
  supported, no vehicle (H3) not supported. Post hoc (X6): robust SEs are 1.8-2.6x the quasi-binomial ones,
  which the study's own simulation shows under-cover. With robust SEs H1 holds and H2 would not
  (Holm p 0.117; 0.320 with the validated HC3 option, under which H1 still holds at 0.049). Exploratory: without NYC, no vehicle turns positive; with race composition, cost burden turns negative.

## 0.20.0 (Round 21): external health outcomes (Step 2)

- `census.health_sources`: registry of external health sources and the CDC PLACES connector (2025 release,
  tract and county). Keyless Socrata CSV exports filtered to states, measures and crude values; pages cached
  with SHA-256 sidecars; the dataset revision stamp (`rowsUpdatedAt`) recorded with the download it describes;
  `CENSUS_HEALTH_OFFLINE`; SE from the published 95% interval.
- Manifest `external` variables: joined on GEOID after the ACS frame; outcome-only for `fit_eiv`,
  `fit_replicate` and `fh_regression`; single release; tract vintage checked (or `harmonize_tracts_to`);
  blocking `external_unavailable` and `external_join_failed` deviations; `create_manifest` notes covariates that
  are inputs of the source's model (circularity); provenance, citation and methods text.
- `fit_eiv`: `fixed_variables` (an outcome from another survey, no replicates), `cluster="GEOID.str[:N]"`, the
  independence SE kept in the diagnostics when clustered. Cluster-robust SEs validated by simulation
  (`docs/audits/eiv_cluster_validation.md`, `scripts/eiv_cluster_validation.py`).
- `analysis_frame` builds its columns at once (no pandas fragmentation warnings).
- Study: `docs/studies/r21_mi_ny_places_disability_validation.md`: PLACES 2025 adult disability against the
  ACS 2020-2024 direct estimate, MI/NY tracts. H1-H3 supported (slope about 0.8 after correcting ACS error,
  within counties and beyond age); levels differ by about 13 points; exploratory E2 shows the circularity of
  determinant studies with a PLACES outcome.
- Part 2 (owner request): the circularity rule is enforced and stated in the MCP. `create_manifest` refuses
  (R1) an external outcome whose construct the ACS measures directly (PLACES DISABILITY: B18101) unless the
  analysis compares it with that ACS measure, and (R2) a tested term built from the outcome model's inputs
  unless the hypothesis carries a written `circularity_justification`. The rule is in the server instructions,
  the core profile, `docs/agent_protocol.md` section 16, the recipe `external_health_outcome` and the new tool
  `list_health_sources`.
- New sources: USALEEP tract life expectancy (2010 tracts; fully predicted tracts dropped by default;
  `apportion_to: 2020` by population-weighted rate apportionment, split tracts left missing because
  inheritance failed validation, `docs/audits/rate_apportionment_validation.md`); County Health Rankings &
  Roadmaps 2025 county data (direct NCHS mortality measures; PLACES-based measures flagged; ACS-derived columns
  refused); CDC WONDER exports (`census.vital_records`: pinned by SHA-256, footer required, suppressed counts
  censored, exact Poisson intervals).
- `fit_eiv(cluster_se="jackknife")`: delete-one-cluster jackknife, validated beside CR1; `make_map`
  `scheme="diverging"`; `run_variant` (exploratory refits of a finished run, MCP tool).
- Study (Part 2): `docs/studies/r21b_mi_ny_county_premature_mortality.md`: county premature age-adjusted
  mortality (CHR&R 2025, NCHS 2020-2022) against the Round 20 determinants, MI/NY counties. Poverty (H1) and
  disability (H4) supported; no-vehicle (H2, reversed by New York City) and cost burden (H3) not supported.
  The exploratory crude-adult re-run corrects the Part 1 E2 education ratio to 1.4×.
- Supported versions: Python 3.11 or later (3.10 reached end of life in October 2026) and SciPy 1.16 or later;
  CI tests Python 3.11-3.13.
- Multi-start optimizers (`census.optim.best_start`, used by the spatial Fay-Herriot fit, the multilevel model
  and the study-only `me_sem_fit`) prefer a converged start whose objective ties the minimum. `me_sem_fit` also
  judges convergence by the projected score, so an ABNORMAL line-search exit at the optimum no longer reports
  a fit as unconverged. This was the long-standing Python 3.10 failure in `test_spatial_lambda_correction`
  (SciPy 1.15: two starts reached the same optimum and the flagged one was 2e-13 lower).

## 0.19.0 (Round 20): public-health determinants

- Age standardization: `census.standardize` with the bundled 2000 U.S. standard population (NCHS/SEER single
  ages, SHA-256 checked, `scripts/update_standard_populations.py`), `standard_weights`, `direct_standardize`
  and the Fay-Feuer interval for age-adjusted rates from counts. Manifest derivation `age_standardized`
  (bands, standard; `create_manifest` fills the weights before hashing; exact replicate SEs).
- `fit_eiv` (`census.models`, manifest method `fit_eiv`, `fit_model` method `eiv`): least squares corrected for
  ACS sampling error in covariates and outcome, including their correlated errors, with error covariances from
  the replicates (Fuller 1987); sandwich SEs, optional `cluster`. Simulation validation in
  `docs/audits/eiv_validation.md` (`scripts/eiv_validation.py`).
- `fit_replicate` reports covariate reliability (overall and per factor group) and notes low or uneven
  reliability, pointing to `fit_eiv` (or regression calibration for GLMs).
- `aggregate_then_derive` collects the codes of `age_standardized` groups.
- Study: `docs/studies/r20_mi_ny_disability_determinants.md` (H1 supported; H2 not supported pooled but clear
  outside New York City, exploratory; H3 not supported, opposite sign; friction log F1-F10).
- PLAN_ROUND_20 also tracks Step 2 (external health data, no API keys needed) and Step 3 (count outcomes).

## 0.18.0 (Round 19): one complete preregistered study

- Manifests: `geography.harmonize_tracts_to` puts tract panels across the 2010/2020
  redraw on one tract vintage (block housing-unit/population weights); Census VRE
  replicates are apportioned through the same crosswalk, giving exact replicate SEs for
  apportioned estimates (`census.tract_harmonization`).
- RPP `areas: "county_metro"` at tract level (a tract takes its county's RPP area).
- `run_manifest` writes the analysed frame and replicates to `<output>/analysed/`, with
  SHA-256s in `run.json`, so follow-up analyses use exactly what the models saw.
- Review fixes: tract harmonization reuses `harmonize_panel`'s GEOID recodes (ACS 2011/2012
  renumberings were missed); unexplained unmatched tracts (`harmonization_incomplete`) and
  replicate/estimate mismatches (`harmonization_mismatch`) are blocking deviations; known
  ACS boundary changes and targets without apportioned rows are recorded; no crosswalk
  downloads when nothing needs apportioning; stricter validation (suffix, concept ids,
  pre-2010 releases, unverifiable codes); a failed analysed-data copy never loses the run.
- First complete preregistered study: `docs/studies/r19_mi_ny_tract_income_change.md`
  (H1 and H3 supported, H2 not supported; run history, friction log F1-F12 and review).
  The review (author self-review at the owner's request) adds an errors-in-variables check
  of H2 (`scripts/r19_review_eiv.py`).

## 0.17.0 (Round 18): metadata integrity

- Verify bundled variable/group archives before use or API fallback, including
  legacy lookups; return metadata-specific integrity failures across interfaces.
- Record consumed JSON hashes, custom-source status and group metadata identity;
  isolate caches by resolved archive root and preserve explicit cache resets.
- Stop manifest execution on corrupt metadata before current-run output, preserve
  typed workflow failures, and extend the stored-input reference workflow checks.
- Keep archived research data and Round 17 model evidence unchanged. No estimator,
  dependency or archive format changes.
- Review fixes:
  - integrity errors are no longer `ValueError`s, so input handlers cannot
    report corruption as a bad argument; every MCP tool translates them to
    `BUNDLED_DATA_INTEGRITY` at registration;
  - manifest analysis ids are checked as portable, case-distinct filenames
    when the manifest is validated, not after every model has run;
  - an occupied output folder is reported as an `output_dir` problem (run_manifest)
    and keeps the completed verification result (verify_proposition);
  - clearing the metadata cache no longer empties dicts callers still hold;
  - the model benchmark accepts omitted arguments for tools with no required
    arguments;
  - the archive cache no longer retains raw bytes; release labels are matched once
    per distinct value.

## 0.16.0 (Round 17): exact claims and bound evidence

- Exact operator-pinned proposition evidence with full digests, reviewed
  formalizations, a small typed matrix rule domain, rational witnesses,
  evidence replay, and opt-in CLI/MCP verification. No new dependencies.
- Preserve ACS1 analysis identity and refuse incompatible five-year replicates;
  reject stale bundle destinations without deleting prior artifacts.
- Correct disattenuation/aggregation input guards, validate model SE signs,
  redact API-key errors, and preserve errata archives on incomplete refresh.
- Run mandatory exact verification tests before tag-triggered publication,
  rejecting missing or skipped required checks.
- Preserve malformed benchmark tool arguments as protocol failures; distinguish
  runtime failures, exhausted tool loops and empty final answers in new results.
- Reject malformed Unicode with typed verification errors; prevent MCP schema
  version coercion and check binding/revocation through the real stdio transport.
- Preflight bundle artifact names to prevent path traversal, writes outside the
  bundle, and case-insensitive filename collisions; preserve valid display labels.
- Include nested `bundle.json` payloads in bundle hashes and reject final figure
  filename collisions before bundle writes, including rendered/copied combinations.
- Add offline frozen-prompt preparation and bound-evidence transcript scoring
  for verification benchmarks, separate from proof authority and live model runs.
- Add injected async verification-client controls for two model phases, shared
  deadlines and replay-checked duplicate suppression; no default model connection.
- Wire an opt-in loopback runtime adapter with verification-only MCP, exact
  model preflight, bounded raw traces and separate declared/observed metadata.
- Archive the Round 17 model study with raw evidence, checksums and replay
  instructions. Preserve primary failures separately from the JSON-mode follow-up.

## 0.15.1 (patch): B01003 total from B01001 for firewall-blocked VRE files

- **`fetch_vre` substitute for the total-population VRE file.** census.gov's firewall
  rejects the 2015-2019 Michigan tract B01003 file for every client (support ID
  13979921158196382640). When a B01003 file is rejected or returns HTTP 404, `fetch_vre`
  now reads line 1 ("Total:") of the B01001 file for the same release, geography and
  state, and relabels it as B01003_001.
  - Only this pair is substituted (`VRE_TOTAL_FALLBACKS`). On the 2015-2019 New York
    tract files the two lines are identical in every cell. A live test
    (`CENSUS_LIVE_TESTS=1`) re-checks this.
  - The substitution is never silent. It issues a warning and is recorded in
    `attrs["substitution"]`: requested URL, reason, the B01001 URL and its SHA-256, and
    the verification. Manifest replicate records and methods text carry it.
  - Other B01003 lines, other tables or failures, `allow_substitute=False`, or an
    unavailable B01001 file still raise the original error. A new `lines=` argument
    keeps only the requested table lines.
- **Michigan 2015-2019 population covariance completed**
  (`docs/audits/acs_sampling_covariance.md`), using the B01001 substitute. Results match
  2020-2024 and New York, so the conclusions are unchanged.
  - Order 1 within county is -0.075 [-0.103, -0.046] (2020-2024: -0.081).
  - Across county it is -0.005 [-0.014, 0.004].
  - The county aggregation ratio is 0.000.
  - Split-half pair reliability is 0.64.

## 0.15.0 (Round 16): spatial methods validated under ACS sampling error

- Project renamed **Census Research Engine** (github.com/cafeTechne/Census-Research-Engine);
  the distribution name `census-acs-toolkit` is unchanged.
- **Lag-model effects:** `spatial_regression(model="lag")` reports direct, indirect and
  total effects first (delta-method and replicate SEs; verified against the S(W) algebra
  and spreg's multipliers), with notes that beta is not the marginal effect and that a
  rho = 0 test is not a specification test. Coverage and a heavy-tail caveat at high rho
  are measured (`docs/audits/spatial_regression_validation.md`).
- **New option `spatial_regression(model="error", correct_outcome_error=True, se_col=...)`:**
  corrects lambda for outcome sampling error using spatial Fay-Herriot (REML). Lambda
  coverage is 0.86-0.93 against 0.003-0.85 uncorrected, measured on the shipped estimator.
  - Assumes errors independent across areas. Warns when errors are correlated, and when
    the outcome is a controlled total, where the sign of the bias depends on the release.
  - Limited to 2,000 areas.
- **ACS sampling-error covariance measured from VRE replicates** (Michigan and New York,
  2015-2019 and 2020-2024; `docs/audits/acs_sampling_covariance.md`):
  - neighbour error correlation is about 0 for rates, shares, medians and most counts;
  - controlled totals are correlated within county, with a sign that can differ by
    release.
- **LISA validation:** under ACS error (`docs/audits/lisa_validation.md`), with no default
  change.
  - The Round 15 "38%" caveat is corrected: it counts maps with at least one significant
    area, not contiguous false clusters.
  - Replicate stability and Fay-Herriot reruns are shown not to be false-positive checks.
- **Common-factor and specification studies:** LR size measured in Juhl's design; Koley &
  Bera score tests shown not to identify SEM vs SDM. All new studies are info-only and
  run on demand.
- **Polite census.gov downloads:** one shared helper (`census/http.py`) with
  - backoff and Retry-After on 429/5xx;
  - per-host pacing;
  - a clear error for the firewall "Request Rejected" page, with the support ID and the
    cache path for a manual download;
  - validation of manually placed files.
- **Literature:** full-text reading notes with verification levels
  (`docs/literature/full_text_reading_notes.md`). Remote-access planner decisions are
  recorded in `docs/remote_access_decisions.md`.
- **CI:** the weekly live-validation cron moved off the hour (Mondays 06:17 UTC).

## 0.14.0 (Round 15): studies across releases, spatial coverage, 2020 Census

- Confirmatory studies across releases: CPI conversion to a declared `dollar_year`, then
  each release's own RPP (`rpp_years`); `"replicates": {"source": "census_vre"}` fetches
  Census VRE tables (URLs and SHA-256 recorded). Overlapping releases are refused for any
  replicate source; `replicate_scope: "covariates_only"` is an explicit, hashed exception
  for outcomes without replicates. Example: MI/NY change in CPI- and RPP-adjusted mean
  household income, 2015-2019 to 2020-2024: +$3,111 per county, 90% CI [2,709, 3,513].
- Spatial coverage studies (info): `spatial_regression_coverage`, `local_morans_size`.
  **Default changes (owner decisions):** the spatial lag model now defaults to GMM (ML rho
  coverage under ACS sampling error was 0.48 at rho 0.3 and 0.003 at 0.6; GMM 0.89-0.90);
  local Moran's I now reads p-values two-sided with 9999 permutations (per-area false
  positive rate 0.20 to 0.10). Previous behaviour: `method="ml"`;
  `sided="folded", permutations=999`. Caveats with measured numbers in both tools'
  outputs (error-model lambda attenuation; false clusters under spatially patterned
  sampling error).
- spreg's per-fit stdout print is suppressed at its source, so it can no longer corrupt
  the MCP stdio stream.
- 2020 Decennial Census: P.L. 94-171 (`dec/pl`) and DHC (`dec/dhc`) through the existing
  pipeline. Counts are "not sample-based (MOE undefined)", never MOE 0, with a
  disclosure-avoidance advisory; sampling tests refuse decennial-only input; ACS vs
  census comparisons treat the count as a fixed reference. New live check F11
  (invariants and block-to-tract/county hierarchy, 5,492 values); 11/11 checks pass live.
- Remote access decisions recorded (`docs/remote_access_decisions.md`); no networking
  changes in this release.

## 0.13.0 (Round 14): confirmatory multi-state analyses

- Pre-registered manifests take several states (`geography.states`, 2-digit FIPS; not
  with ZCTAs), derivations evaluated on replicates, and a declared RPP adjustment step
  (`adjustments`, shared with `place_adjust_frame`; `rpp_year` required, filled in by
  `create_manifest` into `<name>.completed.json` when omitted; exclusions run first;
  RPP provenance recorded). The Michigan/New York study runs confirmatorily
  (`examples/manifests/mi_ny_income_education.json`) and reproduces Round 13 exactly
  (pct_bachelors 811.0, 90% CI [684.3, 937.7]).
- Validation battery adds Michigan (26); all 10 checks pass live and offline.
- PUMS memory measured (`scripts/pums_memory_benchmark.py`, `docs/audits/pums_memory.md`;
  risk R2 closed): peak about 275 MiB + 2.8 KB per person record. Avoidable weight-matrix
  copies removed (1.9M rows: 6.4 to 5.4 GiB peak, results bit-identical); grouped medians
  gather each group once.
- MCP `cache_import` (full profile) with the CLI's safety rules; pandas 4 deprecation in
  `format_dataframe` fixed.
- Review fixes: `run_manifest` records replicate-derivation errors as deviations instead
  of raising; ACS refs with E/PE suffixes match their replicates; methods text reports how
  many units received replicate SEs.

## 0.12.0 (Round 13): real data, end to end

- Live verification: the full battery against Census-published values passes live (10/10
  checks, `docs/audits/validation_report.md`); stale F5 expected-failure marker and
  criterion text fixed (the first dispatched CI live run failed only on that marker).
- Live case study for Michigan and New York counties (`docs/case_study_mi_ny.md`): RPP-adjusted
  median household income, journal maps with an uncertainty layer, a regression with
  replicate refits, a results bundle; CLI only. New tools `place_adjust_frame` (county RPP by
  CBSA membership, applied to estimates, SEs, and replicates) and `make_results_bundle`;
  `build_analysis_frame` takes several input and replicate files; `tool ... --save PATH`.
- The Round 12 reference workflow runs entirely from the CLI: `python -m census cache import`
  (atomic; a synthetic import into the default cache needs `--allow-default-cache`;
  `cache clear` also removes the synthetic marker) and `run_manifest --arg replicates_path=...`
  with Python/CLI/MCP parity tests.
- Provenance: extraction metadata records the observed data source; bundles take it from
  their inputs (`census_api`, `synthetic`, `mixed` with a warning, or `unknown`), not from
  the cache present at bundle time. Failed saved results are refused.
- Bundled price index and RPP tables are verified against their SHA-256 at load (risk R1
  closed); custom tables are recorded with their hash and marked unverified. New error
  code `BUNDLED_DATA_INTEGRITY`.
- Validation: a fast smoke gate (band widened by 3 Monte Carlo SE) runs on pull requests;
  the full gate is a release step and now runs in parallel (`--jobs`), with BLAS pinned to
  one thread, which also makes its results independent of the machine's thread count.
  New info-only study `did_ar1_sensitivity`: DiD coverage stays near nominal under AR(1)
  errors up to rho 0.9 in 4-5 period panels.
- Fixes: map legends stay inside journal-width figures and do not split identifiers;
  `_load_frames` rejects missing GEOID/Year keys; pandas-3 integer replicate columns.

## 0.11.0 (Round 12): verifiable and reproducible workflows

- Independent dense reference checks for the multilevel GLS layer and two-group DiD.
- `scripts/inference_validation.py --gate`; `docs/audits/CHECK_MAP.md`. The gate also
  requires the default multilevel and DiD coverage studies (`multilevel_known_variance`,
  `multilevel_random_slope`, `did_two_group`, `did_event`); replicate-refit and
  serial-correlation variants remain on demand.
- `census.results.interval_description`: every output (tables, figures, methods,
  tool and adapter results) states the same estimand, interval basis, level, and
  distribution; method-aware estimand text (PUMS, DiD, area-level); undefined
  uncertainty shown as undefined.
- `docs/reference_workflow.md`: an offline, rerunnable reference analysis with a
  blocked case, checked by an independent second reader.
- Manifests: `confirmatory_incomplete` for runs with blocking deviations (including
  failed calls); synthetic labels follow the actual data source, with mismatch
  deviations; caller-supplied replicates described and hashed identically across
  pandas/numpy versions; hypothesis results kept in bundles; `run_manifest` tool
  accepts replicates and returns the run status.
- CLI tool runner accepts `--arg KEY=VALUE` (portable paths).

## 0.10.1 (Round 11): audit decisions

- **Q2 incomplete replicates:** `replicate_policy="flag"|"strict"` on replicate-based
  models; pre-registered manifests run strict; exploratory results say when sampling
  SEs may be understated.
- **Q1 DiD serial correlation:** coverage measured under AR(1) area shocks (0.896-0.905
  at rho 0.5 and 0.8, default population target); no estimator added; assumption
  documented in `census.did`, with a not-validated warning for panels over 4 periods.
  The non-default these-areas target is conservative under serial correlation
  (coverage 0.90-0.965).
- **R2 PUMS memory:** measured ~3.6 GB peak at California scale; warning for all-column
  reads of large files.
- **R1 price-data integrity:** documented guarantee (verified at generation and by tests,
  not at each load).
- pandas 3 read-only array fixes in `census.models`, `census.did`, `census.analysis`.

## 0.10.0 (Round 10): microdata, 1-year estimates, research designs; Round 11 audit fixes

- **PUMS microdata** (A, B): `census.pums` tabulations, crosstabs, weighted
  medians, and survey-weighted regression with 80 replicate weights; reproduces
  all 32 Census PUMS verification estimates and SEs for Wyoming (2024 1-year and
  2020-2024 5-year). PUMA boundaries.
- **ACS 1-year** (C): `product="1-year"` across planning and extraction;
  2005-2025 metadata archive (no standard 2020 release); 65,000+ geography checks;
  1-year vs 5-year comparisons refused; product-aware overlap.
- **Designs** (D): `census.multilevel` (Kenward-Roger intervals) and `census.did`
  (non-overlapping periods, full replicate refits); simulation coverage 0.89-0.91.
- **Regional price parities** (E): `census.rpp`, BEA RPPs for states, metro and
  nonmetro portions, and MSAs; never applied by default.
- **Carryovers** (F): ZCTA and place crosswalks, self-contained interactive HTML
  maps, local-model harness tasks for maps and spatial tools.
- **Round 11 audit fixes** (C1-C7 in `PLAN_ROUND_11.md`): undefined PUMS
  replicates no longer report zero uncertainty; zero-weight records no longer move
  weighted medians; spatial replicates are aligned to the estimate's release;
  scalar SE/CV decode Census sentinels; two-group DiD requires a pre-treatment
  reference; regression outputs name the SE behind each interval.
- Concept DOI for citation: [10.5281/zenodo.23925301](https://doi.org/10.5281/zenodo.23925301).

## 0.9.1 (hotfix): Zenodo metadata

- Zenodo archiving: add `.zenodo.json` with an explicit creator name (Zenodo could not build creators from the alias-only `CITATION.cff` author), so releases are archived and receive a DOI. No code changes.

## 0.9.0 (Round 9): geography, maps, spatial inference, data quality, packaging

- **Geography and maps** (workstreams A-E): cartographic and TIGER/Line boundaries
  with vintage-checked joins, static journal maps that report class separability
  and mark low-reliability areas, spatial statistics and models that carry ACS
  sampling error, block-population-weighted crosswalks, block groups and custom areas.
- **ACS errata and user notes** (F): `census.errata` and `data/acs_errata.json`,
  generated by `scripts/fetch_acs_errata.py` from the Census errata and user-notes
  pages (source URL and retrieval date per record). `errata_for(table, years)`
  looks up notes that name a table; `check_urls` confirms every cited note resolves.
- **Controlled-estimate MOEs** (G1): `clean_census_sentinels` now keeps a
  controlled MOE (`-555555555`) as `0` and adds a boolean `<base>_CONTROLLED`
  column (behavior change; `preserve_controlled=False` restores NaN). Validation
  check F1 accepts exactly this representation.
- **Slim core download** (G2): `workflows.download_table(table_code, geography,
  state_code, years, variables, output_dir)` plans, stops if the plan would block,
  then downloads a panel with codebook and SE/CV columns. It replaces
  `batch_download` in the `core` MCP profile (the full profile keeps it). Round 7
  workflow tools return native `summary` and `next_step`; `run_validation`'s
  per-check tally moved from `summary` to `checks_summary`.
- **Tract CV profile** (G3): the simulation tract profile is derived from real
  2023 tract MOEs (`tests/fixtures/cv_profile`, `simulation.derive_cv_profile`)
  instead of an assumed one.
- **Packaging** (H): `pyproject.toml` (`pip install -e .` from a clone, extra `dev`), console
  scripts `census-acs` and `census-acs-mcp`, this changelog, a tag-triggered
  release workflow, and `CITATION.cff` 0.9.0.

## 0.8.0 (Round 8): inference that respects ACS sampling error

Analysis frames with SE columns and replicates; replicate-refit regression
(OLS/WLS/GLM), regression calibration, SIMEX and reliability screening;
Fay-Herriot small-area estimation (reproduces the R `sae` example); power and
minimum detectable differences; GLS trend tests on non-overlapping releases;
correlation matrices; journal figures and tables; preregistration manifests;
MCP tool profiles (`core`, `review`, `full`), recipes, and coverage simulations.

## 0.7.0 (Round 7): derived statistics verified against Census

Proportions, ratios, products, percent changes, aggregation of geographies,
medians from distributions, all with 90% MOEs; Variance Replicate Estimates for
exact variances; batch significance with multiple-comparison corrections; the
F1-F10 validation battery against Census-published values; table-scoped
concordance rules; the 2010/2020 tract crosswalk; nationwide extraction;
extraction replay; C-CPI-U; `CITATION.cff`; continuous integration.

## Round 6: vintage-safe variables and R-CPI-U-RS

Cross-release variable concordance (concept IDs, reviewed overrides, continuity
checks that block unsafe panels), metadata archive per vintage, constant dollars
with R-CPI-U-RS (the Census Bureau's ACS index), and an agent-first interface.

## Round 5: research-grade pipeline

Tidy GEOID x Year panels, Parquet export, codebooks, sentinel cleaning with
notes, SE/CV/reliability columns, inflation adjustment, and a query cache.

## Round 4: MCP server

FastMCP server exposing table search, variable lookup, and batch download to agents.

## Round 3: headless library

The `census` package: API client, geography, tables, export, and statistics
separated from the GUI, with a command-line interface.

## Round 2: research usability

Improvements to the desktop downloader for research workflows (table search,
multi-year batches, output formats).

## Round 1: foundation

Initial stabilization of the original batch downloader.

## Releasing

1. Bump `census/__init__.py` `__version__` (and `PACKAGE_VERSION` in
   `census/pipeline.py`), update this file and `CITATION.cff` (`version`,
   `date-released`).
2. Tag and push: `git tag v0.9.0 && git push origin v0.9.0`. The `Release`
   workflow (`.github/workflows/release.yml`) builds the sdist and wheel, checks
   the tag matches the package version, and creates a GitHub release with both
   files attached.
3. Zenodo: the repository owner enables the repository once in Zenodo
   (Account > GitHub > toggle the repository on). Zenodo then archives every
   published GitHub release and mints a version DOI plus a concept DOI that
   always resolves to the latest version. After the first release, add the
   concept DOI to `CITATION.cff` (`doi:`) and the README badge.

# Statistics roadmap: SciPy/statsmodels methods for the engine (Rounds 31–39)

**Status: draft (2026-11-18).** The owner's multi-round roadmap. It is the source from which each
`PLAN_ROUND_<n>.md` is drafted; it is not itself a plan. **Implementing agents: do not read this file
unless the owner asks; implement only the lowest-numbered `PLAN_ROUND_<n>.md`.** Update the status
column in section 6 when a round merges, and reorder freely.

## 1. Why a roadmap, and the one idea behind it

SciPy's `scipy.stats` (t-tests, ANOVA, chi-square, rank tests, correlation, resampling, multiple
comparisons) and statsmodels (ANCOVA, MANOVA, GLMs, meta-analysis tools) assume **independent,
exactly measured observations**. Our data break that in three ways:

1. **ACS area estimates carry sampling error**, published as MOEs and 80 replicate estimates (VRE).
2. **PUMS microdata are a weighted survey sample**, with 80 replicate weights.
3. **Neighbouring areas are spatially dependent** (Rounds 21–30), and some outcomes come from external
   sources with their own rules (WONDER suppression, PLACES model-based estimates).

So we never expose a SciPy test raw. Each method is wrapped so its uncertainty comes from the right
source, validated by a fixed simulation, and only then offered for confirmatory use. **The SciPy call
computes the statistic; the engine supplies the variance and the reference distribution.**

### Data regimes (every method must say which it supports)

| Regime | Units | Uncertainty source | Existing entry points |
| :--- | :--- | :--- | :--- |
| A. Area-level ACS | tracts, counties, places | 80 VRE replicates per estimate (MOE fallback, flagged) | `build_analysis_frame`, `fit_model`, `run_manifest` |
| B. PUMS microdata | persons, households | survey weight + 80 replicate weights (SDR) | `pums_tabulate`, `pums_regression` |
| C. External outcomes | counties (WONDER, PLACES, CHR) | source-specific (Poisson counts, model-based CIs) | `external` manifest inputs, `smr` |

### What already exists (do not rebuild)

- **Models:** `fit_replicate` (OLS/WLS/binomial/Poisson, HC3, replicate SE, IM-8 spatial clusters),
  `fit_eiv`, `regression_calibration`, `simex`, `multilevel_model`, `spatial_regression`, DiD.
- **Tests:** `calculate_significance`/`batch_z_test` (two estimates), `trend_test`,
  `minimum_detectable_difference`, `correlation_matrix` (Pearson), `adjust_pvalues`
  (Holm, Bonferroni, BH, BY).
- **Indices:** `inequality` (SII/RII/concentration), `segregation` (D/isolation/Theil H), `smr`.
- **Failed and exploratory:** joint chi-squared Wald (oversized: 0.106–0.183 at nominal .10),
  splines, cluster EIV, CR1/WCR/Conley. **The joint-Wald failure blocks every omnibus test below
  (ANOVA, ANCOVA, MANOVA, interactions), so Round 31 fixes it first.**

## 2. Rules every new method follows (the "method contract")

1. **Validation first.** Criterion and script committed before the full run; failures stay exploratory
   (CLAUDE.md). Default criterion: 90% coverage ≥ 0.86 and nominal-.10 size ≤ 0.13 in every cell.
2. **Name the estimand and the uncertainty.** Outputs state the regime, the variance source
   (replicates / design / Poisson) and what is left out (spatial dependence, offset error, attenuation).
3. **Effect sizes with intervals, not just p-values.** Every test returns the effect (difference,
   ratio, η², odds ratio, rank correlation) and its CI.
4. **Spatial honesty.** Area-level tests say whether IM-8 (C1) applies; otherwise "independence
   assumed" is a stated limitation.
5. **Existing rules apply:** circularity R1/R2, WONDER disclosure (no counts 1–9 or derived values),
   pre-registration discipline, MI/NY studies with held-out replication.
6. **MCP for small local models.** Few umbrella tools with enum arguments, not one tool per SciPy
   function; guided, plain-language results; refusals with an `error_code`. Target: **at most six new
   tools across the roadmap**, plus `core` profile entries only for the most-used two. Rule text is
   mirrored in `docs/agent_protocol.md`, `docs/recipes/` and the MCP profile text.
7. **Each round is one plan under 15 KB**, with a worked MI/NY example (exploratory unless registered).

## 3. Catalogue: what SciPy/statsmodels offers and where it fits

Priority: **H** high value for public-health county work, **M** useful, **L** later or niche.
"Round" is the proposed home in section 5.

| Family | SciPy / statsmodels functions | Regimes | How uncertainty enters | Pri | Round |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Two-group mean difference (t / Welch) | `ttest_ind`, `ttest_rel`; regression on an indicator | A, B | replicate / SDR SE; t(df) reference | H | 31, 32 |
| One-way ANOVA, Welch ANOVA | `f_oneway`, `alexandergovern`; OLS with a factor | A, B | corrected omnibus Wald (F) | H | 31 |
| ANCOVA (group effect adjusted for covariates) | statsmodels OLS + omnibus contrast | A | as above | H | 31 |
| Two-way ANOVA / interactions | statsmodels `anova_lm` logic, re-derived for replicates | A | omnibus Wald on interaction block | M | 31 |
| Post hoc pairwise / many-vs-reference | `tukey_hsd`, `dunnett`, `multivariate_t` | A, B | simultaneous intervals from replicate covariance | H | 31, 34 |
| Contingency tables, independence | `chi2_contingency`, `contingency.association` | B | Rao–Scott first/second-order correction from SDR | H | 32 |
| Odds ratio, relative risk | `contingency.odds_ratio`, `contingency.relative_risk` | B, C | SDR / Poisson intervals | H | 32 |
| Quantiles, medians, income distributions | `quantile_test`, `ecdf` | B | Woodruff intervals via SDR | M | 32 |
| Rank correlation | `spearmanr`, `kendalltau`, `somersd` | A | replicate refits of the rank statistic | H | 33 |
| Partial correlation | via OLS residuals | A | replicate refits | M | 33 |
| Rank-based group tests | `mannwhitneyu`, `kruskal`, `brunnermunzel` | A | replicate refits (non-smooth: must validate) | M | 33 |
| Distribution comparison | `ks_2samp`, `anderson_ksamp`, `cramervonmises_2samp`, `wasserstein_distance` | A, B | descriptive; inference only if validated | L | 33 |
| Model diagnostics | `shapiro`, `anderson`, `probplot`, Breusch–Pagan (statsmodels) | A | diagnostic only, never a gate | M | 33 |
| Ranking areas, league tables | `rankdata`, `multivariate_normal` / `multivariate_t` | A, C | replicate ranks; simultaneous rank intervals | H | 34 |
| Spatial random effects | statsmodels `MixedLM`, BYM/ICAR-style via `scipy.sparse`, `optimize` | A, C | model-based + replicate | H | 35 |
| Composite indices (deprivation) | `scipy.linalg.svd` (PCA), factor analysis (statsmodels `Factor`) | A | fixed loadings, replicate propagation | H | 36 |
| Internal consistency | Cronbach's alpha (closed form) | A | replicate refits | M | 36 |
| Area typologies (clustering) | `scipy.cluster.hierarchy`, `vq.kmeans2` | A | assignment stability across replicates | M | 36 |
| Agreement between sources | Bland–Altman, Lin's CCC, ICC (closed forms), `linregress` | A, C | replicate + source CIs | H | 37 |
| Meta-analysis across states or rounds | statsmodels `meta_analysis` (fixed/random, Q, I²) | A, C | inverse-variance from each study's SE | H | 38 |
| Equivalence (TOST), non-inferiority | two one-sided t / z tests | A, B | replicate SE | M | 38 |
| Power and sample size | `nct`, `ncf`, `ncx2`, `stats.power` (simulation) | A, B | planned SEs from MOEs | M | 38 |
| MANOVA / MANCOVA | statsmodels `MANOVA` (Pillai, Wilks) | A | replicate covariance of the multivariate test | M | 39 |
| Canonical correlation | statsmodels `CanCorr` | A | replicate refits | L | 39 |
| Overdispersed and zero-heavy counts | statsmodels `NegativeBinomial`, zero-inflated models | C | HC3 / replicate; validated like Poisson | M | 39 |
| Bootstrap and permutation | `bootstrap`, `permutation_test`, `monte_carlo_test` | B (exchangeable units only) | resampling; not valid under spatial dependence | L | 33 |

**Deliberately excluded:** SciPy tests run on ACS estimates as if exact; Fisher/Barnard exact tests on
weighted data; normality tests as gates for choosing a test; stepwise selection; permutation tests on
spatially dependent areas. They give confident-looking but wrong answers for our data.

## 4. Shape of the MCP surface at the end

| New tool (umbrella) | Covers | Round |
| :--- | :--- | :---: |
| `compare_groups` | t / Welch, ANOVA, ANCOVA, interactions, pairwise post hoc; `regime` A or B | 31 (B from 32) |
| `test_association` | PUMS contingency tables (Rao–Scott), OR/RR, rank and partial correlation | 32–33 |
| `rank_areas` | league tables, simultaneous comparisons to a reference, rank intervals | 34 |
| `build_index` | composite indices, internal consistency, typologies | 36 |
| `check_agreement` | agreement between two sources for the same quantity | 37 |
| `combine_estimates` | meta-analysis, equivalence tests, power | 38 |

Each tool also becomes a manifest method (`METHODS` registry) so confirmatory studies can use it, and
each gets a `get_recipe` entry. MANOVA and count models extend `compare_groups` and `fit_model`
instead of adding tools.

## 5. Proposed rounds

Each round: validation first; one worked MI/NY example (exploratory unless registered); docs mirrored;
version bump. Dependencies are noted; anything without one can move.

### Round 31: omnibus tests and group comparisons (ANOVA, ANCOVA, t-tests) for area data

- **Why first:** the joint Wald test failed (oversized), and it is the core of ANOVA, ANCOVA,
  interaction tests and spline tests. Fixing it unlocks most of section 3.
- **Candidates for the omnibus test** (q restrictions, n areas, p parameters):
  - **W1:** Wald F = W/q against F(q, n − p), with HC3 + replicate covariance;
  - **W2:** the same with a small-sample covariance (CR2/Bell–McCaffrey-style adjustment) and
    Satterthwaite-type denominator df;
  - **W3 (spatial):** Hotelling T² on the IM-8 per-cluster coefficient vectors (needs q ≤ 6).
- **Validation:** nominal-.10 size ≤ 0.13 and power reported, across q ∈ {2, 4, 6}, n ∈ {80, 145},
  reliability {0.9, 0.7}, independent and spatial fields; one-way (3–5 groups) and ANCOVA designs.
- **Ships:** `compare_groups(regime="area", design="two_group" | "oneway" | "ancova" | "twoway")`:
  - group means with replicate CIs, differences, η² and partial η² with CIs, the omnibus test;
  - pairwise post hoc: Holm, or simultaneous (max-|t| from the replicate covariance, Tukey-like);
  - re-validates the Round 27 spline and joint tests under the passing candidate.
- **Example:** poverty by metro/nonmetro/rural group, adjusted for age structure (ANCOVA), MI/NY.

### Round 32: PUMS design-based tests (contingency tables, means, OR/RR, quantiles)

- **Methods:** Rao–Scott first- and second-order corrected chi-square from SDR replicate weights;
  design-based two-group and k-group mean tests; odds ratio and relative risk with SDR intervals;
  quantile comparisons with Woodruff intervals.
- **Validation:** a synthetic finite population with known associations, sampled with unequal weights
  and SDR-style replicates; size and coverage criteria as in section 2.
- **Ships:** `test_association(regime="pums", ...)` and `compare_groups(regime="pums")`.
- **Example:** disability by insurance type, and the poverty rate by disability status, MI/NY PUMAs.

### Round 33: rank correlation, rank-based group tests and diagnostics

- **Methods:** Spearman, Kendall and partial correlation with replicate refits; Mann–Whitney and
  Kruskal–Wallis effect sizes (probability of superiority, ε²) with replicate intervals; residual
  diagnostics (normal Q–Q, heteroscedasticity) added to `fit_model` output as diagnostics only.
- **Validation:** coverage of rank statistics under ACS-type error (ranks are non-smooth, so
  replicate variance may fail; failures stay descriptive). Bootstrap/permutation only for designs
  with exchangeable units.
- **Ships:** extends `test_association` and `compare_groups` (`method="rank"`).

### Round 34: ranking areas and simultaneous comparisons

- **Methods:** replicate distribution of each area's rank; simultaneous rank intervals; "which
  counties differ from the state" with Dunnett-style simultaneous intervals from the replicate
  covariance; top-k membership probabilities. Optional EB shrinkage for external rates (Round 27).
- **Why:** county rankings drive public-health decisions and are often over-interpreted.
- **Validation:** coverage of simultaneous rank intervals and familywise error of the many-vs-
  reference comparisons.
- **Ships:** `rank_areas`. WONDER outcomes follow the disclosure rules (suppressed counties unranked).

### Round 35: spatial random effects (backlog item 1)

- **Methods:** area random effects with a spatial structure (ICAR/BYM-style or SAR on the error)
  fitted by penalised likelihood (`scipy.sparse`, `scipy.optimize`) or statsmodels `MixedLM` where it
  fits; ACS error via replicates; Poisson version for external counts.
- **Goal:** corrected (EIV-type) inference under spatial dependence, which Round 30's cluster EIV
  failed to provide, and a spatial option for Rounds 31–34.
- **Validation:** the Round 26/30 geometry and criteria. If it fails, record it and stop.

### Round 36: composite indices, internal consistency and typologies

- **Methods:** PCA or factor-based deprivation indices from ACS tables (fixed loadings from the full
  sample, propagated through all 80 replicates); Cronbach's alpha; hierarchical or k-means area
  typologies with assignment-stability scores across replicates.
- **Circularity:** an index must not contain the outcome it is used to explain (R1/R2 check).
- **Ships:** `build_index`. Validation: index-score coverage and typology stability under
  ACS-type error.

### Round 37: agreement between data sources

- **Methods:** Bland–Altman bias and limits of agreement, Lin's concordance correlation and ICC,
  for one quantity measured by two sources (ACS vs PLACES disability, ACS vs decennial counts, ACS
  population vs WONDER denominators), with both sources' uncertainty.
- **Why:** before using an external source as a substitute or a check, show how well it agrees.
- **Ships:** `check_agreement`.

### Round 38: combining evidence: meta-analysis, equivalence and power

- **Methods:** fixed- and random-effects meta-analysis (DerSimonian–Laird and REML), Q, I² and
  prediction intervals, to pool replications (MI/NY + OH/PA, later more states); TOST equivalence
  and non-inferiority; power and sample size for the tests above (noncentral t/F/χ² and simulation),
  extending `minimum_detectable_difference`.
- **Note:** pooling states is a new, registered analysis, never a reinterpretation of a past study.
- **Ships:** `combine_estimates`.

### Round 39: multivariate outcomes and count-model families

- **Methods:** MANOVA and MANCOVA (Pillai's trace preferred) with replicate covariance; canonical
  correlation (exploratory); negative binomial and zero-inflated models for overdispersed counts,
  validated against the Round 29 Poisson HC3 baseline.
- **Ships:** extensions to `compare_groups(design="manova")` and `fit_model(model="negbin")`.
- **Depends on:** Round 31's omnibus test.

## 6. Status

| Round | Theme | Status |
| :--- | :--- | :--- |
| 31 | Omnibus tests, ANOVA/ANCOVA, t-tests (area) | proposed |
| 32 | PUMS design-based tests | proposed |
| 33 | Rank methods and diagnostics | proposed |
| 34 | Ranking areas, simultaneous comparisons | proposed |
| 35 | Spatial random effects | proposed (backlog item 1) |
| 36 | Composite indices and typologies | proposed |
| 37 | Agreement between sources | proposed |
| 38 | Meta-analysis, equivalence, power | proposed |
| 39 | MANOVA/MANCOVA, count families | proposed |

## 7. Open questions for the owner

1. **Order:** 31 first is a dependency; 32–39 can move. Is spatial random effects (35) more urgent
   than the new test families?
2. **Studies:** should each round end with a registered MI/NY study (slower, citable) or an
   exploratory example only (faster)?
3. **Tool budget:** is six new MCP tools acceptable for the local-model profile, or should only
   `compare_groups` and `test_association` join `core`?
4. **PUMS geography:** PUMAs are the smallest PUMS areas; is PUMA-level analysis useful to you, or
   should Round 32 drop down the list?

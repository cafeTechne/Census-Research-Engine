# Round 39 plan: multivariate group comparisons and count-model families

**Goal.** Two gaps remain from `ROADMAP_STATISTICS.md`: (1) testing a group effect on several outcomes
at once (MANOVA/MANCOVA: e.g. poverty, uninsurance and disability rates by metro class), and (2)
count outcomes that are more variable than Poisson or have many zeros (rare causes of death, small
counties). This round:

- **(A)** validates a multivariate omnibus test and count-model slope intervals under ACS-type error;
- **(B)** ships `compare_groups(..., outcomes=[...])` (MANOVA/MANCOVA) and `fit_model` families
  `negbin` and `zip` with validated flags;
- **(C)** runs one exploratory example.

Version 0.36.0. Baseline: 1957 passed, 37 skipped. Ground rules as Round 31 (branch
`phase39/manova-counts`; validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures

**Multivariate omnibus** (m outcomes, a group factor with q columns, OLS): restricted fits without the
group columns for every outcome; area-level score contributions stacked over outcomes (q·m
columns); statistic S = Aᵀ Ω⁻¹ A with Ω their outer-product sum plus the replicate covariance of
the stacked coefficients (conservative target, as Round 31).
- **V1** wild score bootstrap with one Rademacher sign per area shared by all outcomes (399 draws);
- **V0** Pillai's trace from statsmodels `MANOVA` (iid, ignores sampling error): comparison only.

**Count slopes** (one covariate of interest, external counts with an exposure offset):
- **N0** Poisson with HC3 (the Round 29 baseline);
- **N1** negative binomial (NB2, α by maximum likelihood) with HC3;
- **N2** zero-inflated Poisson (logit inflation with intercept only), robust sandwich.

## 2. Validation (`scripts/manova_counts_validation.py` → `docs/audits/manova_counts_validation.md`/`.json`)

- 145 MI/NY counties, Round 30 geometry, independent fields (spatial informational).
- Multivariate: m ∈ {2, 3} outcomes with cross-outcome correlation 0.5, each with sampling error
  (reliability 0.85, replicates with that correlation); groups as Round 31 (4 groups, q = 3) and an
  ANCOVA version (one covariate with error, reliability 0.7, independent of groups). Null: no group
  effect on any outcome. 4 cells; 2,000 draws; size at .10 in [.07, .13].
- Counts: E from Round 30 (lognormal, median 100) and a low-count variant (median 10); log-rate =
  β·x + noise; overdispersion: Poisson-gamma with shape {∞ (none), 2}; zeros: none or 20% structural
  zeros. Covariate x with sampling error (reliability 0.9, replicates; naive target β*, computed from a
  reference as Round 30). 8 cells; 2,000 draws; 90% coverage ≥ .86 per family, judged in the cells
  each family is meant for (N0, N1 in all; N2 only where zeros exist and as information elsewhere).

## 3. Engine, example, tests

`compare_groups(..., outcomes=[...])` adds a multivariate joint test (V1 if it passes) alongside the
per-outcome results; `fit_model(model="negbin"|"zip")` report validated flags; docs mirrored.
Example: poverty and share 65+ by metro class (MI/NY, Round 31 frame) as a MANOVA; drug-overdose
counts with NB vs Poisson is **not** used (WONDER outputs stay in registered studies). Tests:
score statistic by hand, Pillai's trace against statsmodels, NB/ZIP fits against statsmodels, flags
against the audit. Goldens unchanged; full suite; STATUS, CHANGELOG, version 0.36.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `0686bc0` | Pushed before the full run. |
| V1 / N0–N2 results | Mixed | V1 and NB2 pass; Poisson HC3 and ZIP fail. |
| Engine, tests | Done | count_models; MCP paths; 6 tests. |
| Example | Done | MANOVA of poverty and share 65+. |
| Goldens, final suite | Done | Goldens identical; 1963 passed, 37 skipped, 0 failures. |
| Exceptions | Recorded | Pre-freeze ZIP changes; WIP commit before freeze. |

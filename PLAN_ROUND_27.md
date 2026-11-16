# Round 27 plan: empirical-Bayes rate smoothing, splines and joint Wald tests

**Goal.** (A) Stabilise small-area rates from counts, such as county deaths, including WONDER's
suppressed counts (1–9), with Poisson–gamma empirical Bayes. (B) Allow non-linear covariate effects
through natural cubic splines, tested with a joint Wald test. A joint test is also usable for any
multi-column term, such as `C(region)`. Each part ships only after its pre-set validation passes.
Version 0.24.0.

**Non-goals.**

- No manifest method for smoothing: smoothed rates are descriptive (maps, tables), not hypothesis tests.
- No splines inside `fit_eiv`, `fh_regression` or the spatial models.
- No new MCP tools; no new dependencies.

## 0. Ground rules

1. Branch `phase27/eb-splines` from `defaultBranch` (after Round 26 merges). Do not merge, tag or release.
   Never rebase or force-push. Work in your own clone or worktree.
2. **No AI attribution** in commits or the PR body.
3. Never print, log or commit `.env` or any key or token.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. No GitHub CI.
5. **Validation first:** the script and criterion are committed and pushed before the first full run.
   Nothing changes after it. Smoke runs: at most 20 draws per cell, writing no audit files.
6. Record impossibilities in section 8 and choose the option that changes least.

## 1. Part A: `census/rate_smoothing.py`

Model: `O_i ~ Poisson(E_i θ_i)` and `θ_i ~ Gamma(α, β)` (mean α/β). Here `E_i` is an expected count:
from `indirect_standardize`, or `pop_i × overall rate` when the caller passes exposure only.

**`eb_poisson_gamma(observed, expected, censored_lower=None, censored_upper=None, level=0.90,
interval="posterior"|"laird_louis", n_boot=200, seed=None)`**

1. **Hyperparameters by maximum likelihood** on the negative-binomial marginal.
   - A censored area (WONDER `Suppressed`, bounds 1–9 from `vital_records.read_wonder_export`)
     contributes `P(lower ≤ O ≤ upper)` to the likelihood.
   - Start from the Marshall (1991) moment estimates. If the ML fit fails to converge, raise; do not fall
     back silently.
2. **Posterior.** An observed area is `Gamma(α + O, β + E)`. A censored area is the finite mixture
   `Σ_k w_k Gamma(α + k, β + E)` over k from lower to upper, with `w_k` proportional to the
   negative-binomial pmf at k.
3. **Outputs**, as a DataFrame keyed by GEOID: `observed`, `censored`, `expected`, `raw_ratio`,
   `eb_ratio` (posterior mean), `shrinkage = β/(β + E)`, `eb_lower` and `eb_upper`, and the `interval`
   type. Rates are the ratio times the reference rate, when the caller passes one.
4. **`interval="laird_louis"`**: a parametric bootstrap of the hyperparameters (Laird & Louis 1987, JASA
   82:739–750). Draw `(α*, β*)` by refitting on simulated counts, and widen the intervals with the
   mixture of posteriors.

**Validation (`scripts/eb_rate_validation.py` → `docs/audits/eb_rate_validation.md`/`.json`).**

- Cells: areas n ∈ {145, 1000} × true θ distribution {gamma, lognormal} × CV(θ) ∈ {0.15, 0.30}, giving
  8 cells with 1,000 draws each. The seed is `20261127 + cell index`, in that nesting order.
- Expected counts are lognormal with median 20 and log-SD 1.2, drawn once per cell, so many areas have
  counts of 9 or fewer. In each draw, apply WONDER suppression: counts 1–9 become censored [1, 9].
- Acceptance (pre-set): the **area-averaged** 90% coverage of the true θ is ≥ 0.86 in all four gamma
  cells and both lognormal CV 0.15 cells. The lognormal CV 0.30 cells are informational. Judge both
  interval types separately.
- The default is the posterior interval if it passes, else Laird–Louis if it passes. If neither passes,
  the function ships with a "not validated" note in its output, and STATUS says so.
- Also report: mean squared error of `eb_ratio` against the raw ratio (uncensored areas); coverage in
  the smallest-E quintile; and the share of censored areas.

**Integration.**

- `census/figures` map helpers accept an `eb_ratio` column.
- The `small_area` recipe and `docs/recipes/small_area.md` get an "Event counts (deaths)" section that
  says when to use EB (counts) versus Fay–Herriot (ACS estimates with known sampling variance).
- Mirror the rules in the agent protocol.
- Exports: `eb_poisson_gamma`.

## 2. Part B: splines and joint Wald tests

**Formula functions.**

- Add `cr` to `schema.FORMULA_FUNCTIONS`: patsy's natural cubic regression spline, with `df` required
  (3, 4 or 5) and knots at default quantiles. The registry check refuses `cr(...)` outside the
  `fit_replicate` family (OLS, WLS, binomial, Poisson).
- **Knots are fixed from the full sample.** Replicate refits already rebuild the design through
  `X_df.design_info` (`census/models.py`, `build_design_matrices`), which keeps patsy's stateful knots.
  Add a test proving that a refit on perturbed data reuses the full-sample knots.

**Joint statistic.**

- A new hypothesis statistic `joint_wald`, for `fit_replicate` analyses. The hypothesis gives
  `variable: <manifest variable>`: the test covers every design column whose patsy factor involves that
  variable, alone and not in an interaction. `direction` must be `two_sided`. `term` is not allowed.
- The statistic is `W = b' V⁻¹ b` over the q columns, referred to χ²(q). `V` is the covariance that
  matches the analysis target:
  - **model:** HC3 or robust covariance;
  - **sampling:** `4/80 Σ_r (b_r − b)(b_r − b)'` from the replicate refits;
  - **conservative:** model plus sampling.
- `fit_replicate` exposes the full sampling covariance in `diagnostics["sampling_covariance"]` (as a
  term-indexed DataFrame). If `V` is singular, the hypothesis is not tested and gets a deviation; do not
  pseudo-invert.
- Circularity R2 applies to `variable`, and the methods text gets one sentence on joint tests.
- In the hypothesis table, `estimate` is W and the CI columns are empty. Add a `df` column.

**Validation (`scripts/joint_wald_validation.py` → `docs/audits/joint_wald_validation.md`/`.json`).**

- Cells: model {linear, binomial with `scale: "robust"`} × spline df {3, 5} × ACS-like sampling error on
  x {none, CV 0.15}, giving 8 cells. n = 145, 2,000 draws per cell, seed `20261128 + cell index`.
  Replicates come from `census.simulation.make_replicates`, as in the Round 24 validation.
- Under the null (no effect of x), the outcome depends only on an independent control z.
- Acceptance (pre-set): the empirical size of the nominal 0.10 test (conservative target) is within
  [0.07, 0.13] in all 8 cells.
- Report power at one fixed non-linear alternative (`f(x) = 0.3·sin(x)` on the standardised scale) as
  information.
- If the criterion fails, `joint_wald` and `cr` stay exploratory only (confirmatory manifests are
  refused).

## 3. Tests (`tests/test_round27.py`)

- **EB likelihood:** a hand-calculated negative-binomial likelihood for a 5-area example, including one
  censored area. The posterior mixture weights sum to 1, and the posterior mean for an uncensored area is
  `(α + O)/(β + E)`.
- **Validation values:** EB refuses negative or non-integer counts and E ≤ 0.
- **Spline rules:** the knots-fixed test, and `cr` refused in `fit_eiv`, `fh_regression` and the spatial
  methods.
- **Joint Wald:** W matches a hand calculation from a known covariance. A `C(region)` joint test works.
  A singular V produces a deviation. `term` together with `joint_wald` is refused, and so is a one-sided
  direction.
- **Gates:** the exploratory gate works for both parts (patch where the check imports from, and assert
  the refusal).
- **End to end:** an offline manifest run with `cr(x, df=4)` and a `joint_wald` hypothesis.

## 4. Acceptance

- Both audits are committed after their criterion commits.
- `scripts/refactor_golden.py` and `scripts/run_golden.py` differ only in the "supported
  statistics/functions" messages (list them in section 8).
- Full suite: baseline plus the new tests, 0 failures.
- STATUS validation table: rows for EB smoothing and the joint Wald test. Remove the parts of backlog
  item 5 delivered this round.
- Version 0.24.0, with a CHANGELOG entry.

## 5. Commits

(1) The EB validation script and criterion; (2) its run and audit; (3) the joint-Wald validation script
and criterion; (4) its run and audit; (5) the library, the manifest changes and tests; (6) docs, STATUS,
version and the status table. Push. If you cannot open a PR, leave a body at `/tmp/round27-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite | | |
| EB criterion commit / result (posterior, Laird–Louis) | | |
| Joint Wald criterion commit / result | | |
| Engine, tests | | |
| Golden changes | | |
| Final suite | | |
| Exceptions | | |

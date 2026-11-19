# Round 31 plan: omnibus tests and group comparisons (ANOVA, ANCOVA, t-tests) for area data

**Goal.** Make multi-coefficient tests trustworthy, then build group comparisons on them.
Round 27's joint chi-squared Wald test was oversized (0.106–0.183 at nominal .10, even without
sampling error; `docs/audits/joint_wald_validation.md`). Every omnibus test (one-way ANOVA, ANCOVA,
interactions, spline terms) needs it. This round:

- **(A)** validates small-sample omnibus tests, and simultaneous pairwise comparisons;
- **(B)** ships the passing tests in `joint_wald`, and a new `compare_groups` MCP tool and manifest
  method for area-level data (regime A of `ROADMAP_STATISTICS.md`; do not read that file);
- **(C)** runs one exploratory MI/NY example.

Version 0.28.0 (current release v0.27.0). Baseline suite at v0.27.0: 1886 passed, 37 skipped.

**Non-goals.** No PUMS tests (Round 32), no rank tests (Round 33), no MANOVA (Round 39), no
registered study, no changes to registered manifests or their outputs, no new dependencies.

## 0. Ground rules

1. Branch `phase31/omnibus-groups` from `defaultBranch` in your own worktree (for example
   `/tmp/census-round31`). Do not merge, tag or release. Never rebase or force-push.
2. **No AI attribution** in commits or the PR body. Never print, log or commit `.env`, keys or tokens.
3. Read `CLAUDE.md` and `STATUS.md` first. `.venv/bin/python`, `OPENBLAS_NUM_THREADS=1`. No GitHub CI;
   every commit message ends with `[skip ci]`.
4. **Validation first:** script and criterion committed and pushed before the first full run; nothing
   changes after it. Smoke runs: at most 20 draws per cell, writing no audit files. The full run
   refuses unless its files match the criterion commit (as in Rounds 26 and 30).
5. Record impossibilities in section 8 and choose the option that changes least.

## 1. The test and its candidates

A hypothesis restricts q coefficients: `H0: Rb = 0` (R is q × p; n analysed areas; p parameters).
`b` is the full-sample estimate; `V = V_model + V_sampling`, where `V_model` is HC3 (linear) or the
existing GLM robust covariance, and `V_sampling` is 4/80 × Σ (b_r − b)(b_r − b)ᵀ over the 80 replicate
refits (as Round 27). `W = (Rb)ᵀ (R V Rᵀ)⁻¹ (Rb)`.

| ID | Statistic | Reference distribution |
| :--- | :--- | :--- |
| W0 | W (Round 27, failed) | χ²(q); kept only as the comparison row |
| W1 | W / q | F(q, n − p) |
| W2 | W / q with HC2 in place of HC3 in `V_model` | F(q, ν), ν from the Bell–McCaffrey / Satterthwaite approximation (Pustejovsky–Tipton "HTZ" form with each area its own cluster); GLMs use the working-weighted linearisation |
| W3 | W | wild score bootstrap (Kline–Santos): fit the null-restricted model once; Rademacher weights; 399 draws; studentised with the same `V_sampling` added in every draw |
| W4 (spatial) | Hotelling T² on the IM-8 per-cluster estimates of `Rb` (Round 30 C1): `T² = G · d̄ᵀ S⁻¹ d̄`, `F = (G − q)/(q(G − 1)) · T²` | F(q, G − q), G = 8; needs q ≤ 6 |

- W1–W3 assume independent areas. W4 targets the naive (observed-ACS) coefficients and needs every
  cluster full-rank (Round 30 rules: within-cluster constant terms absorbed; partial constancy refused).
- A failed fit (W4 rank failure, W3 non-convergent null fit) counts as a **rejection** under the null.
- **Pre-set selection:** among non-spatial candidates that pass, ship the simplest (W1, then W2, then
  W3). W4 ships separately if it passes, behind the existing `spatial_clusters` argument.

**Pairwise post hoc.** For k groups, all k(k−1)/2 differences of adjusted group means:
- **P1 Holm:** marginal t(n − p) tests on each difference, Holm-adjusted.
- **P2 simultaneous:** max-|t| critical value from `scipy.stats.multivariate_t` (df n − p) with the
  correlation of the differences implied by `V`; simultaneous intervals.

## 2. Validation (`scripts/omnibus_validation.py` → `docs/audits/omnibus_validation.md`/`.json`)

- **Geometry:** the 145 MI/NY counties and the frozen k = 8 assignment from
  `docs/audits/spatial_cluster_validation.json`. Import the Round 22/26/30 generators.
- **Fields:** independent, and spatial with range 100 km (Round 30's generator).
- **Groups:** a fixed "urbanicity" score per cell = a spatial field + independent noise (equal
  variances), cut into k equal-sized groups. Groups are exact (no sampling error), like a published
  classification. The noise keeps every group present in most clusters; W4 failures still count.
- **Designs** (q in brackets):
  1. `oneway4`: 4 groups [3];
  2. `oneway6`: 6 groups [5];
  3. `ancova4`: 4 groups + two covariates `x1`, `x2` (correlation 0.5), reliability 0.7, generated
     **independently of the groups**, so the naive adjusted group effect is 0 under the null [3];
  4. `twoway`: 2 × 3 groups (urbanicity halves × a second, independent 3-level field), testing the
     interaction [2];
  5. `spline3`, `spline5`: Round 27's centered natural splines in `x1` (reliability 0.85), testing all
     spline columns [3], [5].
- **Models and outcomes:**
  - linear: outcome is an ACS-type estimate: true value + sampling error (reliability 0.85), with
    replicates from `census.simulation.make_replicates` (refits are closed-form);
  - binomial and Poisson: external outcomes with no sampling error (trials and expected counts as in
    Round 30); replicate refits only where covariates have error.
  - Null: all tested coefficients 0. Alternative (power, informational): group effects spaced by
    0.15 SD of the outcome (linear) or 0.15 on the link scale; spline effect 0.3·sin(x1) as Round 27.
- **Cells:** 6 designs × 3 models × 2 fields = 36 cells; 2,000 null draws and 500 alternative draws
  per cell. Seed `20261218 + cell index` in that nesting order; bootstrap RNG
  `SeedSequence([20261218, cell, draw, 9])`.
- **Acceptance (pre-set), per candidate × model:** nominal-.10 null size within [.07, .13] in every
  cell it is judged on: W1–W3 on the independent cells; W4 on all cells. Report size at .05 as well.
- **Post hoc (judged on `oneway4` and `oneway6`, all models):** familywise error at .10 ≤ .13 under the
  global null, for P1 and P2, in the independent cells (and with W4's per-cluster covariance in the
  spatial cells, informational).
- **Informational:** power, the W0 row (expected to fail again), W1–W3 size in spatial cells (expected
  to be oversized), mean ν for W2, failure counts.
- **Runtime:** GLM cells with covariate error need 80 refits per draw. Use `multiprocessing` with
  fixed per-cell seeds so results do not depend on worker count; record wall time.

## 3. Engine

1. **`census.splines.joint_wald`** (manifest statistic `joint_wald`): use the selected candidate and
   return `df` (and `df_denominator`), the statistic, the p-value and the reference distribution name.
   Set `JOINT_WALD_VALIDATED` per model from the audit flags. Spline and joint tests become
   confirmatory-eligible only for models whose spline cells passed; otherwise they stay refused with
   the audit cited. The validated n is 145: below 145 analysed units, joint tests are exploratory only.
2. **Omnibus tests on factors:** `joint_wald` accepts a manifest `variable` that is a categorical
   factor (all its dummy columns) or an interaction term, not only splines.
3. **`compare_groups`** (library function in a new `census/group_compare.py`, manifest method
   `compare_groups`, MCP tool `compare_groups` in the `full` and `core` profiles):
   - arguments: `outcome`, `group`, optional `covariates`, `design` = `"two_group" | "oneway" |
     "ancova" | "twoway"` (with `group2` for twoway), `model` = `"ols" | "binomial" | "poisson"`
     (with `trials`/`exposure`), `posthoc` = `"holm" | "simultaneous" | "none"`, optional
     `reference_group`, optional `spatial_clusters`;
   - it fits through `fit_replicate` (so replicate handling, circularity and coverage rules are
     unchanged) and returns: adjusted group means (predictions at covariate means) with CIs; the
     omnibus test; pairwise differences with the chosen adjustment; effect sizes (partial η² and ω²,
     point estimates; their intervals are exploratory); group sizes; notes on the estimand,
     independence or IM-8, and validation status;
   - `two_group` is a t-test on the group indicator (single coefficient; already validated path);
   - a change outcome between two non-overlapping releases is allowed (variances add), which covers
     the repeated-measures case without a separate method;
   - refusals with an `error_code`: a group with fewer than 5 areas; a group constant within an IM-8
     cluster where the test needs it; unvalidated model/test combinations in confirmatory manifests.
4. **Diagnostics in every output** (information only, never a gate): group sizes, Levene /
   Brown–Forsythe spread check on residuals by group (`scipy.stats.levene`), and, for exact-data
   linear designs, the classical `scipy.stats.f_oneway` and Welch `statsmodels.stats.oneway.anova_oneway
   (use_var="unequal")` results labelled "ignores sampling error; comparison only".
5. **Docs mirrored together:** methods text, `docs/agent_protocol.md`, a new recipe
   `docs/recipes/group_comparison.md`, `get_recipe("group_comparison")`, MCP profile text. Guided
   result summaries must read well for small local models (one sentence per finding).

## 4. Exploratory example (`docs/studies/r31_group_comparison_example.md`)

Exploratory; author self-review, not independent; no registration.
- MI/NY counties, ACS 2018–2022: poverty rate (B17001) by three groups from CBSA membership
  (`census.boundaries.county_cbsa_membership`, the delineation `census.rpp` uses): counties in a
  metropolitan CBSA whose ACS population is 1 million+, other metropolitan, and nonmetropolitan.
- `oneway` with Holm and simultaneous post hoc; then `ancova` adjusting for the share aged 65+
  (B01001); W4 (IM-8) alongside if it passed.
- Show the guided MCP output as a small local model would see it. State the limits.
- Outputs in a key-scanned `r31_example_outputs.tar.gz` (attached at release).

## 5. Tests (`tests/test_round31.py`)

- Hand-computed W, F, df and p for a small design; W1 with a homoskedastic covariance equals
  `scipy.stats.f_oneway` on exact data; W2's ν equals a hand computation; W3 with a fixed seed is
  reproducible; W4's T² and F match a hand computation from known cluster estimates.
- Factor and interaction `variable`s select the right columns; q and df recorded.
- `compare_groups`: adjusted means equal predictions at covariate means; pairwise differences and
  Holm values by hand; simultaneous critical value matches `multivariate_t` for a known correlation;
  two-group equals the indicator coefficient's t-test; refusal codes.
- Gates follow the audit flags (patch where the check imports them); Round 27 refusals stay for
  anything not passed; below-145 joint tests are exploratory.
- An offline manifest run using `compare_groups` with `joint_wald` on a factor.

## 6. Acceptance

- Both goldens (`scripts/refactor_golden.py`, `scripts/run_golden.py`) change only in "supported"
  messages and additive diagnostics; list every change in `docs/audits/round31_compatibility.md`.
  Existing numbers are unchanged. Run goldens with the owner's `external_data` present (symlink it
  into the worktree for the run and remove the link after; never edit it).
- Full suite: baseline plus the new tests, 0 failures.
- STATUS: validation rows; backlog note (Round 27 joint tests resolved for passed models or not);
  the example in the studies table as exploratory.

## 7. Commits

1. Validation script and criterion (pushed before the full run). 2. Full run and audit. 3. Engine
and tests. 4. Example. 5. Docs, STATUS, version 0.28.0, CHANGELOG, section 8. Push. If you cannot
open a PR, leave the body at `/tmp/round31-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite | | |
| Criterion commit | | |
| W1 / W2 / W3 / W4 results (per model) | | |
| P1 / P2 familywise error | | |
| Engine, `compare_groups`, tests | | |
| Example | | |
| Golden changes | | |
| Final suite | | |
| Exceptions | | |

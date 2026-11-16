# Round 26 plan: spatial dependence, with large spatial clusters

**Goal.** County regressions show residual Moran's I of about 0.18–0.20. Conley HAC standard errors
failed their Round 22 validation (0.71–0.87 coverage at 150 km). This round pre-registers three
cluster-based alternatives on the **same simulation design** and ships whichever passes. It then re-checks
the Round 21b and 22 studies post hoc. Version 0.23.0.

**Non-goals.**

- No spatial random-effects (GLMM, BYM) models; they are the fallback if everything here fails.
- No change to registered results; post hoc re-checks are labelled as such.
- No new MCP tools; no new dependencies.

## 0. Ground rules

1. Branch `phase26/spatial-clusters` from `defaultBranch` (after Round 25 merges). Do not merge, tag or
   release. Never rebase or force-push. Work in your own clone or worktree.
2. **No AI attribution** in commits or the PR body (`Co-Authored-By`, `Generated with` or similar).
3. Never print, log or commit `.env` or any key or token.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. Do not run
   GitHub CI.
5. **Validation first.** The script and criterion are committed and pushed **before** the first full run.
   No seed, design or criterion changes after the run. Smoke runs: at most 20 draws per cell, writing no
   audit files.
6. Record impossibilities in section 9 and choose the option that changes least.

## 1. Candidates (each passes or fails on its own)

Clusters are fixed before any outcome is seen: **k-means on projected county centroids** (EPSG:5070 via `pyproj`).
`sklearn` is not a declared dependency, so use `scipy.cluster.vq.kmeans2` with 50 seeded restarts from seed
`20261126` and keep the lowest within-cluster sum of squares. Each cluster must hold at least 5 counties;
if the best solution violates that, take the next best. The number of
clusters `G` is a manifest argument.

| ID | Method | Interval |
| :--- | :--- | :--- |
| C1-8, C1-12 | Cluster-robust sandwich, CR1 scaling `G/(G−1)·(n−1)/(n−k)`, on the same scores as `fit_replicate` (OLS residuals; binomial `x·t(y−μ)`), G = 8 and G = 12 | `est ± t(G−1) · se` (Bester, Conley & Hansen 2011, J Econometrics 165:137–151) |
| C2-8 | Ibragimov–Müller: fit the model separately in each of G = 8 clusters, then a one-sample t-test on the G estimates | `mean ± t(G−1) · sd/√G` (2010, J Bus Econ Stat 28:453–468) |
| C3-12 | Wild cluster restricted bootstrap, G = 12, 999 draws with Webb six-point weights. Linear: WCR on residuals under H0. Binomial: the score bootstrap (Kline & Santos 2012, J Econometric Methods 1:23–41). | Coverage = share of draws where the test of `β = β_true` does not reject at 0.10 |

C2 fails a draw when any cluster fit fails; count that draw as non-coverage.

## 2. Validation design (`scripts/spatial_cluster_validation.py`)

Reuse the **Round 22 design exactly**, importing the generators from `scripts/spatial_hac_validation.py`
rather than copying them:

- 145 MI/NY county points;
- exponential covariance fields;
- linear `y = 1 + 0.5x + e`;
- binomial `logit p = −2.6 + 0.3x + u` with SD(u) 0.15 and the same lognormal trials.

The cells are design {linear, binomial} × range {0, 50, 100} km: six cells, 2,000 draws each. The seed is
`20261126 + cell index`, ordered linear 0/50/100, then binomial 0/50/100. Clusters are computed once, not
per draw.

**Acceptance per candidate (commit this before running):** 90% coverage ≥ 0.86 in all six cells. Also
report Monte Carlo SE, mean interval width relative to HC3 at range 0, and failed draws.

**Choice of default, pre-set:** among candidates that pass, pick the one with the smallest mean interval
width in the binomial, 100 km cell. Ties go to C1 (it gives an SE, which combines with ACS replicates).

**If nothing passes:**

- every candidate stays exploratory only;
- the audit records the result;
- STATUS backlog item 1 is updated to "spatial random effects next";
- skip section 3, and do section 4 as exploratory output only.

## 3. Engine (only for a passing candidate)

1. **Library.** `census/spatial_clusters.py`:
   - `spatial_clusters(geoids, level, acs_year, k, seed=20261126)`, which reuses
     `spatial_hac.unit_coordinates`;
   - `cluster_covariance(scores, bread_inv, labels)`;
   - `im_test(...)` and `wild_cluster_test(...)` as needed.
2. **`fit_replicate`.** It gains `spatial_clusters={"k": int, "method": "cr1_t"|"im"|"wcr"}`, which is
   mutually exclusive with `spatial_se` and with `scale: "robust"`. The sandwich replaces HC3 for the model
   part.
   - C1 is an SE and combines with replicates exactly as HC3 does today: `se_total = √(se_model² +
     se_sampling²)`, with the interval and p-value using `t(G−1)`.
   - If the default is C2 or C3, it gives no SE. That method is then allowed only with
     `target: "population"`, and refused (with a message) when any analysed variable has ACS replicates.
     The methods text says that sampling error is not included.
3. **Manifest.**
   - The analysis argument `spatial_clusters` is gated by `SPATIAL_CLUSTERS_VALIDATED[method]`: a
     confirmatory manifest is refused for a method that failed.
   - It is hashed; methods text gets one paragraph naming the cluster count, method, critical value and
     reference.
   - Add it to the method registry's `fit_replicate` check, with no new `if method ==` branch.
   - Record the cluster assignment (GEOID → label) in the bundle.
4. **Docs.**
   - An agent-protocol line and a recipe note in `regression_sampling_error`. Mirror the rules in the MCP
     text.
   - STATUS validation table: one row per candidate with its result.

## 4. Post hoc re-check (labelled post hoc, author self-review, not independent)

- Re-run the registered Round 21b (premature mortality) and Round 22 (low birth weight) manifests with
  the default candidate, through `run_variant`. Use `k` as validated; for C3, report p-values.
- Write `docs/studies/r26_posthoc_spatial_clusters.md`:
  - each hypothesis: the original Holm p-value and the clustered Holm p-value, and whether it still holds;
  - the residual Moran's I;
  - the cluster map, as a release attachment, not in the repo.
- Use cached data only. If a cache is missing, stop and report it; do not download.
- Outputs go in `r26_study_outputs.tar.gz` for the release, after a key scan.

## 5. Tests (`tests/test_round26.py`)

- The k-means assignment is deterministic and every cluster has at least 5 members.
- CR1 matches `statsmodels` `cov_type="cluster"` (with its `use_correction` defaults) on a linear
  example.
- Binomial cluster scores match a hand calculation.
- The `t(G−1)` interval is used.
- Manifest checks: the argument's validity, mutual exclusion with `spatial_se` and `robust`, the
  exploratory gate when the validated flag is False (patch the module the check imports from, and assert
  the refusal), and hash inclusion.
- An end-to-end offline run.

## 6. Acceptance

- The audit is committed after its criterion commit.
- `scripts/refactor_golden.py` and `scripts/run_golden.py` change only where the new argument appears
  (list the changes in section 9).
- The full suite: baseline plus new tests, 0 failures.
- Version 0.23.0 and a CHANGELOG entry.

## 7. Commits

(1) The validation script and criterion; (2) the run and the audit; (3) the engine and tests; (4) the
post hoc study; (5) docs, STATUS, version and the status table. Push. If you cannot open a PR, leave a body
at `/tmp/round26-pr-body.md`.

## 9. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite | | |
| Criterion commit | | |
| C1-8 / C1-12 / C2-8 / C3-12 results | | |
| Default chosen (or none) | | |
| Engine and tests | | |
| Post hoc R21b / R22 | | |
| Golden changes | | |
| Final suite | | |
| Exceptions | | |

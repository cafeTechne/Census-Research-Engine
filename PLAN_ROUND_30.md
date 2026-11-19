# Round 30 plan: spatial-cluster inference with ACS sampling error (IM with replicates and EIV)

**Goal.** Make spatially robust inference usable on the registered MI/NY county studies. Round 26 found
that only Ibragimov–Müller with eight fixed clusters (IM-8) holds coverage under spatial dependence, but
the engine refuses it whenever analysed variables carry ACS replicates, refuses EIV and Poisson, and
refuses designs with a state fixed effect. Every registered county study has at least three of these;
Round 29's mortality study (Poisson, ACS replicates, state fixed effect) states spatial dependence as its
main open limitation. This round:

- **(A)** validates two IM-8 procedures on data with ACS-type sampling error, and a rule for fixed effects
  that are constant within clusters;
- **(B)** ships whichever pass, behind the existing `spatial_clusters` argument;
- **(C)** re-runs the R21b, R22 and R29 (MI/NY) hypotheses with them, post hoc.

Version: 0.27.0 (current release v0.26.0). Baseline suite at v0.26.0: 1860 passed, 37 skipped.

**Non-goals.**

- No spatial random-effects, SAR or CAR models. If both candidates fail, record that and stop. Spatial
  random effects then become the next backlog step.
- No measurement-error correction for GLMs. Binomial and Poisson models get the naive-estimand
  procedure only (C1).
- No other cluster counts. Only k = 8 passed in Round 26; do not try other k.
- No changes to registered manifests or their outputs. No new MCP tools or dependencies.

## 0. Ground rules

1. Branch `phase30/im-acs` from `defaultBranch` (at or after `89edb41`). Do not merge, tag or release. Never rebase or
   force-push. Work in your own clone or worktree, never in the owner's checkout.
2. **No AI attribution** in commits or the PR body. Never print, log or commit `.env` or any key or token.
3. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. No GitHub CI.
4. **Validation first:** the script and criterion are committed and pushed before the first full run.
   Nothing changes after it. Smoke runs: at most 20 draws per cell, writing no audit files. The script
   refuses a full run unless its files match the criterion commit (as in Round 26).
5. Record impossibilities in section 8 and choose the option that changes least.

## 1. Why the Round 26 refusals can be relaxed, and what must be shown

IM fits the model separately in each cluster and runs a t(G−1) test on the G cluster estimates. ACS
sampling errors are independent between counties, so their effect on each cluster estimate is part of
the between-cluster spread that IM already measures. No additive ACS term is needed. Two problems remain.
Both are addressed by simulation, not by argument:

1. **Attenuation.** Error in covariates biases every cluster estimate the same way, so IM centres on the
   wrong value. That includes control covariates: error in a control biases the tested coefficient even
   when its own true value is 0. EIV (Fuller's moment estimator, `fit_eiv`) removes the bias using the
   replicate error covariances `S_i`, `s_i`. Within a cluster of about 12–25 counties it may be unstable.
2. **Fixed effects.** The k = 8 assignment on MI/NY never mixes states (checked: no cluster spans both).
   A state indicator is therefore constant within every cluster. Its effect is absorbed by the cluster
   intercept, so dropping it inside the per-cluster fit leaves the other coefficients' estimand unchanged.

## 2. Candidates

| ID | Models | Per-cluster estimator | Target of the 90% interval |
| :--- | :--- | :--- | :--- |
| C1 | OLS, binomial, Poisson (offset `log E`, E fixed) | the existing fit on the observed ACS estimates (naive) | the naive coefficient's probability limit `β*` |
| C2 | OLS | Fuller EIV with that cluster's own `S_i`, `s_i` from the replicates | the true coefficient `β` |

- **Common to both:**
  - the IM estimate is the unweighted mean of the 8 cluster estimates;
  - the SE is their standard deviation / √8, with t(7) intervals and p-values;
  - one-sided p-values follow the hypothesis direction.
- **Within-cluster constant columns:**
  - a formula term whose columns are constant within every cluster is dropped from the per-cluster fits,
    and its coefficient is reported as not estimable under IM;
  - a hypothesis on such a term is refused;
  - if such a term is constant in some clusters but not others, the fit is refused.
  - This replaces the Round 26 "same full-rank design in every cluster" refusal for this case only.
- **C2 failure handling:** a cluster whose corrected moment matrix is not positive definite makes the
  whole C2 fit fail. That counts as non-coverage in validation and is a refusal in the engine. Never drop
  the cluster, and never fall back to the naive estimate.
- **Why C1's target is `β*`:** it is the estimand R22 registered, since its binomial models used ACS
  estimates as observed. When covariate errors are independent of the outcome's error and the model has
  a single error-prone covariate, `β* = 0` exactly when `β = 0`. Report this, but do not rely on it for
  models with error-prone controls.

## 3. Validation (`scripts/im_acs_validation.py` → `docs/audits/im_acs_validation.md`/`.json`)

- **Geometry:** the Round 22/26 MI/NY design and the frozen k = 8 assignment from
  `docs/audits/spatial_cluster_validation.json`. Import its generators, as Round 26 did.
- **Covariates:**
  - true `x1` and `x2` are spatial fields from the Round 22 generator with correlation 0.5;
  - there is a state effect: NY indicator coefficient 0.3 (linear) or 0.2 (logit).
- **Outcomes:**
  - linear: `y = 1 + 0.5·x1 + 0.5·x2 + 0.3·NY + error`;
  - binomial: `logit p = −2.6 + 0.3·x1 + 0.3·x2 + 0.2·NY + 0.15·error`, with trials as in Round 22;
  - Poisson: `deaths ~ Poisson(E·exp(0.3·x1 + 0.3·x2 + 0.2·NY + 0.15·error))`, with expected counts
    `E = max(5, round(lognormal(log 100, 1)))` drawn once per cell (like Round 22's trials), fixed and
    known to the fit as the offset. `error` is the same spatial field as in the binomial model;
  - the outcome is external, so it has no sampling error and no replicates.
- **Sampling error:**
  - observed `xj = true xj + u_ij`, with `u_ij ~ N(0, se_ij²)` independent across counties;
  - `se_ij` is drawn once per cell, lognormal with log-SD 0.5, scaled so the average reliability
    `var(x)/(var(x)+mean se²)` equals the cell's value;
  - replicates come from `census.simulation.make_replicates(observed, se, rng)`, with cross-variable
    correlation 0.3.
- **Cells:** model {linear, binomial, Poisson} × range {0, 100 km} × reliability {0.9, 0.7}: 12 cells,
  2,000 draws each. Seed `20261201 + cell index`, nested in that order (linear 0–3, binomial 4–7,
  Poisson 8–11). Bootstrap or other RNG uses an
  independent `SeedSequence([20261201, cell, draw, 7])`.
- **Runs:** C1 runs in all 12 cells; C2 runs in the 4 linear cells.
- **Target `β*` for C1:**
  - compute it before the full run from one reference dataset of 400,000 independent areas with the same
    marginal distributions;
  - for linear cells, check it against the closed form for the naive regression;
  - commit the values with the criterion.
- **Acceptance (pre-set), for each candidate × model separately:** 90% coverage of `x1`'s target ≥ 0.86
  in every cell it runs in. A failed fit counts as non-coverage.
- **Report (informational):**
  - C1's coverage of the true `β` (expected to fail at reliability 0.7);
  - C2's fit-failure rate;
  - mean interval widths;
  - one-sided size at nominal 0.05 in a null variant with `β1 = 0`, for C2 and for single-covariate C1.

## 4. Engine

- **`fit_replicate`:** if C1 passes for a model, IM-8 with `target="population"` accepts analysed
  variables with replicates.
  - The note states the estimand: "coefficient on the ACS estimates as observed; attenuated toward 0 if
    covariates have sampling error, and not corrected".
  - Poisson: if C1 passes for Poisson, lift the "EIV/Poisson were not validated" refusal for Poisson
    only (`exposure` gives the fixed offset in every cluster fit); EIV stays refused unless C2 passes.
    `spatial_clusters` stays mutually exclusive with `scale="robust"`.
  - `se_cluster_mean` stays the SE column. ACS replicates are not added; the methods text says why.
- **`fit_eiv`:** new keyword `spatial_clusters`, with the same check as `fit_replicate`.
  - Method `im` only, k = 8, OLS only. It refuses `cluster`, `spatial_se`, `cluster_se` and `weights`.
  - If C2 fails, it stays refused, with the audit cited.
  - The full-sample EIV estimate and its usual SE are reported alongside, as a reference, not as the
    test basis.
- **Within-cluster constant-term rule:** applies in both functions, per section 2.
- **Manifests:** `spatial_clusters` already passes through `args`. A confirmatory manifest may use IM-8
  only for a passed model and procedure; otherwise it is refused, with the audit cited.
- **Docs:** update the methods text, `docs/agent_protocol.md`, the regression recipe and the MCP profile
  text together.

## 5. Post hoc re-checks (`docs/studies/r30_posthoc_im_acs.md`)

Post hoc; author self-review, not independent. Use cached inputs only, with HTTP blocked. Verify the
cached analysed-file hashes first. Registered outputs are not changed.

- **R21b:**
  - H1–H4 with C2, if it passed;
  - the state factor is dropped within clusters;
  - Holm over the registered family;
  - compare with the registered EIV results.
- **R22:**
  - H1–H3 with C1 binomial, if it passed;
  - state the naive estimand;
  - Holm as registered.
- **R29 (MI/NY only):**
  - H1–H3 with C1 Poisson, if it passed; the offset `log E_h` fixed as registered; the state factor
    dropped within clusters; Holm over H1–H3 as registered; state the naive estimand;
  - inputs: the analysed frame and replicates in the v0.26.0 release attachment `r29_study_outputs.tar.gz`
    (`r29/mi_ny/confirmatory/analysed/`; a local copy is at `/tmp/r29_study_outputs.tar.gz`); verify their SHA-256 against that bundle's `run.json` first;
  - clusters are assigned on all 145 counties before complete-case filtering (the engine's rule), so
    H2 runs without its 13 suppressed counties; if a cluster then cannot be fitted, H2 is "unavailable";
  - all WONDER output rules apply (`STATUS.md`): no county death counts or derived values for suppressed
    counties in any output; per-cluster estimates are coefficients only;
  - OH/PA is not re-checked: the validation geometry is MI/NY only. Say so in the report.
- **Report:** a table with the registered Holm p, the IM-8 Holm p and "still holds under IM-8?". Also give
  the per-cluster estimates and the residual Moran's I of each reference fit.
- **Failures:** if a candidate failed, the corresponding row says "unavailable". No p-values are invented.
- **Archive:** outputs go in a key-scanned archive that also passes `census.wonder_outputs.audit_outputs` for the R29 part (`r30_study_outputs.tar.gz`), attached at release. The
  report names that file, not a `/tmp` path.

## 6. Tests (`tests/test_round30.py`)

- **C1 and C2 estimators:**
  - the C1 cluster estimates equal separate `statsmodels` fits per cluster (OLS, binomial, and Poisson
    with the offset);
  - each C2 cluster estimate equals `fit_eiv` run on that cluster's rows alone;
  - the IM mean, SE, t(7) interval and one-sided p are checked by hand.
- **Constant-term rule:**
  - the state factor is dropped within clusters and reported as not estimable;
  - a hypothesis on it is refused;
  - a term constant in some clusters but not others is refused.
- **C2 fit failure:** a non-positive-definite moment matrix in one cluster refuses the whole fit.
- **Gates:**
  - the gates follow the audit flags (patch where the check imports them);
  - Round 26 refusals stay in place for anything not passed;
  - `fit_eiv` refuses the incompatible arguments.
- **End to end:** an offline manifest run with IM-8 EIV and a state factor.

## 7. Acceptance and commits

- Both goldens change only in the "supported" messages and in additive diagnostics. List every change
  (as in `docs/audits/round27_compatibility.md`). Existing numbers are unchanged.
- **Full suite:** baseline plus the new tests, 0 failures.
- **STATUS:**
  - add the validation rows;
  - update backlog item 1: resolved for the passed procedures, otherwise "spatial random effects next";
  - add the post hoc outcome to the studies table.
- **Version and CHANGELOG:** bump the version and add a CHANGELOG entry.
- **Commits:**
  1. the validation script, criterion and committed `β*` values;
  2. the run and audit;
  3. the engine and tests;
  4. the post hoc report;
  5. docs, STATUS, version and the status table.
- **Push.** If you cannot open a PR, leave a body at `/tmp/round30-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite | | |
| Criterion commit, `β*` values | | |
| C1 linear / C1 binomial / C1 Poisson / C2 results | | |
| Engine gates and tests | | |
| Post hoc R21b / R22 / R29 MI/NY | | |
| Golden changes | | |
| Final suite | | |
| Exceptions | | |

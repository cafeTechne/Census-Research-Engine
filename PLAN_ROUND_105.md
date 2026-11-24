# Round 105 plan: second wave of exploratory-measure repairs (validation-first)

**Goal.** Diagnose and repair the next five exploratory failures from Rounds 83, 85, 86, 91 and 98 (backlog
N89–N93). Each candidate targets a concrete mathematical defect found in the frozen cores, is evaluated
**validation-first** on the exact DGP cells where its predecessor failed (90% coverage ≥ .86; nominal-.10 size
≤ .13), and is wired into the engine only if it passes. Failed candidates stay exploratory with their diagnosis
recorded. Version 0.101.0. Both manifest goldens stay byte-identical.

## 1. Five diagnosed defects and repair candidates (`census/repairs105_core.py`)

1. **Continuous RDD under strong curvature (Round 98, `rdd_validation.md`; N89):**
   - *Defect:* `rdd_core.rdd` uses the MSE-optimal IK bandwidth `h_ik ~ n^(-1/5)`, which leaves non-negligible
     local-quadratic smoothing bias under strong curvature (`.78–.80` for `n ≤ 10,000`).
   - *Repair (`R1b`):* Calonico–Cattaneo–Farrell (2020) coverage-error-rate (CER) bandwidth `h_cer = h_ik * n^(-1/20)`
     with local-quadratic robust bias-corrected intervals.
2. **PUMS replicate Wald homogeneity test (Round 83, `stratified_validation.md`; N90):**
   - *Defect:* `stratified_core.mh_replicate` compares the replicate Wald statistic against `chi2(K - 1)`,
     ignoring covariance estimation uncertainty from `R = 80` replicates (size up to `.151` at nominal `.10`).
   - *Repair (`H2b`):* Korn–Graubard (1990) Hotelling `F(K - 1, R - K + 1)` reference distribution:
     `F_stat = (R - K + 1) / (R * (K - 1)) * stat`.
3. **Designation accuracy PPV predictive interval (Round 85, `designation_validation.md`; N91):**
   - *Defect:* `designation_core.expected_accuracy` uses conditional Poisson-binomial variance `sum P(1 - P)`
     holding Fay–Herriot `(β̂, Â)` fixed, ignoring shared hyperparameter uncertainty across tracts (`.54–.85`).
   - *Repair (`Q2b`):* parametric bootstrap over the Fay–Herriot model (`B = 100` draws of latent `θ*` and
     refitted `(β̂*, Â*)`) to propagate hyperparameter uncertainty into the realized PPV predictive interval.
4. **Probabilistic misclassification interval (Round 86, `bias_analysis_validation.md`; N92):**
   - *Defect:* `bias_analysis_core.probabilistic` adds random error `se(A, B, C, D)` from the *corrected* cells,
     omitting the `1 / (Se + Sp - 1)^2` sampling-variance inflation from inverting the misclassification matrix
     (`.76–.83` under correct priors).
   - *Repair (`M1b`):* draw observed-table sampling replicates `(a*, b*, c*, d*)` first (binomial per exposure
     arm for outcome misclassification, multinomial for exposure misclassification) and pass them *through*
     `corrected_table(..., se, sp, kind)` (Fox, MacLehose & Lash 2021).
5. **IP-weighted marginal structural models (Round 91/104, `msm_validation.md` / `repairs104_validation.md`; N93):**
   - *Defect:* Round 104's `M3` reached 34/36 cells ≥ `.86` (`.850–.918`) but kept `+0.08–0.13` bias at duration 1
     from rare-event logistic MLE slope inflation in the pooled treatment model.
   - *Repair (`M4`):* Firth-penalized logistic regression for the pooled treatment model + baseline-`L0`
     stabilization + delete-one-unit cluster jackknife `t(G - 1)`.

## 2. Validation (`scripts/repairs105_validation.py`, `docs/audits/repairs105_criterion.md`)

- Fixed pass rule: 90% coverage ≥ `.86` in every cell (nominal-.10 size ≤ `.13` for `H2b`).
- Write `docs/audits/repairs105_validation.md` and `.json` with frozen SHA-256 hashes.
- Wire only passing repairs into `census/rdd.py`, `census/stratified.py`, `census/designation.py`,
  `census/bias_analysis.py`, `census/msm.py`.

## 3. Docs, tests and acceptance

- Update `docs/agent_protocol.md` → `mcp_server.py` (`sync_rule_text.py --check`), `STATUS.md`, `CHANGELOG.md`
  (0.101.0), `ROADMAP_BACKLOG.md` (N89–N93), `docs/audits/round105_compatibility.md`, `tests/test_round105.py`.
- Both goldens byte-identical; targeted and affected round tests pass.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Frozen core, criterion, script | done | `repairs105_core.py`, `repairs105_criterion.md`, `repairs105_validation.py` |
| Simulation run & audit | done | `docs/audits/repairs105_validation.md` (178.1s; R1b & M1b pass; H2b/Q2b/M4 fail) |
| Wire passing repairs into engine | done | `rdd.py` (R1b CER bandwidth), `bias_analysis.py` (M1b propagated sampling) |
| Docs, rule sync, tests, goldens | done | `sync_rule_text.py --check` green; `run_golden` byte-identical |
| Exceptions | none | see `docs/audits/round105_compatibility.md` |

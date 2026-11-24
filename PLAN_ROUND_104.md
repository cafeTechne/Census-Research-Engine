# Round 104 plan: repairing exploratory measures (validation-first) and manifest support for validated methods

**Goal.** Two linked objectives (backlog N83–N88):
1. **Diagnose and repair exploratory measures from Rounds 83–102** where validation audits show a concrete,
   fixable finite-sample or approximation defect (not a recorded fundamental limit from `ROADMAP_BACKLOG.md`
   section 2). Every repair is **validation-first**: diagnose the failure mechanism, implement the candidate in a
   frozen core, commit the criterion and simulation script (`tag criterion-r104`) *before* the full run, and
   promote only candidates that pass the fixed rule (90% coverage ≥ .86; nominal-.10 size ≤ .13). Any candidate
   that still fails stays exploratory and its limit is recorded.
2. **Pre-registered manifest support** for the validated area-level methods from Rounds 41–100 (plus any Part 1
   repair that passes), closing the gap between MCP/library workflows and `create_manifest` / `run_manifest`.

Version 0.100.0. Branch `phase104/repairs-and-manifests`.

**Ground rules (unchanged):**
- Validation first: commit `scripts/repairs104_validation.py`, the frozen candidate core and the criterion before
  running the full simulation; no tuning after seeing results.
- Recorded limits (`ROADMAP_BACKLOG.md` section 2: ITS < 17, Theil T, G2 > 7 covariates, D > .75, etc.) are not
  reopened.
- Registered manifests in `examples/manifests/` stay byte-fixed. `scripts/run_golden.py` stays byte-identical;
  `scripts/refactor_golden.py` may differ only in supported-method / supported-statistic messages.
- No automated WONDER access; no sub-national counts 1–9 or derived values in any output.
- No AI attribution in commits, PRs or release notes; merges and releases wait for the owner's explicit yes.

---

## Part 1: Diagnosing and repairing exploratory measures (validation-first)

Audit review (`docs/audits/`) identifies five exploratory failures from Rounds 91–102 with concrete, testable
repair hypotheses:

### 1.1 Meta-analysis repairs (Round 102, `meta_validation.md`; N83)
- **What went wrong:**
  - Prediction intervals (`P1`) covered .76–.89 at moderate heterogeneity (`I² = 0.25–0.50`) because
    `t_{k-2} √(τ̂² + SE²)` ignores uncertainty in `τ̂²` (which is frequently underestimated or 0).
  - Meta-regression (`R1`) covered `.821` at `k = 10, I² = 0.5, β = 0.2` (passed everywhere at `k ≥ 20`: .865–.917)
    because un-truncated Knapp–Hartung can shrink SEs when residual `q < 1`.
  - Egger's test (`E1`) rejected `.120` at nominal `.10` for `k = 10, I² = 0.75` (passed at `k ≥ 20`: ≤ .107).
- **Repair candidates (`census/meta_repairs_core.py`):**
  - **P2 (prediction interval):** Nagashima–Noma–Furukawa (2019) parametric bootstrap prediction interval using
    the Q-profile / REML `τ²` distribution (which already passed in H1).
  - **R2 (meta-regression):** truncated Knapp–Hartung (`max(1, q)`, matching Round 48's pooling repair); test at
    `k ∈ {10, 20, 40}` (if `k = 10` still fails, validate the `k ≥ 20` gate).
  - **E2 (small-study test):** random-effects weighted Egger regression (incorporating `τ̂²` in the weights) and
    `k ≥ 20` gate.

### 1.2 Nearest-neighbour matching ATT (Round 99, `matching_validation.md`; N84)
- **What went wrong:** `M1-ATT` missed narrowly at `N = 145` with strong propensity (`1.502`): coverage `.852` /
  `.858` (0.008 below `.86`), while `N = 600` passed (.880–.914). With limited overlap, a few control units are
  reused many times, making the normal `z` critical value anti-conservative.
- **Repair candidate (`census/matching_repairs_core.py`):**
  - **M1b-ATT:** Abadie–Imbens bias-corrected matching with effective-sample-size `t(df_eff)` critical value
    (based on the control-weight Kish effective sample size `n_eff = (Σ w_i)² / Σ w_i²`) and `M = 4` matches
    (reduces control-reuse variance), tested on the exact Round 99 cells (`N ∈ {145, 600}`, propensity `0.5 / 1.502`).

### 1.3 BYM2 disease mapping relative-risk intervals (Round 96, `disease_mapping_validation.md`; N85)
- **What went wrong:** 15 of 16 cells covered `.840–.897`, but `counties, φ = 0.2, σ = 0.2, median E = 5` fell to
  `.796` (B1) / `.790` (B2) because the log-posterior of `σ` hits the zero boundary under sparse counts and small
  true variance, causing Laplace plug-in/coarse-grid intervals to under-state hyperparameter uncertainty.
- **Repair candidate (`census/disease_mapping_repairs_core.py`):**
  - **B3:** finer hyperparameter integration grid (B2) with a boundary-avoiding PC prior on `σ` plus a
    variance-inflation check for sparse counts, tested on the exact Round 96 cells; pre-register a fallback gate
    (`median E ≥ 15`) if the sparse `E = 5, σ = 0.2` cell remains below .86.

### 1.4 IP-weighted marginal structural models (Round 91, `msm_validation.md`; N86)
- **What went wrong:** Coverage was `.805–.881` across `K = 12, 18` with a persistent `+0.08` to `+0.12` bias
  *even when `Feedback = 0`*, plus percentile cluster-bootstrap under-coverage on `G = 51` units.
- **Diagnostic & repair candidate (`census/msm_repairs_core.py`):**
  - First diagnose the exact source of the `Feedback = 0` bias in `census/msm_core.py` (treatment-model
    specification, numerator/denominator stabilization, or censoring/alignment of lagged `L`).
  - **M3:** corrected weight specification + studentized cluster-jackknife / `t(G - 1)` interval on the exact
    Round 91 cells.

### 1.5 WHO inequality monitoring mean differences (Round 94, `inequality_monitoring_validation.md`; N87)
- **What went wrong:** `mdm_w` and `mdb_w` passed everywhere at `c = 0.1` (.881–.969) and at `large` spread
  (.874–.976), failing only when `Spread = small` and `c ≥ 0.3` because `|r_i - r_ref|` has positive folded-normal
  bias when sampling noise exceeds group spread.
- **Repair candidate (`census/inequality_monitoring_repairs_core.py`):**
  - **MD2:** replicate bias-corrected `mdm_w` / `mdb_w` (analogous to Round 50's segregation bias correction)
    and/or a pre-registered `max_group_cv ≤ 0.10` validation gate, tested on the exact Round 94 cells.

### 1.6 Validation protocol (`scripts/repairs104_validation.py`)
- Commit frozen cores, script and `docs/audits/repairs104_criterion.md` at tag `criterion-r104` before running.
- Pass rule (fixed): 90% coverage ≥ .86 in every cell of the claimed scope (and nominal-.10 size ≤ .13 for E2).
- Write `docs/audits/repairs104_validation.md` and `.json`. Wire only passing repairs into the engine (`VALIDATED`
  flags, docstrings, `STATUS.md`, recipes); failed candidates stay exploratory with their diagnosis recorded.

---

## Part 2: Pre-registered manifest support for validated methods (N88)

After Part 1 settles, wire the validated area-level methods into `census/manifest/methods.py` (all strictly opt-in
for existing methods; exploratory options refused in confirmatory manifests unless `exploratory: true`):

1. **`estimate_effect`** (Rounds 41, 47, 89, 90, 99): `kind="treatment" | "matching" | "iv" | "mediation"`;
   statistic `effect`. Enforces manifest-level `causal_question`, `dag` backdoor checks, R1/R2 circularity,
   positivity gate (`extreme_share < 0.05` or `weights="truncated" | "overlap"`), and validated matching routes
   (`nn` ATE, `cem`, `ps`; plus `nn` ATT only if M1b-ATT passes Part 1).
2. **`spatial_scan`** (Round 81): county Kulldorff Poisson scan with mechanical `prespecified=True`,
   `max_share=0.5`, exact-denominator gate, WONDER `exclude` + `exclude_rule` enforcement; statistic `primary_rr`.
3. **`stratified`** (Round 83): county-count Mantel–Haenszel (`mh_rr`, `mh_or`, `mh_rd`, `mh_irr`), `reri`, and
   Breslow–Day–Tarone `homogeneity` (Woolf RR homogeneity stays diagnostic-only).
4. **Opt-in validated args on existing methods:**
   - `fit_replicate`: `args.marginal` (Round 84 g-computation `marginal_rr`, `marginal_rd`,
     `attributable_fraction`) and `args.impute` + `args.impute_method: "pmm" | "norm"` (Round 100 FCS).
   - `disparity`: `args.who_measures: true` and `args.compare_years: [y1, y2]` (Round 94 validated `par`,
     `par_pct`, `sii`, release changes; plus `mdm_w`/`mdb_w` only within any scope validated by MD2 in Part 1).

## Part 3: Docs, tests and acceptance

- **Methods text & docs:** `census/manifest/methods_text.py`, `docs/recipes/preregistered.md`, updated recipes for
  any Part 1 repairs, `docs/agent_protocol.md` → `mcp_server.py` (`scripts/sync_rule_text.py --check`),
  `README.md`, `ROADMAP_BACKLOG.md` (N83–N88), `STATUS.md`, `CHANGELOG.md` (0.100.0), version bump.
- **Tests (`tests/test_round104.py`):**
  - Part 1: exact checks and `VALIDATED`-flag-matches-audit tests for every repair candidate;
  - Part 2: `create_manifest` + `run_manifest` end-to-end tests for `estimate_effect`, `spatial_scan`,
    `stratified`, `fit_replicate(marginal/impute)` and `disparity(who_measures)`, plus confirmatory refusals.
- **Goldens:** `scripts/run_golden.py` byte-identical; `scripts/refactor_golden.py` differs only in
  supported-method / supported-statistic messages (`docs/audits/round104_compatibility.md`).
- **Suite:** `OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q` passes with zero failures.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Part 1: diagnose & freeze criterion | done | `census/repairs104_core.py`, `docs/audits/repairs104_criterion.md` |
| Part 1: simulation run & audit | done | `docs/audits/repairs104_validation.md` (159.1s; P2/R2/E2/M1b-ATT/B3_E30 pass; M3/MD2 fail) |
| Part 1: wire passing repairs into engine | done | `evidence.py`, `matching.py`, `disease_mapping.py`; M3/MD2 stay exploratory |
| Part 2: manifest methods `estimate_effect`, `spatial_scan`, `stratified` | done | plus opt-in `fit_replicate` (`marginal`, `impute`) & `disparity` (`who_measures`) |
| Part 3: methods text, recipes, rule sync, docs | done | `sync_rule_text.py --check` green |
| Goldens, tests, suite | done | `run_golden` byte-identical; `refactor_golden` method-list diff only |
| Exceptions | none | see `docs/audits/round104_compatibility.md` |

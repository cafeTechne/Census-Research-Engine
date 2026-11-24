# Round 103 plan: agent access, routing contract and release hygiene after Rounds 76–102 (no new statistics)

**Goal.** Close the agent-access, routing and documentation gaps left after the 27-round run of Rounds 76–102
(v0.72.0–v0.98.0, 21 rounds merged since v0.77.0). Like Round 64 (agent access) and Round 75 (manifest/docs
consolidation), this round adds **no new statistical methods**: every estimator wired here already has its
validation record in `STATUS.md` and `docs/audits/`. Version 0.99.0. Branch `phase103/agent-access-hygiene`.
No simulation; both manifest goldens must stay byte-identical.

**Ground rules (unchanged):**
- Validation labels come straight from the existing audits (`demography_validation.md`, `surveillance_validation.md`,
  `inequality_monitoring_validation.md`, `spatial_models_validation.md`). Never upgrade an exploratory method.
- No automated WONDER access; no sub-national counts 1–9 or derived values in any output.
- No AI attribution in commits, PRs or release notes; merges and releases wait for the owner's explicit yes.
- Engine rules live in `docs/agent_protocol.md` and are synced into `mcp_server.py` by `scripts/sync_rule_text.py`.

## 1. MCP and CLI routes for Python-only methods from Rounds 93–101

Four validated or documented capabilities added in Rounds 93–101 are currently reachable only from Python:

1. **New full-profile umbrella tool `demography_analysis`** (tool count 80 → 81; added to `_WORKFLOW_TOOLS` in
   `census/__main__.py` and `TOOL_SOURCES` in `census/references.py`; `core` profile stays at 16 tools):
   - `kind="life_table"` → `census.demography.life_table_from_wonder` (abridged life table with validated Chiang II
     `e0` and `e65` intervals, Round 101);
   - `kind="arriaga"` → `census.demography.arriaga_from_wonder` (exact age- and cause-specific life-expectancy
     decomposition, Round 101);
   - `kind="age_quality"` → `census.demography.age_quality` (counts) or `age_quality_pums` (PUMS with replicate SEs)
     for Whipple, Myers and UN age-sex accuracy indices (Round 101);
   - `kind="survival_migration"` → `census.demography.census_survival_net_migration` (descriptive net migration by
     age from two censuses, Round 101);
   - `kind="ypll"` → `census.surveillance.ypll_from_wonder` / `ypll_table` (validated age-adjusted YPLL-65/75
     Fay–Feuer intervals with WONDER suppression bounds, Round 95).
   - Wrapper lives in `census/workflows_inference.py` (or `census/workflows_demography.py` re-exported there). Every
     result carries `validated`, `method_sources`, `summary`, `next_step` and the existing WONDER disclosure checks.

2. **Extend existing umbrella tools** (zero extra tools):
   - `disparity_measures`: expose Round 94's `double_disaggregation` and `priority_quadrants` (from
     `census.inequality_monitoring`) via `kind="double_disaggregation" | "priority_quadrants"` (preserving the
     default `kind="disparity"` / `who_measures` behaviour unchanged).
   - `spatial_model`: expose Round 93's `diversity_index` (from `census.spatial_models`, exploratory) via
     `kind="diversity"`.

3. **Method attribution (`census/references.py`):**
   - Register `demography_analysis` in `TOOL_SOURCES` (IUSSP 2013; Chiang 1984; Arriaga 1984; CDC SS1000; Fay and
     Feuer 1997; `demography_validation.md`; `surveillance_validation.md`).
   - Confirm `disparity_measures` and `spatial_model` include the WHO (2013) and Walker (2023) sources.
   - The Round 88 coverage test verifies every registered tool has sources.

## 2. Extend the agent routing contract (`docs/agent_routing.md` and `tests/test_agent_routing.py`)

`docs/agent_routing.md` has not been updated since Round 64 (15 rows, R1–R15). Add offline-tested rows **R16–R30**
covering the major capabilities added in Rounds 76–102, checking for each row that (a) the tool exists in the
named profile, (b) the named recipe or server instructions mention it, and (c) the call returns the expected
`validated` / `exploratory` / `refused` flag on offline fixtures:

| id | Research question | Profile | Tool and key arguments | Expected | Guidance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R16 | Between-group disparity (ACS rates, CV ≤ .30) and WHO PAR | full | `disparity_measures(who_measures=True)` | validated | health_inequality |
| R17 | WHO mean difference from overall mean or best group | full | `disparity_measures(who_measures=True)` | exploratory (MD flag) | health_inequality |
| R18 | Joinpoint count in a 20-year annual rate series + EARS C2 aberration | full | `joinpoint(aberration="ears_c2")` | validated (count & C2) | policy_change |
| R19 | Staggered policy adoption across states (Sun–Abraham) | full | `difference_in_differences(design="staggered")` | validated | policy_change |
| R20 | Policy panel with treatment-confounder feedback (MSM) | full | `difference_in_differences(design="msm")` | exploratory | policy_change |
| R21 | Triple-difference policy design (eligible vs ineligible groups) | full | `difference_in_differences(design="triple")` | validated | policy_change |
| R22 | Stratified 2×2 tables: Mantel–Haenszel RR/OR/RD and RERI | full | `stratified_analysis` | validated | confounding |
| R23 | Area threshold designation probability (Fay–Herriot posterior) | full | `designation_accuracy` | validated (prob); exploratory (rules) | small_area |
| R24 | Unmeasured-confounding E-value vs probabilistic misclassification | full | `bias_analysis` | validated (E-value); exploratory (misclass) | reporting |
| R25 | Causal effect with overlap/truncated weights and positivity check | full | `estimate_effect(weights="overlap")` | validated | causal |
| R26 | Nearest-neighbour matching (ATE) vs ATT on limited overlap | full | `estimate_effect(kind="matching")` | validated (ATE); exploratory (ATT) | causal |
| R27 | Sharp RDD at an age cutoff on PUMS with replicate weights | full | `regression_discontinuity` | validated (discrete PUMS) | causal |
| R28 | BYM2 spatial disease map: exceedance probabilities vs RR intervals | full | `spatial_model(kind="disease_map")` | calibrated (exceedance); exploratory (RR CI) | spatial_patterns |
| R29 | FCS multiple imputation (PMM) with 3 incomplete variables | core | `fit_model(impute=[...], impute_method="pmm")` | validated | regression_sampling_error |
| R30 | Life table (`e0`/`e65`) and YPLL-75 from WONDER age-group exports | full | `demography_analysis(kind="life_table" \| "ypll")` | validated | external_health_outcome |

## 3. Documentation, rule-text sync and backlog hygiene

- **Rule text:** add `demography_analysis` and the `disparity_measures` / `spatial_model` extensions to the
  marked rules block in `docs/agent_protocol.md`, run `scripts/sync_rule_text.py`, and confirm `--check` passes.
- **Recipes:** update `external_health_outcome` (point life tables, Arriaga, age quality, YPLL to
  `demography_analysis`), `health_inequality` (`double_disaggregation`, `priority_quadrants`), and
  `spatial_patterns` (`spatial_model(kind="diversity")`).
- **`README.md`:**
  - fix stale counts (`80 MCP tools` → `81`, `25 task guides` → `26`, `71 tools` at repository layout → `81`);
  - add rows/entries in the Inference table for Rounds 89–102 (`estimate_effect` matching/positivity/DAG,
    `difference_in_differences` triple/MSM, `fit_model` FCS imputation, `spatial_model` BYM2/CV/MAUP/diversity,
    `demography_analysis` life tables/Arriaga/age quality/YPLL, `combine_estimates` τ²/meta-regression/Egger,
    `disparity_measures` WHO monitoring);
  - note the unreleased rounds (v0.78.0–v0.99.0) cleanly without claiming a release tag/DOI before owner approval.
- **`ROADMAP_BACKLOG.md` & `STATUS.md`:**
  - mark N47–N52 and N65–N79 as `(closed)` in Section 1 of `ROADMAP_BACKLOG.md` and fix N70's round column
    (`89` → `88`);
  - add N80 (Python-only Rounds 93–101 methods unreachable via MCP/CLI), N81 (routing contract stale at Round 64),
    N82 (README/backlog drift after Rounds 76–102) → Round 103;
  - refresh the `ROADMAP_BACKLOG.md` description line in `STATUS.md`.

## 4. Tests and acceptance

- **Unit tests (`tests/test_round103.py`):**
  - `demography_analysis` for all five `kind` values (offline synthetic WONDER/PUMS fixtures), verifying validated
    flags, `method_sources`, and WONDER suppression-bound handling;
  - `disparity_measures(kind="double_disaggregation" | "priority_quadrants")` and `spatial_model(kind="diversity")`;
  - CLI `python -m census tool demography_analysis ...` dispatch and `python -m census cite --tool demography_analysis`;
  - `scripts/sync_rule_text.py --check` passes; tool-count and core-profile tests updated (81 total, 16 core).
- **Routing tests (`tests/test_agent_routing.py`):** all 30 rows (R1–R30) pass offline.
- **Goldens:** both `scripts/refactor_golden.py` and `scripts/run_golden.py` byte-identical before and after.
- **Suite:** `OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q` passes with zero failures.
- **Audit & logs:** `docs/audits/round103_compatibility.md`, `STATUS.md`, `CHANGELOG.md` (0.99.0),
  `census/__init__.py`, `pyproject.toml`, `CITATION.cff`. No real-data example needed (no new statistics).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| `demography_analysis` tool + CLI + sources | done | wraps `census.demography` (R101) and `ypll` (R95); 81 tools |
| `disparity_measures` & `spatial_model` extensions | done | `double_disaggregation`, `priority_quadrants`, `diversity` |
| Routing contract R16–R30 | done | `docs/agent_routing.md` + `tests/test_agent_routing.py` (30 rows) |
| Rule text, recipes, README, backlog hygiene | done | `sync_rule_text.py --check` green; stale counts fixed |
| Goldens, tests, suite | pass | goldens byte-identical; 2416 passed, 42 skipped, 0 failures |
| Exceptions | none | see `docs/audits/round103_compatibility.md` |

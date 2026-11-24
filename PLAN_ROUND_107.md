# Plan — Round 107: Final-Wave Gated Exploratory Repairs + Full Agent/Workflow Integration

**Version target:** `v0.103.0`  
**Branch:** `phase103/agent-access-hygiene` (continuing uncommitted work per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run; failed candidates stay exploratory); goldens byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

Rounds 104–106 repaired and validated **9** previously exploratory measures (`P2` meta-analysis prediction interval, `R2` truncated Knapp–Hartung meta-regression, `E2` random-effects Egger test, `M1b-ATT` nearest-neighbour ATT, `B3` BYM2 disease mapping at `median E ≥ 30`, `R1b` continuous RDD, `M1b` probabilistic misclassification, `C2` observed Lin's CCC, and `M5` parametric g-formula for annual policy panels).

Two high-value gaps remain before this multi-round series is ready for review and commit:
1. **Four remaining near-miss exploratory measures** have clear, defensible finite-sample regimes or exact replicate bias-correction fixes that were diagnosed in Rounds 93 and 106:
   - **`Q2d` (Designation PPV predictive interval, Round 85 / N95):** In Round 106, `Q2c` (FH parametric bootstrap with rule re-selection) cleared all 4 `rule="prob80"` cells (`.891–.944`) and missed only `N=1000, A=0.02, rule="point"` (`.850`). Round 107 validates `Q2d` explicitly for `rule="prob80"` (and separately tests Li–Lahiri positive-`A` bootstrap for `rule="point"`).
   - **`E3b` (Croon/Fuller reliability-corrected ecologic slope, Round 87 / N96):** In Round 106, `E3` cleared all `n_j = 40` cells (`.883–.888`), failing only `n_j = 20` (`.810–.825`). Real PUMAs have `n_j ≥ 100`. Round 107 validates `E3b` across the realistic PUMA regime `n_j ∈ {40, 80, 150}`, `G ∈ {50, 150}` with an explicit `median_area_n ≥ 40, areas ≥ 50` gate.
   - **`H2d` (PUMS Hotelling `F` homogeneity test, Round 83 / N94):** In Round 106, `H2c` cleared 11/12 cells (`≤ .13`), missing only `rd K=5 n=300` at `.131`. Round 107 validates `H2d` across `n_per_stratum ∈ {500, 800}`, `K ∈ {3, 5}`, `measure ∈ {rr, or, rd}` with an explicit `min_stratum_n ≥ 500` gate.
   - **`S2` (Entropy diversity index, Round 93):** Round 93's `diversity_index` covered `.847` at `n = 50` respondents/tract and `.883` at `n = 200` because its `varp / (2 * P)` plug-in correction explodes at small `P` and ignores replicate bias-correction variance. Round 107 tests the exact SDR replicate bias correction `E_bc = E - 4 * (mean(Er) - E)` (the same estimator validated for segregation `H` in Rounds 50/52) across `n ∈ {50, 100, 200}`, `G_groups ∈ {4, 6}` (judged both overall and gated at `n ≥ 100`).
2. **Agent access, protocol, and routing parity for Rounds 104–107:**
   - `difference_in_differences(design="msm")` in `census/workflows_microdata.py` does not yet forward `method="gformula"` to `census.msm.marginal_structural_model`.
   - `docs/agent_protocol.md` (and synced `mcp_server.py` rules), `docs/agent_routing.md`, and `tests/test_agent_routing.py` do not yet advertise or test the newly validated Round 104–107 repairs.

---

## 2. Deliverables

1. **Frozen criterion & core:** `docs/audits/repairs107_criterion.md`, `census/repairs107_core.py`, `scripts/repairs107_validation.py`.
2. **Full validation audit:** `docs/audits/repairs107_validation.md` and `docs/audits/repairs107_validation.json`.
3. **Wire passing repairs only:**
   - `Q2d` (`prob80`) → `census/designation.py` (`ppv_interval` + `VALIDATED["q2_prob80"] = True`).
   - `E3b` (`median_area_n ≥ 40, areas ≥ 50`) → `census/ecologic.py` (`ecologic_corrected` + `VALIDATED_FROM["ecologic_corrected"]`).
   - `H2d` (`min_stratum_n ≥ 500`) → `census/stratified.py` (`homogeneity_hotelling` + gated `validated` flag on `stratified_pums`).
   - `S2` → `census/spatial_models.py` / `census/spatial_models_core.py` (if validated).
4. **MCP/CLI & routing/protocol parity:**
   - Wire `method="gformula"` into `difference_in_differences(design="msm")` in `census/workflows_microdata.py` and update `regression_discontinuity` docstring.
   - Update `docs/agent_protocol.md` with a concise **Repaired & Validated Methods (Rounds 104–107)** section and run `scripts/sync_rule_text.py`.
   - Expand `docs/agent_routing.md` and `tests/test_agent_routing.py` from 30 to **36 offline-tested rows (R1–R36)** (updating R20 to `method="gformula"` validated, and adding R31–R36 for Rounds 104–106 repairs).
5. **Tests, compatibility & docs:** `tests/test_round107.py`, `docs/audits/round107_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version bump `0.103.0` (`census/__init__.py`, `census/pipeline.py`, `CITATION.cff`), full-suite `pytest`, and manifest golden check.

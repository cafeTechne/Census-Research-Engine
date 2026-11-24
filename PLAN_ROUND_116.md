# Plan — Round 116: Recipes, README & Agent-Discoverability Refresh (`v0.112.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Bring `README.md` and `docs/recipes/` into 100% parity with Rounds 103–115 (81 MCP tools, 28 pre-registered manifest methods, 40 routing rows, and all 22 validated exploratory-measure repairs).

## Deliverables
1. Refresh `docs/recipes/preregistered.md`, `policy_change.md`, `causal.md`, `combine_estimates.md`, `small_area.md`, `reporting.md`, `confounding.md`, `health_inequality.md`, `spatial_patterns.md`, and `agreement.md` so every recipe points to the newly validated options (`method="gformula"`, `method="B3"`, `method="nn_att"`, `ppv_intervals=True`, `homogeneity_method="hotelling_f"`, `method="sdr_bc"`, `aapc_bootstrap_t`, `ecologic_fuller`, count-scale disparity indices, RDD continuous + density test, and the 28 manifest methods).
2. Refresh `README.md` (tool count 81, manifest method count 28, routing rows 40, reference benchmarks).
3. Add `tests/test_round116.py` verifying recipe/README consistency and zero stale count drift.
4. Update `docs/audits/round116_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.112.0`.

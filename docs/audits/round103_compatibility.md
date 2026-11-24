# Round 103 compatibility audit

- **Version:** 0.99.0 (`phase103/agent-access-hygiene`).
- **Scope:** Agent access, routing contract (R16–R30) and release hygiene after Rounds 76–102; no new statistical
  methods and no simulation.
- **Goldens:** `scripts/refactor_golden.py` and `scripts/run_golden.py` verified byte-identical before and after.
- **MCP surface:** 81 tools total (added full-profile `demography_analysis`; `core` unchanged at 16, `core_spatial`
  at 17). Existing signatures for `disparity_measures` and `spatial_model` remain backwards-compatible; new options
  are additive (`kind="double_disaggregation" | "priority_quadrants"` and `kind="diversity"`).
- **Rule text:** `scripts/sync_rule_text.py --check` passes.
- **Exceptions:** none.

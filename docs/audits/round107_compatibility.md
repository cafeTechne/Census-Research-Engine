# Round 107 Compatibility Audit (`v0.103.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Backward compatibility of library defaults:**
  - `census.designation.designation_accuracy(...)`: `ppv_intervals=False` by default (zero runtime overhead for existing callers; opt-in `ppv_intervals=True` adds `ppv_lower`, `ppv_upper`, `ppv_validated` with validated `'prob80'` and `'point'` rules).
  - `census.stratified.stratified_pums(...)`: `homogeneity_method="wald"` by default (preserving Round 83 test assertions); opt-in `homogeneity_method="hotelling_f"` provides Round 107's validated Hotelling `F` homogeneity test gated at `min_stratum_n >= 500`.
  - `census.workflows_microdata.difference_in_differences(design="msm")`: defaults to exploratory IPW (`method="ipw"`); opt-in `method="gformula"` routes to Round 106's validated parametric g-formula.
- **Agent routing & rule sync:** `docs/agent_routing.md` and `tests/test_agent_routing.py` expanded from 30 to **37 offline-tested rows (`R1–R37`)**; `docs/agent_protocol.md` synced to `mcp_server.py` via `scripts/sync_rule_text.py`.
- **No new MCP tools (81 total; 16 `core`, 17 `core_spatial`) and no new dependencies.**

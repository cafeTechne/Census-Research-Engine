# Round 147 Compatibility Audit (`v0.142.0`)

- **Scope:** Added `verify_bundle` and `list_manifest_methods` tools to Layer A MCP (`mcp_server.py`), added `publication` and `epidemiology` MCP profiles in `census/mcp_profiles.py`, and added `validate_handoff_seed` to Layer B MCP (`layer_b_openscholar/mcp_server.py`, 8 tools total).
- **Backward Compatibility:** All existing MCP profiles (`core`, `core_spatial`, `review`, `verification`, `full`) and `DESCRIPTION_BUDGET` remain 100% unchanged.
- **Review Note:** Author self-review, not independent.

# Round 154 Compatibility Audit (`v0.149.0`)

- **Scope:** Added `mcp_capabilities` introspection tool to Layer A MCP (`census/workflows_reporting.py`, `mcp_server.py`, `publication` profile), optional `query` keyword filtering to `census.recipes.get_recipe`, and `run_exploratory_pipeline` to Layer B MCP (`layer_b_openscholar/mcp_server.py`, 9 tools total).
- **Backward Compatibility:** `get_recipe()` and `get_recipe(name=...)` keep identical behavior and `RecipeName` enum schema; `tests/test_mcp_profiles.py` passes unchanged.
- **Review Note:** Author self-review, not independent.

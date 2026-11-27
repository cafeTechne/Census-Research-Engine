# Round 148 Compatibility Audit (`v0.143.0`)

- **Scope:** Modularized `mcp_server.py` (`1,719` → `< 1,150` lines) by extracting server instructions into `census/mcp_instructions.py` (updating `scripts/sync_rule_text.py` target) and pure calculation tools (`calculate_cv`, `calculate_significance`, `adjust_inflation`) into `census/mcp_helpers.py`.
- **Backward Compatibility:** Zero behavioral change; all module-level attributes on `mcp_server`, all FastMCP tool names/signatures, and `scripts/sync_rule_text.py --check` remain identical.
- **Review Note:** Author self-review, not independent.

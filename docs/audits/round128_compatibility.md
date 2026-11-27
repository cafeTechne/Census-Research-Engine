# Round 128 Compatibility Audit (`v0.123.0`)

- **Additions:** `layer_b_openscholar/mcp_server.py` (standalone FastMCP server with 4 tools), `seed-domain` CLI subcommand in `layer_b_openscholar/__main__.py`, `layer_b_openscholar/tests/test_layer_b_mcp.py`.
- **Isolation:** Zero imports from or into `census/`; `pyproject.toml` and `requirements.txt` unchanged.

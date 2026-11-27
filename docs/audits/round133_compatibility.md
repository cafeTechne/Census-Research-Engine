# Round 133 Compatibility Audit (`v0.128.0`)

- **Additions:** `layer_b_openscholar/pdf_indexer.py` (page/section-level FTS5 passage citation store targeting `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/passages.sqlite` by default), `search_passages` MCP tool in `layer_b_openscholar/mcp_server.py`, and `layer_b_openscholar/tests/test_layer_b_passages.py`.
- **Isolation:** Zero imports from or into `census/`; `pyproject.toml` and `requirements.txt` unchanged.

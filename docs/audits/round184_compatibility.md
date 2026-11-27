# Round 184 Compatibility Audit (`v0.179.0`)

- **Scope:** Added `dedupe_title_duplicates` to `layer_b_openscholar/maintenance.py`, wired `dedupe-corpus` CLI and `dedupe_corpus` MCP tool (19 Layer B MCP tools total).
- **Layer B Isolation:** Zero `census` imports; all outputs tagged `exploratory_hypothesis_seed`.
- **Review Note:** Author self-review, not independent.

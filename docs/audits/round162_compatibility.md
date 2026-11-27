# Round 162 Compatibility Audit (`v0.157.0`)

- **Scope:** Upgraded `layer_b_openscholar/rag.py` with JATS/HTML tag stripping (`strip_jats_html`), `min_year`/`domain_filter`/`export_bib_path` options, and `build_evidence_brief` (wired into CLI and `evidence_brief` MCP tool).
- **Layer B Isolation:** Zero `census` imports; all outputs tagged `exploratory_hypothesis_seed`.
- **Review Note:** Author self-review, not independent.

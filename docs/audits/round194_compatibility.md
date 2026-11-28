# Round 194 Compatibility Audit — Layer B Cross-Corpus Claim Grounder (`v0.190.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Added `layer_b_openscholar/claim_grounder.py` (`ground_claims`, `write_grounding_markdown`) using 3-way Hybrid RAG to audit draft manuscript claims against `index.sqlite` + `passages.sqlite` + `vectors.sqlite`.
  - Wired `ground-claims` CLI subcommand and `ground_claims` MCP tool (**22** isolated Layer B MCP tools total).
- **Isolation:** Strictly zero `census` imports in `layer_b_openscholar/`.

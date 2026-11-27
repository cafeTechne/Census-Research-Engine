# Recipe: Domain-Specific Hybrid RAG & Continuous Corpus Mining (Layer B)

Use this workflow to query the continuously mined Samsung 850 EVO SSD literature corpus (`index.sqlite`, 36 curated epidemiology/demography domains) fused with local study reports and PDFs (`passages.sqlite`) via citation-grounded Hybrid RAG.

## Strict Isolation Boundary
- All commands below live in `layer_b_openscholar/` (zero `census` imports). Every output carries `status: "exploratory_hypothesis_seed"` and requires human review before entering a Layer A pre-registered manifest.

## Steps

1. **Check corpus coverage & background miner health:**
   - CLI: `python -m layer_b_openscholar corpus-health`
   - MCP: `corpus_health()` or `miner_status()`
2. **Run citation-grounded Hybrid RAG v2 (`FTS5 + BM25 RRF + local passages`):**
   - CLI: `python -m layer_b_openscholar rag-query "<question>" --min-year 2020 --bib-out refs.bib --out brief.md`
   - MCP: `rag_query(query="<question>")` or `evidence_brief(query="<question>", min_year=2020)`
3. **Expand 1-hop citations around high-value seed papers:**
   - CLI: `python -m layer_b_openscholar expand-citations W4408165420 --limit 25`
   - MCP: `expand_citations(work_id="W4408165420")`
4. **Keep the 36-domain miner running across reboots (optional):**
   - Generate a `systemd --user` service unit: `python -m layer_b_openscholar systemd-unit --out ~/.config/systemd/user/layer-b-corpus-miner.service`
   - Enable: `systemctl --user daemon-reload && systemctl --user enable --now layer-b-corpus-miner.service`
5. **Transition to Layer A pre-registration:**
   - Follow `get_recipe("literature_to_preregistration")` to review the seed scaffold and register a frozen Layer A manifest.

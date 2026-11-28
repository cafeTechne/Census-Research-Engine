# Round 201 Compatibility Audit — 3-Tier Open-Access Full-Text Fallback Harvester (`N131`, `v0.197.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Upgraded `layer_b_openscholar/fulltext_harvester.py` with `fetch_oa_fulltext_with_fallback()` (`epmc_xml` -> `pmc_oai_pmh` -> `arxiv_html`) and `sources_used` tracking.
- **Isolation:** Strictly zero `census` imports in `layer_b_openscholar/`.

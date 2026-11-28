# Plan — Round 201 (N131): Multi-Source Open-Access Full-Text Fallback Harvester (`v0.197.0`)

## 1. Strategic Objective
Upgrade `layer_b_openscholar/fulltext_harvester.py` from a single Europe PMC `fullTextXML` endpoint (which returns HTTP 500 on many PMC IDs) to a resilient 3-tier open-access fallback chain:
1. Europe PMC `fullTextXML`
2. NCBI PMC OAI-PMH `GetRecord` (`metadataPrefix=pmc` JATS XML)
3. arXiv HTML (`https://arxiv.org/html/{arxiv_id}`) when an arXiv ID is present
Strictly isolated from `census/` (zero census imports, zero new dependencies).

## 2. Exact File Contracts
1. `layer_b_openscholar/fulltext_harvester.py`: Add `PMC_OAI_PMH_URL`, `ARXIV_HTML_URL`, `parse_html_sections()`, fallback fetch chain, and `sources_used` summary counter.
2. `tests/test_round201.py` & `docs/audits/round201_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented from roadmap item `N131`.

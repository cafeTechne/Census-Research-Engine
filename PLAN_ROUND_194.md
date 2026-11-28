# Plan — Round 194: Layer B Cross-Corpus Claim Grounding & Citation Audit (`v0.190.0`)

## 1. Strategic Objective
Add an isolated Layer B claim-grounding auditor (`layer_b_openscholar/claim_grounder.py`) that takes a list of draft research claims, runs 3-way Hybrid RAG (FTS5 + BM25 + Neural/Hash Vector + local passages) for each claim, and emits a structured grounding coverage report with `[L#]`/`[P#]` citations, DOIs, and BibTeX — strictly tagged `exploratory_hypothesis_seed` and zero `census/` imports.

## 2. Exact File Contracts
1. `layer_b_openscholar/claim_grounder.py`: `ground_claims(claims, ...)` and `write_grounding_report(...)`.
2. `layer_b_openscholar/mcp_server.py`: Register `ground_claims` MCP tool (**22** Layer B MCP tools total).
3. `layer_b_openscholar/__main__.py`: Add `ground-claims` CLI subcommand.
4. `tests/test_round194.py` & `docs/audits/round194_compatibility.md`.

## 3. Acceptance Gates
1. `pytest -q tests/test_round194.py layer_b_openscholar/tests/` passes with 0 failures.
2. Strict zero-`census`-import isolation holds.

## 4. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Implemented `layer_b_openscholar/claim_grounder.py` (`ground_claims`, `write_grounding_markdown`), wired `ground-claims` CLI and `ground_claims` MCP tool (22 Layer B tools total). Verified via `tests/test_round194.py`.

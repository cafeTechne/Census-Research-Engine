# Round 88 plan: method attribution (citing the sources behind every method)

**Goal.** Backlog N70 (owner request, 2026-11-23). Any engine result must be traceable to the published sources it
rests on, so that a study using it can cite them. Three kinds of source count:
- the papers that define each method (for example Greenland and Robins 1985 for Mantel–Haenszel variances);
- the textbooks whose guidance shaped how the engine applies it (Bovbjerg's *Foundations of Epidemiology*;
  Hernán and Robins's *Causal Inference: What If*; Walker's *Analyzing US Census Data*);
- the engine's own validation audit for the method.

Manifest methods text already lists references, but tool results, results bundles and the CLI do not. Version
0.84.0. Branch `phase88/attribution`. No new statistics; must land before Rounds 89–93 so they register their
sources as they are built.

## 1. Registry (`census/references.py`)

- **One entry per source:** authors, year, title, container or publisher, DOI or URL, and kind (paper, book,
  software, data, documentation). Formatted text (the existing manifest style) and BibTeX can be generated from it.
- **The registry includes:**
  - the existing manifest citations (unchanged text, so registered methods text is byte-identical);
  - the method papers of Rounds 24–87;
  - the three textbooks (Bovbjerg 2020; Hernán and Robins 2020, *What If*, with the edition used noted; Walker 2023).
- **`TOOL_SOURCES`:** for every MCP tool, its method papers, guidance texts, data sources and validation audits.
  Roles are `method`, `guidance`, `data`, `software` and `validation`.
- **Coverage test:** every registered tool has an entry, and every cited id exists. Future tools therefore cannot
  ship without attribution.

## 2. Where attribution appears

- **Every successful MCP and CLI tool result** gains `method_sources`: a list of {id, role, citation}, added at the
  shared tool boundary, so no tool can forget it.
- **`make_results_bundle`** collects the sources of all included results and writes `references.md` and
  `references.bib`. `methods.md` gains a "Sources" section that separates method papers, guidance texts and data.
- **CLI:** `python -m census cite --tool <name> [--format text|bibtex]`.
- **Library:** `census.references.cite(...)`.
- **Docs:**
  - `docs/citing.md` explains how to cite the engine (Zenodo DOI), its methods and the guidance texts;
  - CITATION.cff lists the three textbooks under `references`;
  - the README gets a short "Citing methods" section.
- **Manifest runs keep their methods text.** A new `references.bib` goes into manifest bundles only if goldens show
  no change; otherwise it is left for a documented later change.

## 3. Acceptance

- Coverage and formatting tests; goldens byte-identical (the registry reproduces existing citation text exactly);
  suite.
- STATUS, CHANGELOG, compatibility audit.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Registry | done | `census/references.py`; manifest text reused unchanged; module lists verbatim |
| Tool sources and coverage test | done | 78 tools; `tests/test_round88.py` |
| Results, bundles, CLI | done | 49 method tools; Sources section, `references.md`, `references.bib`; `cite` |
| Docs, CITATION.cff | done | `docs/citing.md`, README, CHANGELOG, STATUS, protocol rule |
| Goldens, suite | see audit | `round88_compatibility.md` |
| Exceptions | 4 | no manifest `.bib`; discovery tools omitted; one unverified entry; audits by path |

# Citing the engine, its methods and the texts behind them

Round 88 (backlog N70). A study that uses this engine should cite four kinds of source.

1. **The engine.** Use [CITATION.cff](../CITATION.cff), or the concept DOI
   [10.5281/zenodo.23925301](https://doi.org/10.5281/zenodo.23925301) plus the version DOI of the release you used.
2. **The data.** Cite the Census Bureau and name the ACS 5-year release(s) and table(s). Bundles write this as
   `citation` in `bundle.json` and under **Data** in `methods.md`. External sources (CDC WONDER exports, PLACES,
   County Health Rankings) are cited by the tools that read them.
3. **The methods.** These are the papers that define each estimator or test, for example Greenland and Robins (1985)
   for Mantel–Haenszel variances or Sun and Abraham (2021) for staggered adoption.
4. **The guidance texts.** These textbooks shaped how the engine applies its methods. Each one has a chapter mapping
   in `docs/literature/`:
   - Bovbjerg, *Foundations of Epidemiology* (2020): epidemiologic reporting, stratification, bias analysis;
   - Hernán and Robins, *Causal Inference: What If* (2020): causal questions, positivity, g-methods;
   - Walker, *Analyzing US Census Data* (2023): census data sources and spatial models.

## Where the sources appear

| Place | What it holds |
| :--- | :--- |
| A tool result's `method_sources` | A list of `{id, role, citation}` entries for the methods and guidance texts the tool rests on, plus its data sources, software and the engine's validation audit (`{role: "validation", audit: path}`). Method tools carry it on success, through MCP and through `python -m census tool`. Pure discovery and extraction tools omit it to keep their frequent results small; their data citation is in provenance. |
| `make_results_bundle` | `methods.md` ends with a **Sources** section grouped by role. `references.md` and `references.bib` (BibTeX) collect every result's sources. |
| `python -m census cite --tool NAME [--format bibtex]` | The references for one tool. `cite ID ...` formats given source ids; `cite --list` lists the tools. |
| `census.references` | The registry (`SOURCES`, `TOOL_SOURCES`) and the functions `cite`, `tool_reference`, `collect` and `render_sources`. |
| Manifest runs | The methods text keeps its own reference list, which is unchanged. |

## Roles

| Role | Meaning |
| :--- | :--- |
| `method` | A paper or book that defines the computation |
| `guidance` | A textbook whose advice shaped how the engine applies the method (defaults, refusals, wording) |
| `data` | A data product the tool reads |
| `software` | A library whose algorithm the tool calls |
| `validation` | The engine's own audit (`docs/audits/...`) that validated the method, or showed it failed |

A validation audit is evidence about the engine. It is not a publication: cite it by the release DOI and path.

## Accuracy of entries

- Entries are written from the publications. Any entry recorded without checking the publication is marked
  `verified: False`, and its citation ends "[details to verify]". Check those before you publish.
- Every new tool must register its sources: `tests/test_round88.py` fails when a tool lacks an entry or cites an
  unknown id.

# Round 72 plan: data sources the replications needed

**Goal.** Backlog N50. Add the non-ACS covariate sources that Rounds 66–69 fetched by hand, and a one-request-per-state
tract path. Version 0.68.0. Branch `phase72/context-sources`. No new statistics; goldens byte-identical (every
addition is opt-in).

## 1. Context covariate sources (`census/context_sources.py`)

A registry like `census/health_sources.py`. Each source records its publisher, licence, URL and years, and pins
the SHA-256 of every downloaded file in a cache sidecar. These are **covariates**, never health outcomes, so the
circularity rule does not apply, but each source states what it is derived from.

| Source | Content | Access | Years |
| :--- | :--- | :--- | :--- |
| `cbp` | County Business Patterns establishment counts by NAICS (county) | Census API `cbp` dataset (the user's key) | 2012–2022 |
| `ers_typology` | ERS county economic types (farming, mining, manufacturing, government, recreation, nonspecialized) and policy types | ERS GIS REST service (`County_Classifications`), CC0 | 2015 edition |
| `ers_rucc` | Rural–urban continuum and urban influence codes, metro status | same service | 2013 (2023 if the service has it) |
| `chr_additional` | County Health Rankings additional measures, e.g. v141 residential segregation | CHR national workbook (xlsx, "Additional Measure Data") or CHR's calculation repository at a pinned commit | 2025 |

**Functions:**
- `fetch_context(source, year, **kw)` returns a GEOID-indexed frame with provenance.
- `list_context_sources()` lists them.
- **MCP:** `list_health_sources` gains a `kind="context"` view, so no new tool. `build_analysis_frame(context=[{"source":
  "cbp", "naics": ["813110"], "per": 10000, "name": "religious"}, …])` joins them.
- **Manifests:** a `context` block with the same entries; validated by `create_manifest` (known source, year,
  pinned hash recorded in the run).
- CHR additional measures that are ACS-derived (like v141) are refused as **outcomes** under the existing CHR rule.
  They are allowed as covariates and as replication comparisons.

## 2. One request per state for tracts

- `build_entities("tract", state, codes=None, state_wide=True)` makes one `tract:*` request per state, where the
  default is one per county.
- `plan_extraction` and `batch_download` accept `state_wide`.
- The default stays per-county, so request patterns and goldens are unchanged.
- Block groups stay per county (the API requires it).

## 3. Checks (numeric, fixed in advance; offline fixtures where possible)

1. **CBP:**
   - reproduces the Round 69 county counts for NAICS 813110 exactly (cached responses);
   - the national total equals the sum over counties.
2. **ERS:**
   - Round 69's extract hashes to the pinned value;
   - type counts by category match the ERS documentation's published counts (recorded in the test with their
     source).
3. **CHR additional:** v141 from the new source equals Round 66's comparison values exactly.
4. **State-wide tracts:** one state's tract frame is identical to the per-county frame (cached MI and NY
   responses).
5. Live checks (`CENSUS_LIVE_TESTS=1`) refetch one item per source.

## 4. Docs and acceptance

- New recipe `docs/recipes/context_covariates.md`; README sources section; protocol text; STATUS, CHANGELOG,
  version, compatibility audit.
- Goldens byte-identical; full suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Registry and fetchers | done | `census/context_sources.py` (cbp, ers_typology, ers_rucc, chr_additional) |
| Frame and manifest joins | done | `build_analysis_frame(context=…)`, manifest `context` block, `list_health_sources(kind="context")` |
| State-wide tracts | no change | already one request per state |
| Checks | done | live: CHR hash = Round 66's, CBP 01001 = 51, ERS complete; OMB metro cross-check not run (no .xls reader) |
| Goldens, final suite | done | identical; 2179 passed, 1 rule failure fixed |
| Exceptions | two | state-wide tracts already existed; OMB cross-check not run |

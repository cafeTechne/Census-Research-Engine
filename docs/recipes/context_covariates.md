# Context covariates (County Business Patterns, ERS county types, CHR additional measures)

Goal: add county characteristics the ACS does not measure, such as establishment counts, rural–urban status, economic
dependence or a published CHR additional measure, to an ACS analysis frame or a manifest (Round 72).

1. List the sources: `list_health_sources(kind="context")`.

   | Source | Content | Years |
   | :--- | :--- | :--- |
   | `cbp` | County Business Patterns establishments by NAICS | 2012–2022 |
   | `ers_typology` | ERS 2015 economic types and policy types | 2015 |
   | `ers_rucc` | ERS rural–urban continuum and urban influence codes; 2013 metro status | 2013 |
   | `chr_additional` | County Health Rankings additional measures from CHR's calculation repository, pinned commit | 2025 |

2. Name each entry and add it to `build_analysis_frame(context=[...])`, or to a manifest's `"context": [...]` block
   (same format). Examples:
   - religious establishments per 10,000:
     `{"source": "cbp", "name": "religious", "year": 2012, "naics": ["813110"], "per": 10000,
     "per_column": "B01003_001E"}`. Several NAICS codes are summed;
   - `{"source": "ers_typology", "name": "econ_type", "field": "Type_2015_Update"}`, coded 0 nonspecialized,
     1 farming, 2 mining, 3 manufacturing, 4 federal/state government, 5 recreation;
   - `{"source": "ers_rucc", "name": "metro", "field": "Metro2013"}`;
   - `{"source": "chr_additional", "name": "segregation_bw", "measure": "v141", "release": 2025}`.
3. These are county values. A tract frame gets its county's value; the join reports the level and the share
   missing. Turn categories into indicators in the formula (e.g. `C(econ_type)`) or with a derivation.
4. Context variables are **covariates only**. An external health outcome still goes in `external` and follows the
   circularity rule. An ACS-derived CHR measure (v141 uses ACS B11002) cannot be an outcome, but can be a
   covariate or a replication comparison.
5. Provenance (URL, SHA-256, download time; the CBP query parameters) is in the result's `context` and in a
   manifest run's `run.json`. `CENSUS_HEALTH_OFFLINE=1` uses cached files only.

Notes:
- ERS's 2015 typology has "recreation" where the 2004 edition had "services". Results are not interchangeable with
  studies that used the older edition (Round 69).
- Tract requests are already one per state when no counties are named (`build_entities("tract", state)`).

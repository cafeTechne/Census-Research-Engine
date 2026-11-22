# Cross-release comparisons: variable concordance and crosswalk decisions

Goal: compare a table across ACS releases only where its variables mean the same thing.

1. Call `check_variable_concordance(table_code, start_year, end_year)`.
   - It works offline, from the metadata archive.
   - It lists variables whose codes, labels or concepts change across releases, with the evidence.
   - `plan_extraction` adds the continuity check before a download.
2. When a change blocks a comparison:
   - **Split** (the default when unsure): treat the codes as different variables.
   - **Merge**: only with a census.gov source saying the measure is unchanged.
   - **Exclude**: drop the affected cells.
3. Record the decision in two steps:
   - `draft_crosswalk_override(table_code, entries=["2017:B27001_005", ...], decision, drafted_by, rationale,
     source_url)` saves the evidence and a draft row;
   - a **different** reviewer re-checks the evidence and the source, then calls `record_crosswalk_review(row,
     reviewed_by, table_code)`;
   - `validate_crosswalks()` checks every committed override.
4. Tract boundaries changed in 2020; see recipe `custom_geographies` (`apportion_tracts`).
5. Compare only non-overlapping releases for tests of change (recipes `tract_trend`, `policy_change`).

# Round 82 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round82`, branch `phase82/epi-reporting`. No new
statistics, so no simulation criterion (numeric checks in `docs/audits/r82_reporting_checks.md`). Version 0.78.0.

## Behaviour changes

- **Manifest methods text** gains "Study design and measures" (design labels; each outcome's measure type) after
  Data, and a generated "Limitations" section before References. **Run info** gains `design` and
  `measure_types`. Registered manifests are unchanged and keep their hashes (the labels are output, not input).
- **Goldens (intended changes, checked field by field):**
  - schema golden: only the `methods` strings differ (525 entries: the two new sections);
  - run golden: only `methods.md`, `results/run.json` (exactly the two new keys `design` and `measure_types` in all
    27 changed cases; no existing key changed) and the file SHA-256 values that hash them. Every other value is
    identical (NaN compared as equal).
- `make_table` gains `kind="table1"` (with `exposure`, `population`) and `confidence_level` for comparison tables.
- `reliability_profile` gains `allocation_tables` and `year` (B99 allocation shares).
- `make_results_bundle` gains `design` (default `"area"`): methods.md now ends with the ecologic and
  cross-sectional limitations, and `bundle.json` provenance records the design.
- Core MCP rule 2 adds the association-language sentence; protocol rule text and the `reporting` recipe updated.
  No new tool (75).

## Exceptions

1. **External variables without `measure_type` are reported as "unspecified", not refused.** The plan proposed
   refusing them in confirmatory manifests, but registered manifests are byte-fixed and must keep validating; the
   limitations section names undeclared outcomes instead. WONDER, PLACES, USALEEP and the registered CHR measures are
   typed by source.
2. **Allocation shares are a tool option, not a manifest stage.** Adding API calls to manifest runs would change
   offline runs and every golden; `reliability_profile(allocation_tables=...)` and `census.epi_reporting` provide
   them, and the limitations builder accepts them.
3. **Causal-language rule is advisory text** (protocol, recipes, MCP) plus a `causal_terms` checker used in tests on
   generated text; the engine does not rewrite user prose.
4. The 5% allocation level flags every common health table in MI/NY counties (health insurance 20.5% median,
   disability 12.1%, family poverty income 37.4%); it is a reported limitation, not a refusal.

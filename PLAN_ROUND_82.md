# Round 82 plan: epidemiologic reporting conventions

**Goal.** Backlog N59. Make every result read the way *Foundations of Epidemiology* (Bovbjerg 2020; mapping in
`docs/literature/foundations_of_epidemiology.md`) says an epidemiologic result must read. This round makes four
kinds of change:
- it says what kind of measure each outcome is (chapter 2);
- it says what an area-level, cross-sectional design can and cannot show (chapters 1 and 9);
- it reports item nonresponse (chapter 6);
- it adds a study's standard "Table 1" and a limitations section (Appendix 1).

No new inferential statistics. Version 0.78.0. Branch `phase82/epi-reporting`.

## 1. Measure types and units (chapter 2)

- **`measure_type` for every outcome**, one of `count`, `prevalence`, `incidence_rate` or `incidence_proportion`:
  - ACS proportions, PLACES and CHR prevalence measures are `prevalence`;
  - WONDER deaths over person-years, and `expected_count` with person-years, are `incidence_rate`;
  - an external variable declares its type, and an undeclared one is refused in confirmatory manifests.
- **Reported with the type:**
  - the unit ("per 100,000 person-years", "percent of the civilian noninstitutionalized population");
  - the period. ACS five-year measures describe the 60-month window and are not annual figures.
- **Rate comparisons need the same unit and period.** The engine converts where it can and refuses where it can't,
  for example a five-year pooled count against an annual rate without `period_years`.

## 2. Design labels and language (chapters 1, 4, 5, 9, 10)

- **Every area-level analysis carries `design: ecologic, cross-sectional`** with two fixed notes:
  - results describe areas, not individuals (ecologic fallacy);
  - exposure and outcome are measured over the same window, so temporal order is not established.
- **Methods text and MCP rule text use association language.** A protocol rule forbids "causes", "effect of" and
  "leads to" for these designs, except in `estimate_effect` and the DiD tools, which state their assumptions.
- **Interpretation templates** (chapter 4) for ratios ("… times as high in … compared with … over …") and for
  differences, plus "no evidence of a difference" rather than "no difference" (chapter 5). The make_table and
  results-bundle text use them.
- **`confidence_level=.95` reporting option** for health audiences in `make_table` and bundles. Tests stay at the
  manifest's level, and the 90% Census convention stays the default.

## 3. Item nonresponse: ACS allocation rates (chapter 6)

- **Map each analysis variable to its B99 allocation table.**
  - Use the 100 B99 tables in the offline metadata, for example B992701 for health insurance, B99181 for
    disability and B99192 for household income.
  - Report the share of the universe whose answer was allocated (imputed) per area and overall.
- **A median allocation share above 5%** in the analysed areas adds a limitation note. This is the book's
  missing-data warning; it is not a refusal.
- **Check:** the computed shares reproduce published B99 line ratios exactly for MI/NY counties.

## 4. Table 1 and limitations (Appendix 1)

- **`make_table(kind="table1")` and a bundle `table1.csv`:**
  - the study areas described by the exposure's tertiles;
  - for each tertile, the number of areas, population, and the mean and median of outcome and covariates;
  - MOEs from replicates where available.
- **A generated limitations section in the bundle**, assembled from what the run knows:
  - design labels;
  - measure type;
  - allocation shares;
  - WONDER suppression;
  - incomplete replicates;
  - spatial dependence warnings;
  - circularity justifications;
  - failed or exploratory methods used.

## 5. Acceptance

- Numeric checks (Table 1 against direct estimates; allocation shares against published lines).
- Text rules mirrored in `docs/agent_protocol.md`, recipes and MCP text (sync script).
- Tests; goldens.
  - The run golden is expected to change in the methods text and the new bundle files only. This is intended and
    documented, with a field-by-field diff.
  - Registered manifests keep their hashes, because the labels are output, not input.
- Suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Measure types, units | | |
| Design labels, language, templates | | |
| Allocation rates | | |
| Table 1, limitations | | |
| Goldens, suite | | |
| Exceptions | | |

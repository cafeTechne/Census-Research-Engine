# CDC, *Principles of Epidemiology in Public Health Practice*: guidance mapped to engine work

Source: Centers for Disease Control and Prevention. *Principles of Epidemiology in Public Health Practice: An
Introduction to Applied Epidemiology and Biostatistics*, 3rd ed. (Self-Study Course SS1000). U.S. Department of
Health and Human Services, 2006, updated 2012 (`literature_pdfs/cdc_6914_DS1.pdf`, public domain). Mapping by the
maintainer agent, used to draft Round 95 (backlog N72). Author self-review, not independent.

| Lesson | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 1 | Descriptive epidemiology (person, place, time), analytic epidemiology | Covered by reporting conventions (Round 82) | — |
| 2 | Summarizing data: frequency distributions, measures of central location and spread (including geometric mean) | Covered | — |
| 3 | Measures of risk: rates, ratios, proportions; mortality measures including **years of potential life lost** (YPLL to 65, 75 or life expectancy, age-adjusted YPLL rates); measures of association and public health impact | Rates, SMR, attributable fractions: covered; YPLL only as a County Health Rankings measure | 95: YPLL from WONDER age-group exports, crude and age-adjusted rates with intervals; suppression-aware |
| 4 | Displaying data: tables, graphs, deviation charts against **historical limits** | Figures and tables: covered | 95: historical-limits comparison chart for annual series |
| 5 | Surveillance: analysis by time, place and person; **aberration detection** (historical limits, EARS) | Interrupted series and joinpoint describe known or unknown breaks; no aberration flag for the latest period | 95: historical-limits and EARS-style aberration flags for annual county/state rates, validated for false-alarm rate |
| 6 | Outbreak investigation steps | Not applicable to annual area data | — |

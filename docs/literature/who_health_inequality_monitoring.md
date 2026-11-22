# WHO, *Handbook on Health Inequality Monitoring*: guidance mapped to engine work

Source: World Health Organization. *Handbook on Health Inequality Monitoring: With a Special Focus on Low- and
Middle-Income Countries*. Geneva: WHO, 2013 (`literature_pdfs/handbook-on-health-inequality-monitoring.pdf`).
Mapping by the maintainer agent, used to draft Round 94 (backlog N71). Author self-review, not independent.

| Chapter | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 1–2 | The monitoring cycle; equity stratifiers (economic status, education, place, sex, race/ethnicity); data-source mapping | Stratified extraction, health sources registry: covered | — |
| 3.2–3.3 | Simple measures (difference, ratio) and their limits (they ignore middle groups and group sizes) | Covered (`disparity_measures`) | — |
| 3.4–3.6 | Complex measures: SII and concentration index (ordered groups); between-group variance, Theil, MLD, index of disparity, **mean difference from the overall mean or from the best subgroup, weighted or unweighted** (non-ordered groups) | SII, RII, CI (Round 24), BGV, Theil, MLD, IDisp (Round 76); no mean-difference measures | 94: weighted and unweighted mean difference from the overall mean and from the best subgroup, with intervals |
| 3.7 | Population attributable risk (absolute and %) relative to the best-performing subgroup | Attributable fractions for exposures (Round 84); not relative to a best subgroup | 94: PAR and PAR% against the best subgroup (or a chosen reference) |
| 4.1–4.6 | Report both absolute and relative inequality; benchmarking; **time trends in inequality** (change in measures between surveys, with uncertainty) | Single-period measures only | 94: change in an inequality measure between non-overlapping releases, with intervals |
| 4.7, 5.5 | Priority areas from both the level of a health indicator and the size of its inequality (four-quadrant view) | No | 94: level-by-inequality quadrant report |
| 5 | Step-by-step assessment; double disaggregation (two stratifiers at once) | One stratifier at a time | 94: double disaggregation (e.g. race by poverty, or place by income) |

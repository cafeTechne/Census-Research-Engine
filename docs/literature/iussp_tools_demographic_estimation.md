# Moultrie et al., *Tools for Demographic Estimation*: guidance mapped to engine work

Source: Moultrie TA, Dorrington RE, Hill AG, Hill K, Timæus IM, Zaba B (eds). *Tools for Demographic Estimation*.
Paris: International Union for the Scientific Study of Population, 2013 (second impression; CC BY-NC-SA 3.0;
`literature_pdfs/TDE_2013_2ndImpression_opt_0.pdf`). Mapping by the maintainer agent, used to draft Round 101
(backlog N78). Author self-review, not independent.

| Part | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| Evaluation of data (ch. 1) | Age and sex data assessment: Whipple's and Myers' indices of age heaping, sex ratios by age, the UN age-sex accuracy index | No age-data quality measures | 101: age-heaping and age-sex accuracy indices for PUMS single-year ages and decennial counts, with replicate intervals |
| Fertility (ch. 2–14) | P/F ratios, relational Gompertz, reverse survival, own-children methods | ACS fertility tables are direct (B13016), so these indirect methods serve data-poor settings | Not planned |
| Child and adult mortality (ch. 15–27) | Indirect methods (Brass, orphanhood, siblings), growth balance and Synthetic Extinct Generations for death-registration completeness | US registration is complete, so completeness methods add little | Not planned |
| Model life tables (ch. 31–33) | Life-table construction, model life tables, combining estimates | No life-table function (USALEEP and CHR life expectancy are external) | 101: abridged life tables from age-band deaths and populations (Chiang II SEs); Arriaga decomposition of life-expectancy change by age and cause |
| Migration (ch. 34–37) | Estimation from census data (census survival ratios, residual method), model migration schedules, log-linear flows | ACS flows (Round 92) | 101: net migration by age from two decennial censuses by the census survival method (descriptive) |

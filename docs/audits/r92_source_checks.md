# Round 92 source checks: Population Estimates, LODES and ACS migration flows

Author self-review, not independent. Run on 2026-11-23 against the live files, which are now cached with SHA-256
sidecars.

| Check | Result |
| :--- | :--- |
| PEP vintage 2024 (`co-est2024-alldata.csv`): each state total equals the sum of its counties, every year 2020–2024 | pass (255 state-years) |
| PEP vintage 2019 (`co-est2019-alldata.csv`): the same, 2010–2019 | pass |
| PEP age/sex (`cc-est{2019,2024}-agesex-26.csv`): county `POPESTIMATE` equals the totals file for every county-year | pass (MI; confirms the `YEAR` code mapping: 2019 file codes 3–12 = 2010–2019; 2024 file codes 2–6 = 2020–2024) |
| PEP values | MI July 1, 2023 = 10,083,356; NY = 19,737,367 (vintage 2024, as published in the file) |
| LODES8 MI 2021 WAC (all jobs, JT00): tract aggregates sum to county aggregates | pass (4,042,589 jobs) |
| LODES8 MI 2021 RAC total | 4,103,011 jobs by residence |
| ACS flows 2016–2020, MI counties: MOVEDIN − MOVEDOUT = MOVEDNET in every county pair (within 1) | pass (12,607 rows; every row has MOEs) |
| ACS flows 2017–2021 and later | partners are states, not counties, so these releases are refused for county-to-county use |

## Limits

- PEP and LODES carry no MOE. LODES perturbs small-area values for confidentiality.
- ACS flows give no out-flow to places abroad, so totals cover domestic out-migration only.

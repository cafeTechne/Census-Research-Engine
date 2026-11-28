# Round 197 (N128): Age-Structure (% 65+) & Urban-Rural Confounding in the 11-Cause County Mortality Atlas

- **Causes analyzed:** `11` CDC WONDER 2018–2022 county mortality causes across MI+OH and NY+PA.
- **Key Finding (NY+PA confounding resolution):** Before adjustment, **`6/11`** causes had crude poverty RR `< 1.0` per +10 pp poverty in NY+PA; after adjusting for county `% age 65+` (from cached 2024 ACS `B17001` VRE) and `log(population density)`, **`10/11`** causes are positive (`RR > 1.0`), with **`5` causes flipping sign from `< 1.0` to `> 1.0`**: `['heart_disease', 'suicide', 'clrd', 'liver_disease', 'kidney_disease']`.
- **Governance:** 100% offline reproducible; zero automated WONDER access; zero raw sub-national counts 1–9 emitted.

| Cause | NY+PA Crude RR (+10pp pov) | NY+PA Age+Urban Adj RR (90% CI) | Flipped >1? | MI+OH Crude RR | MI+OH Age+Urban Adj RR |
| --- | ---: | --- | :---: | ---: | ---: |
| heart_disease | 0.959 | 1.067 (0.996–1.144) | Yes | 1.256 | 1.274 |
| drug_overdose | 1.330 | 1.458 (1.223–1.739) | — | 1.996 | 1.853 |
| stroke | 0.810 | 0.944 (0.811–1.099) | — | 1.080 | 1.085 |
| suicide | 0.816 | 1.059 (0.918–1.222) | Yes | 1.045 | 1.095 |
| diabetes | 1.077 | 1.398 (1.321–1.479) | — | 1.344 | 1.433 |
| clrd | 0.835 | 1.152 (1.067–1.243) | Yes | 1.197 | 1.312 |
| liver_disease | 0.905 | 1.210 (1.118–1.310) | Yes | 1.236 | 1.282 |
| kidney_disease | 0.811 | 1.039 (0.875–1.235) | Yes | 1.457 | 1.460 |
| firearm | 1.367 | 1.754 (1.166–2.640) | — | 2.000 | 1.868 |
| alcohol_induced | 1.113 | 1.315 (1.243–1.391) | — | 1.116 | 1.141 |
| unintentional_injury | 1.058 | 1.259 (1.070–1.481) | — | 1.502 | 1.513 |

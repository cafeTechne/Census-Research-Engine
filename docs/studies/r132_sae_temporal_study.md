# Pre-Registered Study (Round 132): Arcsine & Rao–Yu Temporal Fay–Herriot Small-Area Poverty Estimation (2015–2019 vs. 2020–2024)

**Date:** 2026-11-26  
**Protocol SHA-256:** `55f4ae34e3c2b9dd7455ee9e713f5770308152cdf0a0093f855f57149d830c1b`  
**Script:** `scripts/r132_sae_temporal_study.py`  
**Review status:** Author self-review, not independent.

## Validated Small-Area MSE Gains (300 Counties)

| Region | Counties | Arcsine FH Median MSE Reduction | Rao–Yu Temporal FH Median MSE Reduction | Validated |
| :--- | ---: | ---: | ---: | :--- |
| MI / NY (`26`, `36`) | 145 | `8.6%` | **`26.3%`** | `True` / `True` |
| OH / PA (`39`, `42`) | 155 | `6.7%` | **`31.8%`** | `True` / `True` |

Borrowing strength across two non-overlapping ACS 5-year releases (2015–2019 and 2020–2024) via Round 80's validated Rao–Yu temporal Fay–Herriot estimator delivers a 3–4× larger MSE reduction than single-release arcsine shrinkage alone, replicating cleanly across MI/NY and OH/PA.

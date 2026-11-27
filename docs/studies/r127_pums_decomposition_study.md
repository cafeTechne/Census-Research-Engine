# Pre-Registered Study (Round 127): Disability Gaps in Earnings (Oaxaca–Blinder) and Poverty (Fairlie) among Working-Age Adults 25–64 (ACS 2019–2023 PUMS)

**Date:** 2026-11-26  
**Protocol SHA-256:** `a6bf3abc8cc2d269e623b7e21d8eb59f075350878c37b71dcac72ee493631bd8`  
**Script:** `scripts/r127_pums_decomposition_study.py`  
**Data:** Cached ACS 2019–2023 5-Year Person PUMS with 80 SDR replicate weights (`MI`: $N = 244{,}125$ working-age / $190{,}107$ earners; held-out replication `OH`: $N = 280{,}493$ working-age).  
**Review status:** Author self-review, not independent.

## 1. Validated Decomposition Results (90% SDR Intervals)

| Decomposition (Disability vs. No Disability) | Component | Michigan (`26`) | Ohio (`39`) | Replication |
| :--- | :--- | :--- | :--- | :--- |
| **Oaxaca–Blinder** (log earnings, earners 25–64) | Total gap | `-0.564` (`-0.591` to `-0.536`) | `-0.595` | **Replicated** |
| | Explained (age, BA+, sex) | **`-0.087`** (`-0.095` to `-0.078`, `15.4%`, `validated=True`) | **`-0.092`** (`-0.099` to `-0.085`, `15.4%`, `validated=True`) | **Replicated** |
| | Unexplained | **`-0.477`** (`-0.501` to `-0.452`, `84.6%`, `validated=True`) | **`-0.503`** (`-0.527` to `-0.478`, `84.6%`, `validated=True`) | **Replicated** |
| **Fairlie** (poverty rate, adults 25–64) | Total gap | `+17.92` pp (`+17.27` to `+18.56` pp) | `+19.02` pp (`+18.40` to `+19.65` pp) | **Replicated** |
| | Explained (age, BA+, sex) | **`+1.29` pp** (`+1.20` to `+1.38` pp, `7.2%`, `validated=True`) | **`+1.23` pp** (`+1.16` to `+1.30` pp, `6.5%`, `validated=True`) | **Replicated** |
| | Unexplained | **`+16.63` pp** (`92.8%`, `validated=True`) | **`+17.79` pp** (`+17.16` to `+18.43` pp, `93.5%`, `validated=True`) | **Replicated** |

## 2. Author Self-Review (Not Independent)
- Educational attainment (`ba_plus`) accounts for virtually the entire explained portion of both gaps (`-0.106` MI / `-0.113` OH log earnings; `+1.88` pp OH poverty), while 85–93% of the disability earnings and poverty gaps remain unexplained by basic demographics — consistent with labor-force participation, work-limiting hours, and structural employment barriers.
- Limitations: Cross-sectional 5-year PUMS; Oaxaca–Blinder conditions on positive earners (selection into employment is not modeled).

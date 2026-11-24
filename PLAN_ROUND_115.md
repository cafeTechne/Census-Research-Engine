# Plan — Round 115: Published Textbook & Reference Benchmark Suite (`v0.111.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Add an offline, deterministic reference-benchmark suite (`tests/test_reference_benchmarks.py` and `docs/replications/reference_benchmarks.md`) verifying exact numerical agreement of Rounds 76–112 statistical modules against published textbook examples and closed-form mathematical benchmarks.

## Deliverables
1. `tests/test_reference_benchmarks.py` — 8 independent published/textbook benchmarks:
   - **VanderWeele & Ding (2017)** E-value published table (`RR = 3.9` → `E = 7.26`; `RR = 2.0` → `E = 3.41`; `RR = 1.5` → `E = 2.37`).
   - **Rogan & Gladen (1978)** nondifferential misclassification closed-form prevalence/table inversion identity.
   - **Foundations of Epidemiology (ch. 7–8)** OCP/ovarian cancer Mantel–Haenszel pooled OR (`4/9 = 0.4444`) and Table 8-5 confounding/effect-modification classification.
   - **Chiang (1984) / CDC** abridged life table survival & life-expectancy identities (`l_0 = 100,000`, constant-hazard exact `e_0 = 1 / m`, Arriaga exact sum-to-total-`Δe_0` decomposition).
   - **Harrer et al. (2021)** random-effects meta-analysis inverse-variance fixed-effect & Paule–Mandel/HKSJ agreement with `statsmodels` WLS when $\tau^2 = 0$.
   - **Lin (1989)** exact analytical concordance correlation coefficient & symmetry/shift-sensitivity properties.
   - **Kitagawa (1955)** exact rate + composition = crude difference decomposition identity.
   - **Cunningham / Mixtape** sharp and fuzzy RDD exact noiseless linear/quadratic recovery and triple-difference exact noiseless treatment-effect recovery.
2. `docs/replications/reference_benchmarks.md`, `docs/audits/round115_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.111.0`.

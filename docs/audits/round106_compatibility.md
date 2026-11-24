# Round 106 compatibility audit

- **Version:** 0.102.0 (uncommitted on `phase103/agent-access-hygiene`).
- **Validation (`docs/audits/repairs106_validation.md`):**
  - **Passed and wired:** Lin's CCC delete-one-area Fisher-z jackknife (`C2`, `.886–.901` across all 6 cells;
    wired into `census/agreement.py`) and Hernán & Robins ch. 21 parametric g-formula with delete-one-unit cluster
    jackknife (`M5`, `.883–.920` across all 36 cells; wired into `census/msm.py` as `method="gformula"`).
  - **Failed and kept exploratory:** PUMS Hotelling `F` homogeneity (`H2c`: 11/12 cells ≤ `.13`, `rd K=5 n=300` at
    `.131`), FH bootstrap PPV with rule re-selection (`Q2c`: 7/8 cells ≥ `.86`, `N=1000 A=0.02 point` at `.850`),
    and Croon/Fuller ecologic slope (`E3`: `n_j=40` passed `.883–.888`, `n_j=20` at `.810–.825`).
- **Goldens:** `scripts/run_golden.py` verified byte-identical.
- **Rule text:** `scripts/sync_rule_text.py --check` passes.
- **Exceptions:** none.

# Round 105 compatibility audit

- **Version:** 0.101.0 (uncommitted on `phase103/agent-access-hygiene`).
- **Validation (`docs/audits/repairs105_validation.md`):**
  - **Passed and wired:** continuous RDD with CCT CER bandwidth `h_ik * n^(-1/20)` (`R1b`, `.877–.920` across all
    8 cells including strong curvature) and probabilistic misclassification propagating observed-table sampling error
    through `corrected_table` (`M1b`, `.890–.908` across all 5 cells).
  - **Failed and kept exploratory:** PUMS Hotelling `F` homogeneity (`H2b`, RR/OR `.102–.129` passed, RD non-null
    under varying baseline risk `.157–.262`), FH parametric bootstrap PPV (`Q2b`, `prob80` `.963–.975`, `point`
    `.843–.858`), and Firth-logit + L0 + cluster-jackknife MSM (`M4`, 34/36 cells ≥ `.86`, 2 `K = 18` duration-1
    cells at `.832`/`.852`).
- **Goldens:** `scripts/run_golden.py` verified byte-identical.
- **Rule text:** `scripts/sync_rule_text.py --check` passes.
- **Exceptions:** none.

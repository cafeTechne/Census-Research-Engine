# Round 104 compatibility audit

- **Version:** 0.100.0 (`phase104/repairs-and-manifests`).
- **Part 1 (exploratory-measure repairs; `docs/audits/repairs104_validation.md`):**
  - **Passed and wired:** Nagashima–Noma–Furukawa meta-analysis prediction interval (`P2`, `k ≥ 10`), truncated
    Knapp–Hartung meta-regression (`R2`, `k ≥ 10`), random-effects Egger / Thompson–Sharp test (`E2`, `k ≥ 10`),
    Kish `t(df_eff)` nearest-neighbour matching ATT (`M1b-ATT`), and BYM2 PC-prior + log-grid Jacobian (`B3`,
    gated at `median E ≥ 30` without suppressed counts).
  - **Failed and kept exploratory:** baseline-L0-stabilized cluster-jackknife MSM (`M3`: improved from `.805` to
    `.850–.918`, 34 of 36 cells ≥ `.86`, 2 duration-1 cells at `.850`/`.854`) and replicate bias-corrected WHO
    mean differences (`MD2`: improved over raw but still `.429–.752` at `G = 8`, small spread).
- **Part 2 (manifest support):** added `estimate_effect`, `spatial_scan`, `stratified` to `METHODS`, plus opt-in
  `args.marginal` / `args.impute` on `fit_replicate` and `args.who_measures` / `args.compare_years` on `disparity`.
- **Goldens:** `scripts/run_golden.py` verified byte-identical; `scripts/refactor_golden.py` differs only in the
  supported-method / supported-statistic list messages (intended; all existing manifest hashes and scientific
  results unchanged).
- **Rule text:** `scripts/sync_rule_text.py --check` passes.
- **Exceptions:** none.

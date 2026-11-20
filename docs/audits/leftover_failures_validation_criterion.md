# Round 62 criterion: leftover failures

Committed before the full run. Frozen (`validate_pins`): `scripts/leftover_failures_validation.py`, the cores it calls
(`census/scpc_core.py`, `census/pums_inequality_core.py`, `census/segregation.py`, `census/im_acs.py`,
`census/simulation.py`, `census/pums_tests.py`), the earlier scripts whose generators it imports unchanged (Rounds
30, 32, 50, 51, 52, 56, 57, 58), their target and count files, and this file. Per-draw seeds `[20280701 + cell, draw]`.

## Problems

- **A: binomial SCPC.**
  - Cells: Round 58's binomial N cells on MI/NY and OH/PA (8 cells, 2,000 draws) and its R cell (MI/NY, 100 km,
    reliability .7; 10,000 draws).
  - SCPC with ρ̄ .15 and .20; target β*.
  - A ρ̄ passes with coverage ≥ .86 in all nine cells.
- **B: Theil T in larger samples.**
  - Round 56's generator and targets with m = 8,000 households, ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0}; incomes I1
    and I2; 2,000 draws.
  - T1 is Round 60's log-transformed interval; T0 is the comparison.
  - Passes when T1 covers ≥ .86 in all four cells on both incomes. The engine gate would be 18,000 unweighted
    records.
- **C: clipped six-group counties.**
  - Round 57's design A on six groups (Round 50 Gamma observed counts, Round 51 Gaussian replicates clipped at
    zero), ρ ∈ {0, −.15}; 2,000 draws.
  - Round 52's bins and Round 50's bin rule with Round 57's per-bin affected-draw check (≥ .86 when ≥ 500 pairs).
  - The validated range (Round 52's range rule) is capped at the unclipped six-group range in the engine.

Failed draws count as non-coverage.

## Smoke run (not the audit)

One smoke run (20 draws per cell; the R cell 100) checked that every cell runs. No design value changed after it.

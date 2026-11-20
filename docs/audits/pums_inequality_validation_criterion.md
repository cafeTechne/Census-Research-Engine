# Round 56 criterion: PUMS income inequality measures

Committed before the full run with the targets file. Frozen (`validate_pins`): `scripts/pums_inequality_validation.py`,
the new `census/pums_inequality_core.py`, `scripts/pums_tests_validation.py` and `census/pums_tests.py` (the Round 32
generator and SDR factors, unchanged), `docs/audits/pums_inequality_targets.json` and this file. 2,000 draws per
cell; per-draw seeds `[20280201 + cell, draw]`.

## Design

- **Generator:** Round 32's `draw_sample`; cells ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0} × m ∈ {800, 3000}
  households (8 cells).
- **Incomes** from the generator's person income y₁:
  - **I1** = y₁;
  - **I2** = y₁^1.6;
  - **I3** = y₁ with zeros where D is true. In the reference population 29.97% of persons have zero income, not
    the "one in seven" first written in the plan; the plan text was corrected before freezing.
- **Measures** (`pums_inequality_core.measures`, weighted, one sort per income):
  - Gini, Theil T, Atkinson .5 and 1, log P90/P10, log P80/P20 and the top-decile share, on I1 and I2;
  - Gini and the top-decile share on I3;
  - Gini(A = 2) − Gini(A = 0) on I1, with per-replicate differences.
- **Variance:** SE = √(4/80 Σ(θ_r − θ)²); normal 90% interval.
- **Targets:** person-level population values from 2,000,000 reference households (seed `[20280201, 2000000]`,
  ρ = .25, unit weights), computed by `--prepare` with the same core and committed here. The reference Gini
  values are .335 (I1), .512 (I2) and .535 (I3).

## Acceptance

Coverage ≥ .86 in every cell for each (income, measure). Failed draws count as non-coverage. A measure is
validated when it passes on every income on which it is judged (17 judged pairs, 8 measures).

## Smoke run (not the audit)

One smoke run (40 draws per cell) checked that every cell runs. No design value changed after it.

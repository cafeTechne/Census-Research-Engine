# Round 60 criterion: PUMS inequality repairs

Committed before the full run. Frozen (`validate_pins`): `scripts/pums_inequality_repair_validation.py`, Round 56's
`scripts/pums_inequality_validation.py` (its `evaluate` is reused, unchanged), `census/pums_inequality_core.py` (new
`transformed_summary`, `bias_corrected`, `TRANSFORM`; Round 56 functions unchanged), the Round 32 generator and SDR
factors, `docs/audits/pums_inequality_targets.json` (Round 56) and this file. 2,000 draws per cell; per-draw seeds
`[20280601 + cell, draw]`.

## Design

- **Generator, cells, incomes and targets:** Round 56's, unchanged.
- **Judged:** Theil T and Atkinson .5 and 1 on I1 and I2; the top-decile share on I1, I2 and I3.
- **Procedures:**
  - **T0:** Round 56 normal SDR interval (comparison).
  - **T1:** the SDR SE of the transformed replicates (log for Theil; logit for Atkinson and the top share), with a
    normal interval on that scale, back-transformed.
  - **T2:** the SDR bias correction θ̂ − 4(mean θ_r − θ̂) (Round 50's), then T1's interval around the corrected value.

## Acceptance

- A measure is validated with T1, or else T2, when the procedure covers ≥ .86 in every cell on every income judged.
- Otherwise, if T1 or T2 covers ≥ .86 in every m = 3,000 cell, the measure is validated with a gate of at least
  7,000 unweighted records.
- Otherwise the measure stays exploratory.
- Failed draws (a value outside the transform's domain, or failed evaluation) count as non-coverage.

## Smoke run (not the audit)

One smoke run (30 draws per cell) checked that every cell runs. No design value changed after it.

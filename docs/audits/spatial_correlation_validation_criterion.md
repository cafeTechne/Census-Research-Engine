# Round 59 criterion: correlations under spatial dependence

Committed before the full run, with the OH/PA targets file. Frozen (`validate_pins`):
- `scripts/spatial_correlation_validation.py` and the new `census/partial_neff_core.py`;
- `census/small_spatial_core.py`, `census/rank_methods.py`, `census/index_core.py` and `census/simulation.py`;
- `scripts/spatial_hac_validation.py`, `scripts/rank_validation.py` and `scripts/index_validation.py`;
- `docs/audits/rank_targets.json` (MI/NY), the new `docs/audits/ohpa_correlation_targets.json`, both geometry files
  and this file.

2,000 draws per cell; per-draw seeds `[20280501 + cell, draw]`.

## Targets

`--prepare` recomputed Round 33's observed-value coefficient targets and Round 36's α targets for OH/PA. It uses the
same procedures, seeds and 400,000-area references, with the cell constants (area SEs, groups) drawn on the 155
OH/PA areas exactly as the Round 33/36 `setup` functions draw them. Before freezing, the geometry-aware setup was
checked against Round 33/36's on MI/NY: identical SEs and groups in cells 0 and 5.

## Problems

- **P (8 cells, MI/NY):** Round 33 cells with Round 48's draw. P1 = `partial_neff` (one control, replicate term);
  P0 = Round 33's independent-area partial interval (comparison). Target: Round 33's observed partial coefficient.
- **O (8 cells, OH/PA):** C1 (Round 48 effective-n: Spearman and Kendall without replicates, Pearson with
  replicates) and P1. Targets from the OH/PA file.
- **A (8 cells, OH/PA):** A3 (Round 48 effective-n Feldt α). Targets from the OH/PA file.

## Acceptance

Coverage ≥ .86 in every cell of the problem:
- P1 over P and O together (both geometries);
- C1 per method over O;
- A3 over A.

Failed fits count as non-coverage. Engine consequences are fixed in `PLAN_ROUND_59.md` section 3.

## Smoke run (not the audit)

One smoke run (40 draws per cell) checked that every cell runs. No design value changed after it.

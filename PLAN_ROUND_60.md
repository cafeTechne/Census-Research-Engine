# Round 60 plan: PUMS inequality repairs

**Goal.** Backlog issue N32 (`ROADMAP_BACKLOG.md` Round 60).

Round 56 validated the Gini, the quantile ratios and Gini differences. Four measures failed on the heavier-tailed
income, mostly in the smaller samples:

| Measure | Worst cell |
| :--- | :--- |
| Theil T | .811 |
| Atkinson .5 | .845 |
| Atkinson 1 | .858 |
| Top-decile share | .850 |

These measures are bounded below (Theil, Atkinson) or within (0, 1). Their sampling distributions are skewed, and
the plug-in estimators are biased toward zero in small samples. A symmetric interval around a biased estimate
under-covers.

Version 0.57.0. Baseline: the Round 59 suite (2117 passed, 37 skipped). Branch `phase60/inequality-repairs`.
Validation first.

## 1. Frozen core (`census/pums_inequality_core.py`, new functions)

- `transformed_summary(theta, kind)`: the SDR SE on a transformed scale, using log for Theil T and logit for
  Atkinson and the top share (each replicate is transformed), with a normal interval back-transformed. **T1.**
- `bias_corrected(theta)`: θ̂ − 4(mean θ_r − θ̂). This is Round 50's SDR bias correction: SDR replicate
  deviations have a quarter of the sampling variance, so the replicate mean shift estimates a quarter of the
  bias. **T2** applies it, then T1's transformed interval centred on the corrected value.

## 2. Validation (`scripts/pums_inequality_repair_validation.py` → `docs/audits/pums_inequality_repair_validation.md`/`.json`)

Round 56's generator, cells and targets, unchanged: the Round 32 design, 8 cells (ρ × weight CV × m ∈ {800, 3000}
households), incomes I1, I2 and I3, targets `docs/audits/pums_inequality_targets.json`. 2,000 draws per cell;
per-draw seeds `[20280601 + cell, draw]`.

**Judged:** Theil T, Atkinson .5 and Atkinson 1 on I1 and I2; the top-decile share on I1, I2 and I3. Procedures:
- T0: Round 56's normal interval (comparison);
- T1;
- T2.

**Acceptance.** For each measure and procedure, coverage must be ≥ .86 in every cell on every income judged; the
measure is then validated with that procedure (T1 preferred to T2 when both pass). If neither passes everywhere
but one passes in every m = 3,000 cell, that procedure is validated with a sample gate: at least 7,000 unweighted
records (3,000 households average about 7,500 persons). Otherwise the measure stays exploratory. Failed draws
count as non-coverage.

## 3. Engine (only what passes)

- `pums_inequality` reports each repaired measure with its validated procedure: the interval method, and for T2
  the corrected estimate next to the plug-in one. Where a gate applies, the measure is `validated` only when the
  unweighted record count meets it. Measures that fail remain exploratory with Round 56's interval.
- MCP `test_association(kind="inequality")` description and the PUMS recipe updated; rule text mirrored; STATUS,
  CHANGELOG, version, compatibility audit; tests (flags = audit, transforms by hand); goldens identical.
- **Exploratory example:** Round 56's Michigan earnings and income measures with the repaired intervals.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | `60a3b06` |
| Results | done | Atkinson 1 (T1), Atkinson .5 and top share (T1, 7,000 records); Theil fails; T2 worse (`60fb599`) |
| Engine, tests | done | `REPAIRED`, `interval` column, record gate; 4 new tests |
| Example | done | Michigan earnings/income re-run; `/tmp/r60_example_outputs.tar.gz` |
| Goldens, final suite | done | identical; 2121 passed, 37 skipped |
| Exceptions | none | Theil T stays exploratory |

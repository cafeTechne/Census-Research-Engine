# Round 62 plan: leftover failures

**Goal.** Backlog issue N38 (`ROADMAP_BACKLOG.md` Round 62). Three failures or gaps remain from Rounds 57–60.

1. **Binomial SCPC failed.** It covered .793 (ρ̄ .05) and .846 (ρ̄ .10) in the 100 km, reliability .9 cells. Binomial
   influence values are dominated by large-trial counties, so their spatial structure is stronger than the
   benchmark assumed. A stronger benchmark (larger ρ̄) widens the worst case.
2. **Theil T failed** with a log-transformed interval. Its worst 3,000-household cell covered .859. Larger samples
   may suffice, with a higher record gate.
3. **Clipped six-group segregation counties** were not tested (Round 57 covered two to five groups).

Version 0.59.0. Baseline: the Round 61 suite (2127 passed, 37 skipped). Branch `phase62/leftover-failures`.
Validation first.

## 1. Validation (`scripts/leftover_failures_validation.py` → `docs/audits/leftover_failures_validation.md`/`.json`)

Per-draw seeds `[20280701 + cell, draw]`. Generators and targets are imported from the rounds that defined them,
unchanged.

**A. Binomial SCPC (9 cells).**
- The four binomial Round 30 C1 cells on MI/NY and OH/PA (Round 58's N design), 2,000 draws each.
- Round 58's R cell (MI/NY, 100 km, reliability .7), 10,000 draws.
- SCPC with ρ̄ ∈ {.15, .20}; target β*.
- Passes for a ρ̄ when coverage is ≥ .86 in all nine cells.

**B. Theil T in larger samples (4 cells).**
- Round 56's generator and targets with m = 8,000 households, ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0}; incomes I1
  and I2; 2,000 draws.
- T1 (Round 60's log-transformed interval) and T0 (comparison).
- Passes when T1 covers ≥ .86 in all four cells on both incomes. The engine gate is then 18,000 unweighted records
  (8,000 households average about 20,000 persons).

**C. Clipped six-group counties (2 cells).**
- Round 57's design A (Round 50 observed counts, Round 51 Gaussian replicates clipped at zero) on race6 (White,
  Black, Asian, Hispanic, multiracial, other), ρ ∈ {0, −.15}; 2,000 draws.
- Round 52's bins, Round 50's bin rule and Round 57's per-bin affected-draw check.
- The clipped range is capped at the unclipped six-group range.

Failed draws count as non-coverage.

## 2. Engine (only what passes)

- **A:** `scpc.VALIDATED_RHO["binomial"]` gets the passing ρ̄ values, and `DEFAULT_RHO["binomial"]` becomes the
  smallest of them. The manifest check follows automatically.
- **B:** `pums_inequality.REPAIRED["theil_t"] = 18000` (log interval).
- **C:** a `CLIP_RANGES` key for six groups.
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit); goldens identical.
- **Exploratory example:** a binomial version of the OH/PA child-poverty slope (counts of poor children out of
  children) with SCPC, if A passes; otherwise the Michigan Theil T with its gate, if B passes.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Script, criterion commit | | |
| A / B / C results | | |
| Engine, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

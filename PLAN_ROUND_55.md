# Round 55 plan: short interrupted series and estimated reference populations

**Goal.** Backlog issues N25 and N26 (`ROADMAP_BACKLOG.md` Round 55).

**Interrupted series.** These are validated only at 30+ annual points: Round 48's AR(1) bootstrap-t covered
.883–.896 there. At 15 and 20 points it missed narrowly, mainly for the slope change with φ = .6 (.846 and
.857). REML intervals failed at every length (.79–.88). Annual county series rarely reach 30 points, so this
round tries two repairs aimed at the short-series problems: a downward-biased AR coefficient, and too few
effective observations for a variance estimate.

**SMR reference populations.** Indirect SMRs treat the reference person-years as fixed. Only reference deaths
carry Poisson uncertainty (Round 25). When the reference population is an ACS estimate (a state's age bands, for
example), its sampling error is ignored. This round adds that variance term.

Version 0.52.0. Baseline: the Round 54 suite (2088 passed, 37 skipped). Branch `phase55/short-series-reference`.
Validation first.

## 1. Frozen core

New `census/its_small_core.py`:
- `its_bootstrap_t_bc(y, X, rng, B=499)`: **I3**. Round 48's bootstrap-t, except the bootstrap series are generated
  with a bias-corrected AR coefficient: φ_bc = min(.95, φ̂ + (1 + 3φ̂)/n) (Kendall's first-order bias of the AR(1)
  estimator; φ̂ the REML estimate). The bootstrap-t statistic is centred on the full-sample fit as before.
- `its_ewc(y, X)`: **I4**. OLS coefficients with an equal-weighted cosine (EWC) long-run variance of the scores,
  using ν = max(2, round(0.4 n^{2/3})) cosine terms (Lazarus, Lewis, Stock and Watson 2018), and a t(ν) reference.

`census/standardize.py`: `indirect_standardize(..., reference_population_se=None)`. Per-band SEs of the reference
person-years add Σ_b (E_b/E)² (se_b/P_b)² to the log-SMR variance, next to the Poisson reference-death term (so
`reference_counts` is required). The reference rates are D_b/P_b. Ignoring a positive covariance between study and
reference estimates (internal standardization) is conservative, as for reference deaths.

All are pinned with the script and criterion.

## 2. Validation (`scripts/short_series_reference_validation.py` → `docs/audits/short_series_reference_validation.md`/`.json`)

2,000 draws per cell; per-draw seeds `[20280101 + cell, draw]`.

**I (6 cells).** Round 48's generator (`mci_core.its_design`, interruption at n/2 + 1, AR(1) errors with unit
innovation variance, level change 1 and slope change .2) with n ∈ {15, 20, 25} × φ ∈ {.3, .6}. Procedures: I2
(Round 48 bootstrap-t; comparison at the same seeds), I3, I4. Targets: both changes.

**R (8 cells).** Five bands with Round 24's rates as truth; reference person-years P_b = 200,000 × (1, 1, 1, .5,
.2); reference deaths D_b ~ Poisson(rate_b P_b) scaled so the total is 50 or 500 (D ∈ {50, 500}); the observed
reference population is P_b(1 + c·z_b), with SE c·P_b, for c ∈ {.02, .08}; study population fixed, E ∈ {10, 100};
O ~ Poisson(1.2 E). Procedures: **R1** with `reference_population_se`; **R0** without (Round 25 behaviour). Target
SMR 1.2 (study expected count from the true rates).

**Acceptance.**
- **I:** a procedure is validated down to the smallest n at which both changes cover ≥ .86 for both φ, and at
  every larger tested n. (At 30+ points, I2 stays validated by Round 48.)
- **R:** R1 passes with coverage ≥ .86 in all eight cells.
- Failed fits count as non-coverage.

## 3. Engine (only what passes)

- `interrupted_series(method="bootstrap_t_bc" | "ewc")` with `ITS_MIN_N` per method from the audit; MCP and recipe
  text. Below the validated n, results stay exploratory with a note.
- `indirect_standardize(reference_population_se=...)`; manifests `smr` `args.reference_population_se` (column or
  list), refused unless reference counts are given. Registered manifests are unchanged.
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit); goldens identical.
- **Demonstration instead of a data example.** No real series is suitable offline: overlapping five-year ACS
  releases are autocorrelated by construction, and WONDER annual series would need new owner exports. No real
  ACS-estimated reference population is available either: WONDER reference person-years are fixed Census estimates.
  So the round ends with a labelled demonstration on simulated inputs, showing the engine output for each validated
  method next to the methods that failed. This is recorded as an exception.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | `dd6d6b7` |
| I / R results | done | bias-corrected bootstrap-t validated from 20 points; EWC fails; reference-population SE passes (`881c410`) |
| Engine, tests | done | `bootstrap_t_bc`, `reference_population_se` (library, manifest args); 6 new tests |
| Example | done | demonstration on simulated inputs (`r55_demonstration.md`) |
| Goldens, final suite | done | identical; 2094 passed, 37 skipped |
| Exceptions | see notes | demonstration instead of a data example; plain bootstrap-t threshold kept at 30 (comparison arm passed from 25) |

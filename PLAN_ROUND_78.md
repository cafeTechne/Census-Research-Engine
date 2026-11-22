# Round 78 plan: staggered-adoption DiD and synthetic control

**Goal.** Backlog N55. State policies (Medicaid expansion, naloxone and PDMP laws) start in different years. A
two-way fixed-effects DiD is biased under staggered adoption with heterogeneous effects (Goodman-Bacon 2021), and
single-unit policies need synthetic control. Data are annual state panels: ACS 1-year state estimates (annual and
non-overlapping; 2020 has no standard release) and the owner's WONDER state exports. Version 0.74.0. Branch
`phase78/policy`. Validation first.

## 1. Methods (frozen core `census/policy_core.py`)

- **S1: Callaway–Sant'Anna (2021).**
  - Group-time ATT(g, t) with never-treated, or not-yet-treated, controls; outcome-regression or doubly robust.
  - Aggregates: event-study by event time, and the overall ATT.
  - Interval: a state-cluster multiplier bootstrap with uniform bands for the event study.
  - With ACS outcomes, the replicate SE of each state-year adds in quadrature (S1r), and is reported separately.
- **S2: Sun–Abraham (2021)** interaction-weighted event study, as a comparison; its interval is cluster-robust.
- **C1: synthetic control** (Abadie et al. 2010), with weights on the simplex, fitted on pre-period outcomes.
  - Inference: placebo-in-space permutation of the post/pre RMSPE ratio, giving a p-value.
  - C2: conformal per-period intervals (Chernozhukov, Wüthrich and Zhu 2021).
- **Diagnostics:** pre-trend test (S1); pre-period fit RMSPE (C1). Poor pre-fit makes C1 exploratory, with the
  threshold fixed in the criterion.

## 2. Validation (`scripts/policy_validation.py`)

- **Panel:** 50 states + DC, T = 12 and 18 years; a state effect plus an AR(1) state-year error (ρ .3 and .7).
- **Treatment:** staggered adoption in 3 cohorts, plus never-treated states; effects constant or growing with event
  time.
- **ACS-like error:** state-year CVs from 2010–2023 1-year state estimates.
- **S1/S2:** coverage of the overall ATT and of each event-time effect, with a ≥ .86 pass; uniform-band coverage is
  reported.
- **C1:**
  - one treated state;
  - size of the placebo test ≤ .10 under no effect (at nominal .10), with power reported;
  - C2 coverage ≥ .86 per post period.
- **Draws:** 1,000 per cell.

## 3. Engine (only what passes)

- **Tool:** `difference_in_differences` gains `design="staggered"` (cohort column `first_treated`), keeping
  two-group designs as they are.
- **New full-profile tool:** `synthetic_control(input_path, unit, time, outcome, treated_unit, treatment_year)`.
- **Manifests:** `did` with the staggered design; `synthetic_control` (statistics `att`, `event_time`, `placebo_p`).
- **Recipe:** `policy_change` updated, with the route choice (two groups, staggered, single unit, annual series)
  and its assumptions.
- **Refusals:** overlapping 5-year releases, and 2020 ACS 1-year values (no standard release).

## 4. Example and acceptance

- **Example (exploratory):** ACA Medicaid expansion and the state uninsured rate, ACS 1-year 2010–2023 (2020
  skipped), with S1 event study.
  - The published literature finds ~3–5 point reductions (e.g. Courtemanche et al. 2017). This is a descriptive
    comparison, not a registered replication.
  - If a registered replication is wanted, it becomes its own round with a pre-set rule.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `policy_core.py`, `policy_validation.py`; criterion `baf934b` (tag `criterion-r78`) |
| Results | done | Sun-Abraham and CS + ACS variance pass; CS bootstrap alone, uniform bands, synthetic control (C1, C2) fail |
| Engine, manifest, tools | done (no manifest, no new tool) | `census/staggered.py`; `difference_in_differences(design="staggered")`; synthetic control library-only |
| Example | done | `r78_medicaid_example.md`: overall ATT -1.23 points (-2.18 to -0.27) |
| Goldens, suite | done | both goldens byte-identical; 2235 passed, 42 skipped |
| Exceptions | listed | `round78_compatibility.md` |

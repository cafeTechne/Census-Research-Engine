# Round 76 plan: between-group disparity measures and Kitagawa decomposition

**Goal.** Backlog N53. Public-health disparity reports (NCI HD*Calc; Harper and Lynch 2005) compare **population
groups** within one area: race/ethnicity groups, income groups, sexes. The engine has area-gradient indices
(SII/RII, concentration) but no between-group measures. Version 0.72.0. Branch `phase76/disparities`. Validation
first.

## 1. Measures (frozen core `census/disparity_core.py`)

Inputs per group g: a rate r_g, a population share or weight p_g, and the rate's uncertainty. The uncertainty
comes from ACS group rates (B17001A–I, C27001A–I and similar), with 80 replicates per group, or from counts, with
Poisson variance.

| Measure | Definition | Interval candidate |
| :--- | :--- | :--- |
| RD, RR vs reference | r_g − r_ref, r_g / r_ref | D1: replicate SE (ACS) / Poisson delta (counts); log scale for RR |
| Index of Disparity (Pearcy–Keppel) | 100 × mean_g \|r_g − r_ref\| / r_ref | D2: replicate SE of the whole index; D2b: Poisson parametric bootstrap |
| Between-group variance (BGV) | Σ p_g (r_g − r̄)² | D3: replicate SE; log-normal interval |
| Theil T and mean log deviation over groups | Σ p_g (r_g/r̄) ln(r_g/r̄); Σ p_g ln(r̄/r_g) | D4: replicate SE on the log scale |

- The reference group is declared, never chosen after looking.
- Absolute (RD, BGV) and relative (RR, IDisp, Theil, MLD) measures are reported together, as Harper and Lynch
  recommend.

## 2. Kitagawa decomposition

The difference between two areas' crude rates splits into a **rate effect** and a **composition effect** across
strata, such as age bands: Kitagawa (1955), symmetric weights. Interval candidate K1: replicate (or Poisson)
variance of each component.

## 3. Validation (`scripts/disparity_validation.py`)

- **ACS-like designs:**
  - group rates with realistic ACS group CVs, drawn from real B17001A–I tract and county MOEs in MI/NY (Round 52's
    noise bins);
  - 2, 4 and 6 groups;
  - small-group CV levels .10, .30 and .50;
  - correlated replicate errors from Round 52's generator.
- **Count designs:** Poisson counts with expected 20, 100 and 1,000 per group.
- **Draws:** 2,000 per cell.
- **Pass:** coverage ≥ .86 in every cell for that measure and design. A measure that fails only at CV .50 is
  validated with that range gate, as Round 50 did for segregation.
- **Kitagawa:** the same cells with 10 age strata.

## 4. Engine (only what passes)

- **Manifest method `disparity`:** groups as manifest variables, a reference group, and the statistic `rd`,
  `log_rr`, `idisp`, `bgv`, `theil` or `mld`.
- **Manifest method `kitagawa`.**
- **Full-profile tool:** `disparity_measures(input_path, groups=[...], reference=...)`.
- **Recipe:** `health_inequality` gains a "between groups" section, cross-linked from `segregation`.
- **Rule:** measures need mutually exclusive groups that cover the universe, or the result says which groups are
  omitted.

## 5. Example and acceptance

- **Example:** MI/NY county child poverty by race/ethnicity (B17020A–I), with RR vs White non-Hispanic and IDisp,
  with intervals (exploratory).
- STATUS, CHANGELOG, compatibility audit, tests (flags = audit), goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `disparity_core.py`, `disparity_validation.py`; criterion `e995978` (tag `criterion-r76`) |
| Results | done | ACS rd/idisp to CV .50, log_rr/bgv/theil/mld to .30; counts rd/log_rr pass, count indices fail; Kitagawa passes |
| Engine, manifest, tool | done | `census/disparity.py`; manifest `disparity`, `kitagawa`; tool `disparity_measures` (72 tools); recipe section |
| Example | done | `r76_disparity_example.md` (B17010 family poverty; B17020 has no VRE file) |
| Goldens, suite | done | run golden identical; schema golden: method list only; 2223 passed, 42 skipped |
| Exceptions | listed | `round76_compatibility.md`: example table, simulated CVs, count manifests not offered |

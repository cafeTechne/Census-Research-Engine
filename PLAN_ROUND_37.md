# Round 37 plan: agreement between data sources

**Goal.** Before one source stands in for another (ACS vs PLACES, ACS vs Census population estimates,
ACS vs decennial counts), show how well they agree. Agreement statistics computed on noisy
estimates mix real disagreement with sampling error. This round:

- **(A)** validates Bland–Altman bias and limits of agreement, Lin's concordance correlation (CCC)
  and Cohen's kappa, each for the observed estimates and, where the sources' SEs are known, for the
  error-free values;
- **(B)** ships `census/agreement.py` and an MCP tool `check_agreement` (full profile);
- **(C)** runs one exploratory example: ACS 2018–2022 county population vs the Census Bureau's
  population estimates in the owner's WONDER county exports (MI/NY).

Version 0.34.0. Baseline: 1946 passed, 37 skipped. Ground rules as Round 31 (branch
`phase37/agreement`; validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures (n areas; source A = x with SE aᵢ, source B = y with SE bᵢ or none; d = y − x)

| ID | Quantity | Interval (90%) |
| :--- | :--- | :--- |
| B0 | bias d̄ | t(n − 1) |
| B1 | limits of agreement of the observed values, d̄ ± 1.645 s_d | Bland–Altman: SE² = s_d²(1/n + 1.645²/(2(n − 1))), t(n − 1) |
| B2 | limits for the error-free values, d̄ ± 1.645 s_t, s_t² = s_d² − mean(aᵢ² + bᵢ²) | delta method, Var(s_d²) ≈ 2s_d⁴/(n − 1) |
| C1 | CCC of the observed values | Lin (1989) z-transform variance |
| C2 | CCC of the error-free values (error variances removed from s_x², s_y²) | C1's formula at the corrected values |
| K1 | Cohen's kappa of the two sources' quintile classes | asymptotic SE (statsmodels `cohens_kappa`) |

Sources' errors are assumed independent of each other (different surveys or models).

## 2. Validation (`scripts/agreement_validation.py` → `docs/audits/agreement_validation.md`/`.json`)

- 145 MI/NY counties (Round 30 coordinates); true value t a Gaussian field (independent or 100 km);
  A = t + error (lognormal SEs, reliability 0.9 or 0.7); B = 0.2 + 1.05 t (+ error at reliability 0.8
  with known SEs, or no error).
- Targets: observed-value quantities (B1, C1, K1) from a 400,000-area reference per cell; error-free
  quantities (B2, C2) from the same reference's true values; B0's target is the bias 0.2 + 0.05·E[t].
- Cells: A reliability {0.9, 0.7} × B error {none, reliability 0.8} × field {independent, 100 km}:
  8 cells; 2,000 draws; seed `20270128 + cell`.
- **Acceptance:** 90% coverage ≥ .86 in every independent cell, per procedure (both limits for B1 and
  B2); spatial cells informational.

## 3. Engine, tool, example, tests

`check_agreement(frame, a, b, a_se/replicates, b_se=None)` returns all passing quantities with
validated flags and notes; the MCP tool wraps it. Recipe `agreement`; mirrored rule text. Example as
in the goal (ACS replicates for A; the population estimates treated as without sampling error).
Tests: formulas by hand, CCC against its definition, kappa against statsmodels, flags against the
audit, tool offline. Goldens unchanged; full suite; STATUS, CHANGELOG, version 0.34.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `e6d4be6` | Pushed before the full run; δ added before freezing. |
| B0–B2 / C1–C2 / K1 results | Mixed | B0, K1 passed; B1, B2, C1, C2 failed. |
| Engine, tool, tests | Done | check_agreement library and tool; 5 tests. |
| Example | Done | ACS vs population estimates. |
| Goldens, final suite | Done | Goldens identical; 1951 passed, 37 skipped, 0 failures. |
| Exceptions | Recorded | Design change (δ) before freezing. |

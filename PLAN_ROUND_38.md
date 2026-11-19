# Round 38 plan: combining evidence — meta-analysis, equivalence and power

**Goal.** Replications (MI/NY and OH/PA, more states later) produce several estimates of one
effect. Pooling them, saying whether two estimates are practically equivalent, and planning how many
areas a study needs are missing. This round:

- **(A)** validates pooled-effect intervals for few studies, TOST equivalence, and z-test power;
- **(B)** ships `census/evidence.py` and an MCP tool `combine_estimates` (full profile);
- **(C)** runs one exploratory example: Round 29's MI/NY and OH/PA mortality coefficients.

Version 0.35.0. Baseline: 1951 passed, 37 skipped. Ground rules as Round 31 (branch
`phase38/evidence`; validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures (k estimates θ̂ᵢ with SEs sᵢ)

| ID | Pooled-effect interval (90%) |
| :--- | :--- |
| M1 | fixed effect (inverse variance), normal |
| M2 | random effects, DerSimonian–Laird τ², normal |
| M3 | random effects, Paule–Mandel τ², Hartung–Knapp–Sidik–Jonkman variance, t(k − 1) |

Also reported: Q, I², τ², and the Higgins prediction interval (t(k − 2), k ≥ 3; descriptive).
**E1** TOST equivalence of two independent estimates within ±Δ (two one-sided z tests at .05 each;
equivalent if both reject). **P1** power of a two-sided z test of an effect δ with SE s (normal);
minimum detectable effect at 80% power.

## 2. Validation (`scripts/evidence_validation.py` → `docs/audits/evidence_validation.md`/`.json`)

- Studies: k ∈ {2, 4, 8}; true effects θᵢ = μ + uᵢ, uᵢ ~ N(0, τ²) with τ² ∈ {0, mean(sᵢ²)}; sᵢ lognormal
  (log-SD 0.5); θ̂ᵢ = θᵢ + N(0, sᵢ²); SEs estimated from 80 replicates (scaled χ² with 80 df).
- Cells: k × τ²: 6 cells for M1–M3 (target μ); 2,000 draws; seed `20270204 + cell`.
- E1: size at the margin (true difference = Δ) ≤ .07 at nominal .05, and power at difference 0
  reported, with SEs from replicates; 2 cells (equal and unequal SEs).
- P1: |predicted − empirical rejection rate| ≤ .03 at predicted power .5 and .8, 4 settings.
- **Acceptance (pre-set):** M: 90% coverage ≥ .86 in every cell it is judged on — M1 only where
  τ² = 0 (it assumes homogeneity), M2 and M3 in all cells; per k, ship the passing methods; E1 and P1
  as stated.

## 3. Engine, example, tests

`combine_estimates(estimates, ses, method)`, `equivalence(est1, se1, est2, se2, margin)`,
`power_z(effect, se)` / `mde_z(se, power)`; validated flags per k. MCP tool `combine_estimates`
(kind = "pool" | "equivalence" | "power"). Recipe `combine_estimates`; mirrored rule text. Example: pool
R29 H1–H3 across MI/NY and OH/PA (k = 2: fixed effect only if validated; random effects labelled),
heterogeneity, and TOST with Δ = 0.01 per percentage point. Tests: formulas against statsmodels
`combine_effects`, TOST and power by hand, flags against the audit. Goldens unchanged; full suite;
STATUS, CHANGELOG, version 0.35.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | | |
| M1–M3 / E1 / P1 results | | |
| Engine, tool, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |

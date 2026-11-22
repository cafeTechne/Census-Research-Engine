# Round 76 criterion: between-group disparity measures and Kitagawa decomposition

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/disparity_validation.py`;
- `census/disparity_core.py` (new);
- `census/simulation.py` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run at 20 draws per cell, which only checked that the script runs (at 20 draws coverage cannot be judged);
- four 10-draw chunk probes, which checked that coverage counts come back with the right shapes.

## Measures and intervals (`census/disparity_core.py`)

| Measure | Definition | ACS interval | Count interval |
| :--- | :--- | :--- | :--- |
| rd | r_g − r_ref per non-reference group | D1: replicate SE, identity scale | D1: Poisson delta |
| log_rr | log(r_g / r_ref) | D1: replicate SE | D1: delta, 1/d_g + 1/d_ref |
| idisp | 100 × mean over non-reference groups of \|r_g − r_ref\| / r_ref | D2: replicate SE of log idisp | D2b: Poisson parametric bootstrap (B = 500), SE of log idisp |
| bgv | Σ p_g (r_g − r̄)² | D3: replicate SE, log scale | D2b |
| theil | Σ p_g (r_g/r̄) ln(r_g/r̄) | D4: replicate SE, log scale | D2b |
| mld | Σ p_g ln(r̄/r_g) | D4 | D2b |

All intervals are 90% normal intervals on the stated scale, back-transformed. Replicate statistics that are not
finite (for example a negative replicate rate under log) make that interval missing; missing intervals count as
non-coverage. No clipping.

**Kitagawa (K1):** the symmetric decomposition of the difference in crude rates into a rate effect and a
composition effect. Intervals use the replicate SE of each component (ACS) or the Poisson variance of the stratum
rates through the linear weights, with populations known (counts).

## Designs (2,000 draws per cell)

- **ACS (9 cells):** G ∈ {2, 4, 6} × smallest-group rate CV c ∈ {.10, .30, .50}.
  - Poverty-like true rates (.10, .22, .30, .16, .35, .26) and population shares (.60, .15, .10, .08, .04, .03),
    first G of each; group 0 is the reference.
  - Rate CV_g = max(.05, c·√(min p / p_g)), with the reference at .05. Population-count CV = CV_g / 2.
  - Gaussian-copula Gamma observation errors with correlation .2 among rates, .2 among populations and −.2 between a
    group's rate and its population. The 80 replicates use the same correlation and SE = true SE.
  - **Deviation from the plan, made before any run:** CVs are set at the plan's three levels directly rather than
    drawn from real B17001A–I MOE files. The levels span the Round 52 noise bins up to .50; the example reports the
    real county CVs so the range gate can be applied.
- **Counts (9 cells):** G × expected count per group E ∈ {20, 100, 1,000}, with mortality-like rates and known
  populations.
- **Kitagawa (6 cells):** 10 age strata in two areas whose rates and age structures differ.
  - ACS cells: stratum-rate CV c ∈ {.10, .30, .50}, with composition-count CV c/2.
  - Count cells: mean expected count per stratum E ∈ {20, 100, 1,000}.

## Pass rule

- Per measure and design: **coverage ≥ .86 in every cell**. For rd and log_rr, every non-reference contrast counts.
  For Kitagawa, the difference, the rate effect and the composition effect are each judged.
- **Range gates (stated before the run):**
  - a measure that fails only at c = .50 is validated for a smallest-group CV ≤ .30;
  - a measure that fails only at E = 20 is validated for expected counts ≥ 100 per group or stratum.
- Any other failure leaves the measure exploratory for that design.

Seeds: `[20281601 + design offset + cell, chunk]`.

## Engine (only what passes)

- **Manifest method `disparity`** and the full-profile tool `disparity_measures`. Statistics that failed stay
  exploratory, and a registered manifest that tests them is refused.
- **Manifest method `kitagawa`**, under the same rule.
- Groups must be mutually exclusive. Results list any omitted groups.

# Round 81 plan: spatial scan statistic for county counts

**Goal.** Backlog N58. Cluster detection for disease counts (Kulldorff 1997; SaTScan) is standard in public-health
surveillance: is there a group of neighbouring counties with an unusually high rate? The engine has global and
local Moran's I (LISA, characterised as descriptive under sampling error), but no scan statistic. Version 0.77.0.
Branch `phase81/scan`. Validation first.

## 1. Method (frozen core `census/scan_core.py`)

- **K1: Poisson spatial scan.**
  - Circular windows centred on county representative points, up to 50% of the at-risk population (a maximum also
    at 10%, 25%).
  - Expected counts from an indirectly standardised offset (the Round 73 helper) or from population.
  - Likelihood-ratio statistic, with a Monte Carlo p-value from 999 replicates under the null (multinomial
    conditional on the total).
  - Secondary clusters that do not overlap are reported (Gumbel-approximated p-values as a comparison).
- **Counts:** fully observed only.
  - WONDER county counts 1–9 are suppressed, so a scan on WONDER data is refused unless the suppressed counties
    are excluded with a stated rule, or the counts come from a source without suppression (births, CHR).
  - No 1–9 count is ever imputed or output.

## 2. Validation (`scripts/scan_validation.py`)

- **Geometries:** MI and NY counties, and OH/PA.
- **Null:** expected counts 5, 20 and 100 per county. **Pass:** the type I error of the primary cluster test at α
  .10 lies in [.07, .13] in every cell.
- **Power** is reported (not a pass criterion) with planted clusters of 1, 3 and 8 counties at relative risk 1.5
  and 2.
- **Location accuracy** (sensitivity and positive predictive value of the detected cluster) is reported.
- **Draws:** 1,000 per cell.
- **ACS denominators:** population from ACS estimates carries sampling error. A sensitivity cell refits with the
  denominators drawn from their replicates, and the size there is reported.

## 3. Engine (only what passes)

- **Tool:** `spatial_scan(input_path, cases, population|expected, level="county", year, max_population=0.5)` in
  the full profile. Its output gives the cluster, its counties, RR, LLR and p-value, and the secondary clusters.
- **Recipe:** `spatial_patterns` gets a scan section: when to use a scan rather than LISA, multiple-window
  caveats, and the WONDER suppression rule.
- **Manifests:** not added. Cluster detection is exploratory by nature; the tool says so unless a pre-registered
  window and α are declared, which the plan leaves for a later round.

## 4. Example and acceptance

- **Example (exploratory):** MI/NY county low-birth-weight births (CHR&R counts, no suppression in the counts used),
  with the primary cluster, a map and RR.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `scan_core.py`, `scan_validation.py`; criterion `b6b69d0` (tag `criterion-r81`) |
| Results | done | K1 size .099-.116 passes; noisy denominators inflate size (.15-.53, reported) |
| Engine, tool, recipe | done | `census/scan.py`; tool `spatial_scan` (75 tools); `spatial_patterns` section |
| Example | done | `r81_scan_example.md`: Wayne County LBW cluster, RR 1.37 (no map) |
| Goldens, suite | done | both goldens byte-identical; 2249 passed, 42 skipped |
| Exceptions | listed | `round81_compatibility.md` |

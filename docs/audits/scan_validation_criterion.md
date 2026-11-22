# Round 81 criterion: Kulldorff Poisson spatial scan

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/scan_validation.py`;
- `census/scan_core.py` (new);
- the design file `docs/audits/scan_geometry.csv`;
- this file.

**Seen before this commit:**
- the design file: 2022 county populations (B01003) and representative points for MI+NY (145 counties) and OH+PA
  (155);
- one smoke run (2 draws per cell), which only checked that the script runs;
- two single-draw probes on MI+NY at a mean of 20 expected per county:
  - a null draw, with primary p .126;
  - a planted three-county cluster at RR 2, found exactly with p .001.

## Method (`census/scan_core.py`)

- **Windows.** Circular windows of the k nearest counties to each centre (great-circle distance). A window may hold
  up to 50% of the expected total.
- **Statistic.** The high-rate Poisson LLR, with the expected counts scaled to the observed total.
- **Primary cluster.** The window with the maximum LLR. Its p-value comes from Monte Carlo: 999 multinomial null
  data sets, conditional on the total.
- **Secondary clusters.** Clusters that do not overlap, with the same max-LLR p-value, plus a Gumbel approximation
  as a comparison.

## Designs

- **Null (6 cells, 1,000 draws each):** expected counts proportional to population, with a mean of 5, 20 or 100 per
  county, on both geometries.
- **Sensitivity (6 cells, 1,000 draws each, reported only):** the same, but the analysis denominators carry ±5%
  independent ACS-like error.
- **Power (36 cells, 250 draws each, reported only):** planted clusters of 1, 3 or 8 counties around a fixed centre
  (26065 for MI+NY, 42027 for OH+PA), at RR 1.5 or 2. Sensitivity and PPV of the detected primary cluster are
  reported.
- **Deviation from the plan, made before any run:** power cells use 250 draws rather than 1,000. Each draw runs 999
  Monte Carlo scans, and power is not a pass criterion.
  - The plan's 10% and 25% window maxima are offered as engine options but not simulated. Validation uses 50%.

## Pass rule

- **K1:** the rejection rate of the primary-cluster test at α .10 lies in [.07, .13] in every null cell.

Seeds: `[20282101 + cell, draw]`.

## Engine (only what passes)

- **Tool:** `spatial_scan` (full profile), with the primary and secondary clusters, RR, LLR and p-values.
- **Validity:** the p-value is validated for the 50% maximum window if K1 passes. Other maxima are exploratory.
  Cluster detection stays descriptive unless the window and α were declared in advance.
- **Refused:**
  - WONDER data containing suppressed counties, unless they are excluded by a stated rule;
  - imputed or output counts of 1–9.

# Round 85 plan: area designations as screening tests

**Goal.** Backlog N62. Public-health programs designate areas by thresholds on ACS estimates, for example "tract
poverty at least 20%", the top quintile of need, or HUD-style qualifying tracts. Sampling error misclassifies areas.
Chapter 11 of *Foundations of Epidemiology* gives the language for this:
- the designation is a test;
- sensitivity and specificity describe it;
- PPV and NPV depend on how common truly qualifying areas are.

The engine gives MOEs but no accuracy statement for a designation. Version 0.81.0. Branch `phase85/designation`.
Validation first.

## 1. Methods (frozen core `census/designation_core.py`)

- **Q1: per-area probability of truly exceeding the threshold.**
  - Q1a uses the direct estimate with its replicate SE (normal on the logit scale for proportions).
  - Q1b uses the Fay–Herriot posterior (Round 80 arcsine model for proportions).
- **Q2: expected accuracy of a designation rule** across the areas:
  - expected true positives, false positives and false negatives, sensitivity, specificity, PPV and NPV, computed
    from the Q1 probabilities;
  - rules compared: point estimate ≥ threshold, lower 90% bound ≥ threshold, posterior probability ≥ .5 or ≥ .8;
  - Q2 is the sum over areas of probability-weighted classifications.
- **Q3: a rank-based designation** ("top k areas") with the Round 34 rank intervals, giving the expected overlap
  with the true top k.

## 2. Validation (`scripts/designation_validation.py`)

- **Geometries:** MI/NY tracts and counties with real MOEs (Round 80's n_eff file and S1701 poverty), and true
  proportions from the Fay–Herriot generator.
- **Thresholds:** placed so that 10%, 25% and 50% of areas truly qualify.
- **Draws:** 1,000 per cell.
- **Pass:**
  - **calibration of Q1:** among area-draws with a predicted probability in each decile bin, the realized share
    truly above the threshold lies within ±.05 of the bin mean, in every bin with at least 200 area-draws;
  - **Q2:** the predicted sensitivity, specificity, PPV and NPV each lie within ±.05 of the realized values on
    average, and the 90% interval of the realized PPV covers the prediction in ≥ 86% of draws;
  - Q3 is reported only.

## 3. Engine (only what passes)

- **Tool `designation_accuracy(input_path, column, se_col | replicates_path, threshold, rule=...)`** (full
  profile). It returns per-area probabilities and the rule comparison table.
- **Recipe `small_area` section "Designating areas":**
  - choose the rule by the cost of false positives against false negatives;
  - report the expected PPV and sensitivity with any list of designated areas.

## 4. Example and acceptance

- **Example (exploratory):** MI tracts at the 20% poverty threshold.
  - The number designated under each rule, the expected PPV and sensitivity, and how many tracts change status
    between rules.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, tool, recipe | | |
| Example | | |
| Goldens, suite | | |
| Exceptions | | |

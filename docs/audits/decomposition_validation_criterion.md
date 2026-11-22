# Round 79 criterion: Oaxaca–Blinder and Fairlie decompositions with SDR replicate weights

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/decomposition_validation.py`;
- `census/decomposition_core.py` (new);
- Round 32's `scripts/pums_tests_validation.py` and `census/pums_tests.py` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run (4 draws per cell), which only checked that the script runs. It showed that the reference
  populations reach the intended explained shares (.2 and .6 exactly for both estimators);
- checks on a synthetic sample:
  - detailed parts sum to the totals;
  - Yun-normalised categorical contributions do not depend on the reference category;
- timing: Fairlie with 100 orderings and 80 replicates took 3 s on 4,000 persons.

## Methods (`census/decomposition_core.py`)

- **O1: twofold Oaxaca–Blinder with the pooled reference.** The pooled WLS includes the group indicator (Neumark;
  Jann).
  - Detailed explained contributions per covariate block, and detailed unexplained contributions with
    categoricals normalised (Yun 2005), plus the intercept.
  - The threefold decomposition is reported but not judged.
- **F1: Fairlie, logit.** The pooled weighted logit includes the group indicator.
  - The total explained part is the difference in weighted mean predicted probabilities.
  - Detailed contributions come from rank-matched pairs, with random block orders over R orderings and pair weights
    w_A·w_B, rescaled to sum to the explained total. Pairs and orders are reused for every replicate weight.
- **Variance:** SDR, refitting with each of the 80 replicate weights; var = 4/80 Σ (θ_r − θ)². Normal 90%
  intervals.

## Design (12 cells, 1,000 draws each)

- **Sampling:** Round 32's design, with weight CV 1.0, household correlation .25 and SDR factors in geographic
  order.
- **Groups:** A is about two thirds of persons, B the rest. B's sample size is 300, 1,000 or 5,000 persons.
- **Covariates:** 3 or 8 blocks: continuous covariates whose group-B mean is lower by .5, and one 5-level
  categorical.
- **Outcomes:**
  - a linear outcome with a slope difference;
  - a binary logit outcome.
  - In each, the group intercept is set so that the reference-population explained share is .2 or .6.
- **Targets:** the same estimators on a reference population of 300,000 households with unit weights (Fairlie: 20
  orderings).
- **Deviation from the plan, made before any run:** each validation draw uses 10 Fairlie orderings (the engine
  default is 100). With fewer orderings the point estimate carries more matching noise, which the replicate SE
  does not include, so this test is conservative for the engine.

## Pass rule

- **Quantity families, judged separately:**
  - O1 totals (explained, unexplained);
  - O1 detailed (every block, explained and unexplained, plus the intercept);
  - F1 totals;
  - F1 detailed.
- A family passes if 90% coverage is ≥ .86 for every quantity in every cell.
- **Size gate:**
  - a family failing only at size 300 is validated from 1,000;
  - a family failing only at sizes 300 and 1,000 is validated from 5,000;
  - anything else fails (exploratory).

Seeds: `[20281901, k, s]` for reference populations; `[20281911 + cell, draw]` for draws.

## Engine (only what passes)

- A decomposition tool (`decompose_gap` in the full profile) reports each family as validated or exploratory, with
  the size gate on group B's unweighted record count.
- Model-based (design-blind) SEs are not offered.
- "Explained" means statistical composition, not a causal effect.

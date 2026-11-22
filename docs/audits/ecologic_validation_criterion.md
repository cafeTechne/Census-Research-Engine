# Round 87 criterion: ecologic versus individual-level associations on PUMS

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/ecologic_validation.py`;
- `census/ecologic_core.py` (new);
- Round 32's `scripts/pums_tests_validation.py` and `census/pums_tests.py` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run (2 draws per cell), which only checked that the script runs;
- reference targets for two designs. With no covariates the ecologic (C2) slope equals the between-area slope and
  the ecologic gap equals the contextual effect, which is the textbook identity;
- one timing probe (0.5 s per draw at 30,000 records with the logit).

## Methods (`census/ecologic_core.py`)

- **C1: within, between and contextual decomposition.**
  - A weighted regression on the area-centred exposure and the area mean, with area means recomputed per weight
    column.
  - Linear model; the risk-difference scale for 0/1 outcomes.
- **C1l:** the same as C1 with a logit link.
- **C2: the ecologic regression** of area mean outcomes on area mean exposure.
  - The ecologic gap is C2 minus the C1 within slope.
- **SEs:** SDR replicate refits.

## Design (32 cells × 1,000 draws)

- **Sampling:** Round 32's design. Areas are J ∈ {30, 150} bins of geography; records 5,000 or 30,000.
- **Effects:**
  - within slope .5;
  - contextual effect 0 or .25;
  - area confounding off or on (.3 × area mean).
- **Outcomes:** continuous, or binary (logistic).
- **Targets:** the same estimators on a 300,000-household reference population.

## Pass rules (per family: C1; C2 and gap; C1l)

- 90% coverage ≥ .86 for every quantity in every applicable cell.
- **Gate:** a family that fails only at 5,000 records is validated from 30,000.

Seeds: `[20282701, …]` for reference populations; `[20282711 + cell, draw]` for draws.

## Engine (only what passes)

- `pums_regression(..., ecologic_check="<exposure>")` (or a new tool, if the parameters do not fit) reports the
  within, between and contextual associations and the ecologic gap.
- An agent rule routes individual-level claims from area results to this check.
- A `pums_tests` recipe section.

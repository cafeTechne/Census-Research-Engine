# Treatment effects, instrumental variables and mediation with ACS data

Causal estimates need assumptions the data cannot check. Write them down first; register the design
for any confirmatory claim (`get_recipe("preregistered")`).

1. **Treatment effect** of a binary area exposure (e.g. a state policy, coded 0/1):
   `estimate_effect(input_path, "treatment", outcome, treatment=..., confounders=[...])` (AIPW, doubly
   robust). Assumes no unmeasured confounding and overlap. Validated with precisely measured
   confounders; ACS confounders with large MOEs can leave residual confounding (flagged in notes).
2. **Error-prone covariate**: if you have a second, independent measurement of the same quantity
   (a non-overlapping ACS release, another survey), use it as an instrument:
   `estimate_effect(..., "iv", outcome, x=..., instrument=...)`. 2SLS removes the attenuation that
   biases ordinary regression toward zero (validated). A weak instrument (correlation < 0.3) is flagged.
3. **Mediation** (x -> mediator -> outcome): `estimate_effect(..., "mediation", outcome, x=...,
   mediator=...)`, percentile bootstrap by default. Validated only when the mediator is measured
   without sampling error; an ACS mediator attenuates the indirect effect (exploratory).
4. Synthetic worked example: with x observed at reliability 0.7, OLS gave slope 0.35 for a true 0.5,
   and 2SLS with a second measurement gave 0.50 (Round 41 validation, `docs/audits/causal_validation.md`).
5. The difference-in-differences tool remains the default for policy timing.

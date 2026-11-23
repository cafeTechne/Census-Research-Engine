# Treatment effects, instrumental variables and mediation with ACS data

Causal estimates need assumptions the data cannot check. Write them down first; register the design
for any confirmatory claim (`get_recipe("preregistered")`).

**State the causal question first (Round 89; Hernán and Robins, *What If*, chapters 3 and 22).** Describe the
target trial you would run: `causal_question={"eligibility", "intervention", "comparator", "time_zero", "outcome",
"follow_up", "contrast": "average_effect"|"effect_in_treated", "target": "super_population"|"these_areas"}`. Area
characteristics such as poverty or education are not interventions: add `"versions"` naming the intervention that
would change them. Without a causal question, results are labelled associational.

**Draw the diagram, then adjust (chapters 6-8, 18).** `dag={"edges": ["L -> A", "L -> Y", "A -> Y"], "outcome":
"Y"}` (treatment defaults to the tool's treatment; unmeasured nodes are named `U`, `U1`, ...). The tool checks the
backdoor criterion for your confounders and lists minimal sufficient sets. Never adjust for a mediator, another
descendant of treatment, or a collider (M-bias). An instrument-like variable adds nothing and can amplify bias. The
10% change-in-estimate label from `stratified_analysis` is associational: the diagram decides. Manifests take the same
`causal_question` and `dag` blocks, and a formula that fails the check is refused.

**Check positivity (Round 90; chapters 3.3, 12-15).** `kind="treatment"` always returns `positivity`: propensity
quantiles by group, the share outside [.05, .95], the overlap coefficient, standardized mean differences and the
effective n. When 5% or more of propensities are extreme, IP weighting under-covered in validation (.807-.863):
use `weights="overlap"` (estimates the effect in the overlap population; say so), `weights="truncated"` or
`method="ra"` (g-formula), all validated, or restrict to areas with overlap. Weighted results add the g-formula and
flag disagreement (a sign of model misspecification).

1. **Treatment effect** of a binary area exposure (e.g. a state policy, coded 0/1):
   `estimate_effect(input_path, "treatment", outcome, treatment=..., confounders=[...])` (AIPW, doubly
   robust). Assumes no unmeasured confounding and overlap. Validated with precisely measured
   confounders. ACS confounders leave residual confounding (Round 47: coverage .77-.87): pass
   `calibrate=True` with their `_se` or `_moe` columns (validated, .889-.905).
2. **Error-prone covariate**: if you have a second, independent measurement of the same quantity
   (a non-overlapping ACS release, another survey), use it as an instrument:
   `estimate_effect(..., "iv", outcome, x=..., instrument=...)`. 2SLS removes the attenuation that
   biases ordinary regression toward zero (validated). The tool also reports an Anderson-Rubin
   interval, valid however weak the instrument (Round 47). When the first-stage F is below 10, report
   the AR interval: the 2SLS estimate is unstable there, and the AR interval may be unbounded.
3. **Mediation** (x -> mediator -> outcome): `estimate_effect(..., "mediation", outcome, x=...,
   mediator=...)`, percentile bootstrap by default. An ACS mediator attenuates the indirect effect:
   pass `calibrate=True` with its `_se` column (no controls; validated in Round 47, .883-.898).
4. Synthetic worked example: with x observed at reliability 0.7, OLS gave slope 0.35 for a true 0.5,
   and 2SLS with a second measurement gave 0.50 (Round 41 validation, `docs/audits/causal_validation.md`).
5. The difference-in-differences tool remains the default for policy timing.

**Matching (Round 99; Cunningham, *Mixtape*).** `estimate_effect(..., "matching", outcome, treatment=...,
confounders=[...], method=...)`:
- `"nn"`: nearest-neighbour matching with 4 matches, bias correction and the Abadie–Imbens variance. The ATE is
  validated (.861–.903). The ATT under-covered with 145 areas and limited overlap.
- `"cem"`: coarsened exact matching at quintiles, giving the ATT among matched treated areas (validated, conservative).
  Report the share matched, because unmatched treated areas change the estimand.
- `"ps"`: propensity-score caliper matching with a bootstrap. It covered conservatively in this design, contrary to
  Abadie and Imbens (2008); prefer `"nn"`.

Results include balance before matching. Check positivity first.
**Regression discontinuity (Round 98; Cunningham, *Mixtape*).** When eligibility switches at a cutoff of a running
variable (Medicare at 65, a program threshold), compare units just above and just below:
`regression_discontinuity(input_path, outcome, running, cutoff, treatment=None, weight=..., replicate_prefix=...)`.
- **Estimate:** the robust bias-corrected jump (local quadratic at the Imbens–Kalyanaraman bandwidth). Fuzzy designs
  give outcome jump / treatment jump.
- **Validated:** PUMS ages with survey weights and replicate weights (`weight="PWGTP", replicate_prefix="PWGTP"`).
  Discrete running variables use a bandwidth of at least 4.
- **Exploratory:** continuous running variables, which under-covered with strong curvature near the cutoff, and the
  density (manipulation) test.
- **Never cluster by age value.** In validation that covered .69–.71.
- **Always report** covariate jumps and placebo cutoffs. A causal reading needs nothing else to change at the cutoff.


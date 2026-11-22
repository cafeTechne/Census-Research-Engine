# Confounding and effect modification (stratified analysis)

Profile: full (`stratified_analysis`); manifests declare roles in a `covariables` block.

From *Foundations of Epidemiology* chapters 7–8 (`docs/literature/foundations_of_epidemiology.md`).

1. **Before looking at the data, list covariables and their roles.** A confounder is associated with the exposure,
   plausibly causes the outcome and is not on the causal pathway. A **mediator** (on the pathway) is not adjusted
   for. An **effect modifier** changes the association and is reported by stratum. If the causal direction between
   a covariable and the outcome is unclear, mark it `direction_uncertain` and run the analysis both ways (Round 86).
   Manifests: `"covariables": {"age_band": "confounder", "insured": "mediator", "sex": "effect_modifier"}`;
   validation refuses a mediator in a formula and an effect modifier entered only as a main term.
2. **Stratify.** `stratified_analysis` gives the crude measure, each stratum's measure and the Mantel–Haenszel
   pooled (adjusted) RR, OR and RD:
   - counts: `stratified_analysis(input_path="strata.csv", stratum="age_band", cases_exposed=..., total_exposed=...,
     cases_unexposed=..., total_unexposed=...)` (`person_time=True` gives the MH rate ratio);
   - PUMS: `stratified_analysis(state="26", year=2023, exposure="DIS == 1", outcome="HICOV == 2", strata="SEX",
     where="AGEP >= 19 and AGEP <= 64")`.
3. **Decide (book Table 8-5).** Stratum measures that differ (homogeneity p ≤ .10) with the crude between them: an
   effect modifier, report each stratum. Similar stratum measures with the adjusted measure more than 10% from the
   crude: a confounder, report the adjusted measure. Otherwise report the crude. The tool's `classification` label
   is descriptive, not a test.
4. **Validated** (`docs/audits/stratified_validation.md`): MH RR, OR, RD and IRR for counts down to 5 expected cases
   per stratum and arm; MH on PUMS with replicate weights from 300 records per stratum; the Breslow–Day–Tarone test
   for homogeneous ORs. **Exploratory:** the Woolf-type RR homogeneity test (too conservative with sparse strata)
   and the PUMS replicate homogeneity test (rejects too often with four strata).
5. **Additive interaction.** For two binary factors, `interaction="<second condition>"` (PUMS) adds RERI, the
   attributable proportion and the synergy index (validated); report them with the ratio measures, because public
   health impact is additive.
6. **Residual confounding.** Coarse strata (two age bands) leave confounding inside each stratum; use finer strata
   or regression with the variable kept continuous, and say so.

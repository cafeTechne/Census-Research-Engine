# Foundations of Epidemiology: guidance mapped to engine work

Source: Bovbjerg ML. *Foundations of Epidemiology*. Oregon State University; 2020 (Pressbooks print of 2026-03-26;
CC BY-NC 4.0). The owner's copy is in `literature_pdfs/` (gitignored). Summary and mapping by the maintainer agent,
2026-11-22, to draft Rounds 82–87 (backlog N59–N64). Author self-review, not independent.

## What the book asks of an analysis, and where the engine stands

| Chapter | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 1 | Describe distribution by person, place and time; define the population by complete inclusion/exclusion criteria; population-level results say nothing about individuals | Area estimates with MOEs; manifests declare geography and exclusions | 82: ecologic-level label and universe statement in every result |
| 2 | Distinguish counts, prevalence (existing cases; resource planning) and incidence (new cases over person-time; causes). Compare rates only in the same units and time frame. Prevalence ≈ incidence × duration | ACS, PLACES and CHR measures are prevalences; WONDER rates are incidence rates per person-year; outputs do not say which | 82: `measure_type` on every outcome; unit and period statements |
| 3 | An epidemic is cases above the expected level; survey surveillance gives prevalent cases only | SMR (observed vs expected), scan | 82: prevalence caveat for survey sources |
| 4 | Prevalence designs give odds ratios, incidence designs risk/rate ratios; for common outcomes the OR overstates the RR; always keep absolute risks in view (risk difference, attributable risk, NNT); standard interpretation sentences ("times as high … over x years") | Binomial models report ORs; PUMS `two_by_two` gives OR, RR and difference | 84: marginal (standardized) risk ratios and differences, prevalence ratios, attributable fractions; 82: interpretation templates |
| 5 | p-values describe sampling (a full-population count has no sampling error but has stochastic variation); never "accept the null"; power; 95% CIs are the field's convention | 90% default (Census); TOST equivalence (Round 38); detectable-difference tool | 82: 95% reporting option for health audiences; "no evidence of a difference" wording |
| 6 | Bias is systematic and not fixed by statistics; selection bias, differential vs nondifferential misclassification; sensitivity (bias) analysis; >5% missing data unaddressed is a warning | Suppression and replicate gaps are recorded; no item-nonresponse information | 82: ACS item-allocation rates per variable; 86: quantitative bias analysis |
| 7 | Confounder criteria (associated with exposure, causes the outcome, not on the pathway); stratify and pool (Mantel–Haenszel) or regress; report crude and adjusted, a >10% change marks confounding; residual confounding from coarse categories; run both ways when the causal direction is unclear | Regression adjustment; no stratified pooling; no crude-vs-adjusted report | 83: Mantel–Haenszel with crude/adjusted comparison; 86: both-directions sensitivity |
| 8 | Effect modification is a finding to report by stratum, not adjust away; stratum measures differ and the crude lies between them | Interaction terms in formulas only | 83: homogeneity tests, stratum reporting, additive interaction (RERI) |
| 9 | Ecologic studies compare groups and invite the ecologic fallacy; cross-sectional designs lack temporality; both are for hypothesis generation; meta-analysis needs heterogeneity and publication-bias checks | Most engine analyses are ecologic and cross-sectional; `combine_estimates` pools | 82: design labels and limitation text; 87: ecologic-versus-individual contrast on PUMS |
| 10 | Rule out chance, bias and confounding before causal thinking; Hill's considerations (temporality, dose-response, consistency, plausibility) are aids, not criteria; attributable fractions over causes sum past 100% | Replications in OH/PA give consistency | 84: dose-response trend across ordered exposure levels; 82: evidence checklist in bundles |
| 11 | Screening: sensitivity and specificity are fixed, PPV and NPV depend on prevalence | Areas are designated "high need" by thresholds on noisy ACS estimates with no accuracy statement | 85: designation accuracy (probability above threshold, expected Sn/Sp/PPV/NPV) |
| App. 1 | A study reports its sample ("Table 1"), exposure/outcome operationalization, covariable roles, subgroup and sensitivity analyses, and frank limitations | Results bundles hold tables, methods text and deviations | 82: Table 1 and a generated limitations section |

## Principles carried into the plans

- Results from area data describe areas (ecologic), and cross-sectional ACS measures are prevalences; generated
  text uses association language and states both limits.
- Absolute and relative measures are reported together; odds ratios for common outcomes are accompanied by
  standardized risk ratios.
- Covariables are declared with a role (confounder, effect modifier, mediator) before analysis; mediators are not
  adjusted for, and effect modifiers are reported by stratum.
- Every method still ships only after a pre-set simulation passes (engine rule); failed methods stay exploratory.

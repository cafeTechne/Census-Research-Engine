# Changelog

All notable changes, by development round. Versions follow `census.__version__`;
each tagged release (`v<version>`) is archived on Zenodo with its own DOI (see
[Releasing](#releasing)). Plans and acceptance criteria for each round are in
`PLAN_ROUND_<n>.md`.

## 0.93.0 (Round 97): spatial block cross-validation and MAUP sensitivity

- **`spatial_model(kind="cv")`** (`census/model_assessment.py`; frozen core `census/model_assessment_core.py`; N74;
  Moraga 2023 chapters 11 and 16): spatial-block and random 5-fold cross-validation with MAE, RMSE, coverage and CRPS.
- **`spatial_model(kind="maup")`:** slopes over random contiguous zonings.
- **Validation** (`docs/audits/model_assessment_validation.md`, criterion tag `criterion-r97`): **failed**, so block
  CV is exploratory. With spatial correlation, block CV under-estimated new-region RMSE by 19–23% (random CV by
  33–43%); both were exact without correlation. MAUP is reported: zone slopes ranged from −0.2 to 1.4 times the
  tract slope.
- **Example** (`docs/audits/r97_model_assessment_example.md`, exploratory): Wayne County poverty. Random folds flatter
  the neighbour model (RMSE 10.2 against 12.1). Aggregating to zones of about 10 tracts raises the
  poverty–unemployment slope from 1.13 to about 1.9.
- **Recipe** `spatial_patterns` section; protocol rule; sources (Roberts et al. 2017; Openshaw 1984).

## 0.92.0 (Round 96): spatial disease mapping with BYM2

- **BYM2 Poisson disease mapping** (`census/disease_mapping.py`; frozen core `census/disease_mapping_core.py`; N73;
  Moraga 2023 chapters 9–10; Riebler et al. 2016), as `spatial_model(kind="disease_map")`:
  - a Laplace approximation with no INLA dependency;
  - hyperparameters from the grid maximum (B1) or integrated over the grid (B2);
  - relative risks, 90% intervals and exceedance probabilities;
  - suppressed counts predicted from neighbours;
  - bridge edges join separate parts of the contiguity graph.
- **Validation** (`docs/audits/disease_mapping_validation.md`, criterion tag `criterion-r96`):
  - exceedance probabilities calibrated in every cell;
  - intervals covered .84–.90 in 15 of 16 cells but .79–.80 with median expected counts of 5 over 83 counties, so
    the rule failed and intervals are exploratory;
  - BYM2 beat Poisson–gamma EB and SMRs on error everywhere.
- **Example** (`docs/audits/r96_disease_mapping_example.md`, exploratory): drug-overdose relative risks in Michigan
  counties, 2018–2022. Genesee is highest at 1.92, then Wayne at 1.78. Six counties have P(RR > 1.2) ≥ .8.
- **Recipe** `small_area` section; protocol rule; sources (Besag, York and Mollié 1991; Riebler et al. 2016; Moraga
  2023).

## 0.91.0 (Round 95): years of potential life lost and aberration detection

- **YPLL** (`census/surveillance.py`; frozen core `census/surveillance_core.py`; N72; CDC SS1000 lessons 3–5):
  - CDC grouped-data YPLL to 65 or 75, crude and age-adjusted rates with Fay–Feuer intervals;
  - `ypll_from_wonder` for national age-group exports, which reports bounds when cells are suppressed;
  - `ypll_table` for area tables, with bounds only for suppressed bands.
- **Aberration flags:** historical limits and EARS C2 for the latest year of an annual series, as
  `joinpoint(aberration=...)` and `census.surveillance.aberration`; plus `deviation_chart`.
- **Validation** (`docs/audits/surveillance_validation.md`, criterion tag `criterion-r95`): all pass.
  - YPLL interval coverage .888–.963.
  - Null false-alarm rates .005 (historical limits) and .016 (EARS C2).
  - Under a 3% trend false alarms reach .10 and .24 (reported).
- **Example** (`docs/audits/r95_surveillance_example.md`, exploratory):
  - US age-adjusted YPLL-75 rose 14% from 2013–2017 to 2018–2022 (overdose +56%, unintentional injury +33%);
  - 2023 state uninsured rates: 10 low flags, 0 high.
- **Recipe** `external_health_outcome` section; protocol rule; sources CDC SS1000 and Hutwagner et al. 2003.

## 0.90.0 (Round 94): WHO health inequality monitoring

- **WHO measures** (`census/inequality_monitoring.py`; frozen core `census/inequality_monitoring_core.py`; N71; WHO
  2013) via `disparity_measures(who_measures=True, reference="best" | group, compare_years=[y1, y2])`:
  - population attributable risk against the best or declared group, the SII, and mean differences from the
    overall mean and from the reference;
  - the change between non-overlapping releases;
  - library `double_disaggregation` and `priority_quadrants`.
- **Validation** (`docs/audits/inequality_monitoring_validation.md`, criterion tag `criterion-r94`):
  - pass: PAR with a declared or data-selected best group (.884–), SII (.882–) and changes between releases (.879–);
  - **fail**: mean differences (down to .39 when groups are close), which are exploratory.
- **Example** (`docs/audits/r94_inequality_monitoring_example.md`, exploratory): family poverty by race/ethnicity in
  Michigan counties, 2020–2024. Wayne County has the largest PAR, 6.7 points. Age-group poverty inequality fell in
  39 of 80 counties between 2015–2019 and 2020–2024.
- **Recipe** `health_inequality` section; protocol rule; WHO 2013 registered as a guidance source.

## 0.89.0 (Round 93): GWR, neighbourhood types, regions and diversity

- **New full-profile tool `spatial_model`** (79 tools; `census/spatial_models.py`, frozen core
  `census/spatial_models_core.py`; N69; Walker, *Analyzing US Census Data*, chapter 8):
  - `kind="gwr"`: geographically weighted regression, AICc bandwidth, robust local intervals and a permutation test
    of non-stationarity;
  - `"classify"`: k-means neighbourhood types on principal components;
  - `"regionalize"`: SKATER on queen contiguity.

  Classification results carry per-area stability under sampling error.
- **Entropy diversity index** in the library (`diversity_index`).
- **Validation** (`docs/audits/spatial_models_validation.md`, criterion tag `criterion-r93`), Wayne County tracts:
  - GWR **failed**: local coverage .71 when slopes vary, and test size .12–.17. It is exploratory.
  - Diversity **failed** narrowly: .847 at 50 respondents per tract, .883 at 200.
  - Stability is informative: unstable areas were misclassified 39–50% of the time, stable ones 3–16%.
- **Example** (`docs/audits/r93_spatial_models_example.md`, exploratory): Wayne County poverty, unemployment and
  education.
- **Recipe** `spatial_patterns` section; README question row; protocol rule; sources Brunsdon et al. 1996 and
  Assunção et al. 2006.

## 0.88.0 (Round 92): Population Estimates, LEHD LODES and ACS migration flows

- **`census/demographic_sources.py`** (N68; Walker, *Analyzing US Census Data*, chapters 4 and 11):
  - `pep_totals` and `pep_age_sex`: Census Population Estimates, vintages 2019 and 2024. July 1 county and state
    populations, and county age groups by sex. Values carry their vintage; there is no MOE.
  - `lodes`: LODES8 WAC, RAC and OD files aggregated to block, tract or county. Noise-infused; no MOE.
  - `migration_flows` and `net_migration`: ACS county-to-county flows 2010–2020 with MOEs. Later releases have state
    partners only and are refused.
- **Context sources** `pep`, `lodes` and `acs_flows` for `build_analysis_frame(context=...)` and manifests. Flows add
  `<name>_moe`; LODES supports `per`/`per_column`.
- **Checks** (`docs/audits/r92_source_checks.md`): state equals the sum of counties (PEP); tract sums equal county
  totals (LODES); in − out = net (flows).
- **Recipe** `context_covariates`; README; protocol rule; data sources registered for attribution.

## 0.87.0 (Round 91): marginal structural models for annual policy panels

- **IP-weighted marginal structural models** (`census/msm.py`; frozen core `census/msm_core.py`; N67; Hernán and
  Robins chapters 19–21): `difference_in_differences(design="msm", first_treated=..., time_varying_confounders=[...])`.
  - Stabilized or truncated time-varying weights; effects of the 1st, 2nd and 3rd treated year versus never; cluster
    bootstrap over units.
  - Time zero is the first period; "start and stay on" strategies only.
- **Validation** (`docs/audits/msm_validation.md`, criterion tag `criterion-r91`): **failed**. Coverage was .805–.881
  (stabilized) and .799–.885 (truncated) with 51 units, and the method is exploratory. Under feedback, regression on
  the current confounder covered .00–.11 (bias up to −1.6), and no adjustment .05–.68.
- **Example** (`docs/audits/r91_msm_example.md`, exploratory): Medicaid expansion and the state uninsured rate with
  time-varying unemployment: −2.7, −3.2 and −3.6 points in expansion years 1–3.
- **Recipe** `policy_change` step; protocol rule; sources Robins, Hernán and Brumback 2000 and Cole and Hernán 2008.

## 0.86.0 (Round 90): positivity diagnostics and weighting options

- **Positivity** (`census/positivity.py`; frozen core `census/positivity_core.py`; N66; Hernán and Robins chapters
  3.3, 12–15). `estimate_effect(kind="treatment")` always returns `positivity`:
  - propensity quantiles by group and the share outside [.05, .95];
  - the overlap coefficient;
  - standardized mean differences before and after weighting;
  - the maximum weight and the effective n.
- **`weights=`**: `"stabilized"`, `"truncated"` or `"overlap"`. Weighted results also give the g-formula and an
  IPW-versus-g-formula agreement flag.
- **Validation** (`docs/audits/positivity_validation.md`, criterion tag `criterion-r90`):
  - passed: truncated weights (.864–.905), overlap weights for the overlap-population effect (.877–.906), the
    g-formula (.881–.907) and the flag (size ≤ .061);
  - **failed**: stabilized and plain IPW once 5% or more of propensities are extreme (.807–.863). With limited
    overlap, `method="ipw"` is now exploratory, and a note recommends overlap weights or `method="ra"`.
- **Example** (`docs/audits/r90_positivity_example.md`, exploratory): metro status and county uninsured rates in
  MI/NY/OH/PA. 7.3% of propensities are extreme. IPW and AIPW give −2.7 points with wide intervals; the g-formula,
  truncated and overlap weights give −1.5 to −1.7.
- **Recipe** `causal` section; protocol rule; sources Li, Morgan and Zaslavsky 2018 and Lunceford and Davidian 2004.

## 0.85.0 (Round 89): causal question specification

- **Target trial and causal diagram** (`census/causal_spec.py`; N65; Hernán and Robins, *What If*, chapters 3, 6–8,
  18, 22).
  - A `causal_question` block holds the target-trial protocol: eligibility, intervention, comparator, time zero,
    outcome, follow-up, contrast, and target (super-population or these areas).
  - A `dag` block holds the causal diagram; unmeasured nodes are named `U...`.
  - The engine checks d-separation by the moralized ancestral graph and the backdoor criterion, and enumerates
    minimal sufficient adjustment sets.
  - It flags adjusted mediators, treatment descendants, colliders it opens (M-bias), instrument-like variables and
    unmeasured nodes, with the open paths named.
- **Manifests:**
  - a formula that fails the check is a validation error (exploratory manifests get the findings in methods text);
  - a "Causal question" methods section appears only when the blocks are present.
- **Tools:**
  - `estimate_effect(causal_question=..., dag=...)` and `difference_in_differences(causal_question=...)` return a
    `causal_assessment`;
  - without a causal question, results are labelled associational;
  - social exposures need named intervention versions.
- **Round 83's classification** is marked "associational (10% rule)" (`classification_basis`).
- **Recipe** `causal` sections; protocol rule; sources Pearl 2009 and Lauritzen et al. 1990.
- **Tests** reproduce the book's Figures 7.1–7.4 and 18.1–18.4. d-separation and the backdoor verdict are
  cross-checked against path enumeration on random DAGs.

## 0.84.0 (Round 88): method attribution

- **Source registry** (`census/references.py`; N70; owner request). It covers the method papers, the three guidance
  texts (Bovbjerg; Hernán and Robins; Walker), data products, software and the engine's validation audits. Each
  tool's sources carry a role (`method`, `guidance`, `data`, `software`, `validation`). Manifest citation text is
  reused unchanged; module reference lists (small-area, multilevel, DiD) are included verbatim.
- **`method_sources` on successful method-tool results** (MCP and CLI `tool`), added at the shared tool boundary.
  Discovery and extraction tools omit it.
- **Results bundles:**
  - `methods.md` ends with a **Sources** section;
  - new `references.md` and `references.bib`.
- **CLI:** `python -m census cite`.
- **Docs:** `docs/citing.md`; README "Citing methods"; CITATION.cff `references` lists the guidance texts.
- **Coverage:** a test requires every tool to have sources. Unverified entries are flagged "[details to verify]".

## 0.83.0 (Round 87): ecologic versus individual-level associations

- **Ecologic check** (`census/ecologic.py`; frozen core `census/ecologic_core.py`; N64; *Foundations of Epidemiology*
  chapter 9): on PUMS, the within-PUMA (individual), between-PUMA and contextual associations of an exposure, the
  area-level (ecologic) slope and the ecologic gap, with SDR replicate SEs; `pums_regression(ecologic_check=...)`.
- **Validation** (`docs/audits/ecologic_validation.md`): the logit decomposition passes (.871–); the identity-scale
  decomposition and the ecologic gap fail with 150 small areas (.62–.86) and are exploratory.
- **Recipe** `pums_tests` section and a protocol rule against applying area results to individuals.
- **Example** (`docs/audits/r87_ecologic_example.md`, exploratory): MI and OH disability and income-to-poverty.

## 0.82.0 (Round 86): quantitative bias analysis

- **E-values** (VanderWeele and Ding 2017; `census/bias_analysis.py`, frozen core `census/bias_analysis_core.py`; N63;
  *Foundations of Epidemiology* chapters 6–7) for risk, rate, prevalence and odds ratios and standardized
  differences; added to `stratified_analysis` and the marginal measures.
- **Misclassification bias analysis** of 2 x 2 tables: simple correction (outcome or exposure, differential or not)
  and a probabilistic analysis with beta priors. Validation (`docs/audits/bias_analysis_validation.md`): the simple
  correction is unbiased; the probabilistic interval **fails** (.76–.83 to about 1.00) and is exploratory.
- **Tool `bias_analysis`** (full profile; 78 tools); `reporting` recipe section; both-directions helper for
  covariables of uncertain causal direction.
- **Example** (`docs/audits/r86_bias_example.md`, exploratory).

## 0.81.0 (Round 85): area designations as screening tests

- **Designation accuracy** (`census/designation.py`; frozen core `census/designation_core.py`; N62; *Foundations of
  Epidemiology* chapter 11): each area's probability of truly exceeding a threshold (Fay–Herriot posterior on the
  arcsine scale, or the direct flat-prior probability) and the expected sensitivity, specificity, PPV and NPV of
  four designation rules.
- **Validation** (`docs/audits/designation_validation.md`, criterion `61fa47a`; MI/NY tracts and counties, 10–50%
  truly qualifying): the Fay–Herriot probability is calibrated (within .031); the direct probability (up to .17
  off) and the rule-accuracy criterion (PPV predictive interval .54–.85 on tracts; expected values within about .01)
  fail and are exploratory.
- **Tool `designation_accuracy`** (full profile; 77 tools); `small_area` recipe section "Designating areas".
- **Example** (`docs/audits/r85_designation_example.md`, exploratory): Michigan tracts at 20% poverty.

## 0.80.0 (Round 84): marginal risk ratios, prevalence ratios, attributable fractions, dose-response

- **Marginal (standardized) measures** (`census/epi_measures.py`; frozen core `census/epi_measures_core.py`; N61;
  *Foundations of Epidemiology* chapters 4 and 10): g-computation risk ratios and differences and attributable
  fractions for area binomial models (HC3 delta SEs) and PUMS logit models (SDR SEs); modified-Poisson prevalence
  ratios; dose-response trend tests over ordered exposure levels.
- **Validation** (`docs/audits/epi_measures_validation.md`, criterion `c5f6266`): every candidate passes
  (coverage .862–.898; trend size .083–.129).
- **Options**: `fit_model(model="binomial", marginal=..., marginal_values=..., dose_levels=...)` and
  `pums_regression(model="logit", marginal=...)`; a note pairs ORs with marginal RRs when the outcome is common.
  No new tool.
- **Example** (`docs/audits/r84_marginal_example.md`, exploratory): MI/NY county disability and poverty.

## 0.79.0 (Round 83): stratified analysis, Mantel–Haenszel and effect modification

- **Stratified analysis** (`census/stratified.py`; frozen core `census/stratified_core.py`; N60; *Foundations of
  Epidemiology* chapters 7–8): crude, stratum-specific and Mantel–Haenszel pooled RR, OR, RD (Greenland–Robins,
  RBG variances) and the MH rate ratio for counts; the same on PUMS with SDR replicate weights; Breslow–Day–Tarone
  and Woolf-type homogeneity; RERI, AP and S for additive interaction; a descriptive confounder / effect-modifier
  label (book Table 8-5, 10% rule).
- **Validation** (`docs/audits/stratified_validation.md`, criterion `b358799`): MH measures pass for counts
  (.877–.906) and PUMS (.881–.909); RERI passes (delta, bootstrap, SDR); Breslow–Day passes (size .102–.114); Woolf
  (size .032–.113) and the PUMS replicate Wald test (.099–.151) fail and are exploratory.
- **Tool `stratified_analysis`** (full profile; 76 tools); **recipe `confounding`** (26 recipes); **manifest
  `covariables`** roles: mediators are refused in formulas and effect modifiers must enter through interactions.
- **Example** (`docs/audits/r83_stratified_example.md`, exploratory): Michigan PUMS disability and uninsurance by age.

## 0.78.0 (Round 82): epidemiologic reporting conventions

Drawn from *Foundations of Epidemiology* (Bovbjerg 2020; `docs/literature/foundations_of_epidemiology.md`); no new
statistics (N59).

- **Measure types** (`census/epi_reporting.py`): every manifest outcome is typed as a count, prevalence, incidence
  proportion, incidence rate, level, ratio, index or expected count; methods text states each, and external
  variables may declare `measure_type`.
- **Design labels**: manifest methods text gains "Study design and measures" and a generated "Limitations" section
  (ecologic fallacy; cross-sectional design without temporal order; prevalence caveat; undeclared measure types;
  run deviations). Run info records `design` and `measure_types`.
- **Interpretation templates** (`interpret_ratio`, `interpret_difference`): "times as high … compared with …", and
  "no evidence of a difference" when an interval includes the null; `rescale_interval` and
  `make_table(kind="comparison", confidence_level=0.95)` for health journals.
- **Item nonresponse**: `reliability_profile(allocation_tables=[...], year=...)` reports the share of answers the
  Census Bureau allocated (imputed) per area from the B99 tables, flagged above 5%. Checks
  (`docs/audits/r82_reporting_checks.md`): allocated and not-allocated lines sum to the published totals in all 145
  MI/NY counties; median allocation 20.5% (health insurance), 12.1% (disability), 37.4% (family poverty income).
- **Table 1**: `make_table(kind="table1", exposure=..., variables=[...], population=...)`.
- **Results bundles**: `make_results_bundle(design="area" | "individual" | "none")` adds design limitations.
- **Rules**: association-language rule in the protocol, MCP text (core rule 2) and the `reporting` recipe.
- **Goldens**: intended changes only (methods text; two new run-info keys; their file hashes), documented field by
  field in `docs/audits/round82_compatibility.md`.

## 0.77.0 (Round 81): spatial scan statistic for county counts

- **Kulldorff Poisson spatial scan** (`census/scan.py`; frozen core `census/scan_core.py`; N58): circular windows
  of nearest counties up to a share of the expected total, high-rate LLR, Monte Carlo p-values (999 multinomial data
  sets conditional on the total), non-overlapping secondary clusters and a Gumbel comparison.
- **Validation** (`docs/audits/scan_validation.md`, criterion `b6b69d0`; MI+NY and OH+PA counties, 5–100 expected per
  county): size .099–.116 at α .10 in every null cell. Reported: power, sensitivity and PPV of planted clusters; with
  5% ACS-like denominator error the size inflated to .15–.53, so noisy denominators are exploratory.
- **Tool `spatial_scan`** (full profile; 75 tools). Refuses missing (suppressed) counts unless excluded by a stated
  rule; never imputes counts. Descriptive unless the window and α are pre-specified.
- **Recipe** `spatial_patterns` section; protocol and MCP rule text.
- **Example** (`docs/audits/r81_scan_example.md`, exploratory): MI/NY low-birth-weight births (CHR&R 2025), primary
  cluster Wayne County (RR 1.37, p .001).

## 0.76.0 (Round 80): Fay–Herriot for proportions and across releases

- **Arcsine Fay–Herriot** (`census/sae_extensions.py`; frozen core `census/sae_extensions_core.py`; N57): direct
  proportions transformed with the arcsine square root, sampling variance 1/(4 n_eff), bias-corrected back-transform
  and a 200-fit parametric-bootstrap MSE. `small_area_estimates(transform="arcsine", n_col=...)`.
- **Rao–Yu temporal Fay–Herriot**: area plus AR(1) area-time effects across 2–3 non-overlapping releases, latest
  release reported, bootstrap MSE. `small_area_estimates(temporal=True, release_column="Year")`; overlapping releases
  refused.
- **Validation** (`docs/audits/sae_extensions_validation.md`, criterion `251dc9d`; real S2701 sampling variances for
  MI/NY counties and tracts; 500 draws): arcsine per-area coverage .898–.904 (worst decile ≥ .880; relative bias
  ≤ .078 below p = .10); Rao–Yu .897–.898, MSE gain 3–24%.
- **Recipe** `small_area` sections; protocol and MCP rule text. No new tool, no manifest change.
- **Example** (`docs/audits/r80_sae_example.md`, exploratory): Michigan tract and county uninsured rates.

## 0.75.0 (Round 79): Oaxaca–Blinder and Fairlie decompositions on PUMS

- **Decompositions** (`census/decomposition.py`; frozen core `census/decomposition_core.py`; N56): twofold
  Oaxaca–Blinder with the pooled reference (Neumark; Jann), detailed contributions with Yun-normalised categoricals,
  threefold reported; Fairlie (logit) with rank-matched pairs over 100 random orderings. Intervals from the 80 SDR
  replicate weights.
- **Validation** (`docs/audits/decomposition_validation.md`, criterion `9e52bb4`; 12 cells, 1,000 draws):
  Oaxaca–Blinder totals pass from 300 records in the smaller group (.862–.894); detailed contributions and every
  Fairlie quantity pass from 1,000 (they under-covered at 300, .802–.853).
- **Tool `decompose_gap`** (full profile; 74 tools); `pums_tests` recipe section "Decomposing a gap" with the
  interpretation rule (explained = composition, not causation); protocol and MCP rule text.
- **Example** (`docs/audits/r79_decomposition_example.md`, exploratory): Michigan uninsured gap, Black vs White
  non-Hispanic adults 19–64, PUMS 2019–2023.

## 0.74.0 (Round 78): staggered-adoption DiD and synthetic control

- **Staggered adoption** (`census/staggered.py`; frozen core `census/policy_core.py`; N55): Sun–Abraham (2021)
  interaction-weighted event study and Callaway–Sant'Anna (2021) group-time ATTs with a multiplier bootstrap, overall
  ATT and pre-trend check. `difference_in_differences(design="staggered", first_treated=...)` on annual panels
  (ACS 1-year with 2020 refused, or another annual source); five-year releases refused.
- **Validation** (`docs/audits/policy_validation.md`, criterion `baf934b`; 51 units, 12/18 periods):
  - Sun–Abraham passes (.881–.899) and is the default;
  - Callaway–Sant'Anna passes only with the ACS sampling variance added (.882–.906; bootstrap alone .848–.868);
  - uniform bands (.76–.81) and synthetic control (placebo size .12–.19; conformal .73–.95) fail.
- **Synthetic control** is library-only and exploratory (`census.staggered.synthetic_control`).
- **Recipe** `policy_change` step 3 (route choice); protocol and MCP rule text.
- **Example** (`docs/audits/r78_medicaid_example.md`, exploratory): Medicaid expansion and the all-ages state
  uninsured rate, overall ATT −1.23 points (−2.18 to −0.27).

## 0.73.0 (Round 77): joinpoint regression and age-adjusted rate ratios

- **Joinpoint regression** (`census/joinpoint.py`; frozen core `census/joinpoint_core.py`; N54): log-linear segments by
  weighted least squares with grid-searched joinpoints (Joinpoint spacing defaults), the number of joinpoints chosen
  by Kim et al. (2000) sequential permutation tests, per-segment APC and whole-period AAPC.
- **Ratio of two directly age-adjusted rates** with the Tiwari et al. (2006) interval (and a log-delta comparison).
- **Validation** (`docs/audits/joinpoint_validation.md`, criterion `01ad5a4`; 15–25 annual points, 50–5,000 events
  per year, 0–2 true joinpoints):
  - selection passes (false-joinpoint rate .012–.023 at α .05);
  - APC and AAPC intervals **fail** (t given the true number .51–.91; empirical-quantile with selection .02–.88):
    exploratory, because joinpoint locations are estimated;
  - Tiwari (.900–.921) and log-delta (.887–.900) ratio intervals pass.
- **Tool `joinpoint`** (full profile; 73 tools), with `rate_ratio={...}` for the age-adjusted ratio. Refuses
  overlapping ACS five-year releases and incomplete (suppressed) years.
- **Recipe**: `policy_change` step 4; protocol and MCP rule text.
- No manifest method and no example (see `docs/audits/round77_compatibility.md`).

## 0.72.0 (Round 76): between-group disparity measures and Kitagawa decomposition

- **Disparities between population groups** (`census/disparity.py`; frozen core `census/disparity_core.py`; N53):
  rate difference and log rate ratio against a reference group declared in advance, the Pearcy–Keppel Index of
  Disparity, between-group variance, and Theil and mean log deviation over groups. Intervals come from ACS replicate
  refits (identity scale for differences and log ratios, log scale for indices) or, for event counts with known
  populations, from the Poisson delta method (differences, ratios) and a parametric bootstrap (indices).
- **Kitagawa decomposition** of a crude-rate difference between two areas into rate and composition effects.
- **Validation** (`docs/audits/disparity_validation.md`, criterion `e995978`, 2,000 draws per cell):
  - ACS: rate difference (.879–.924) and Index of Disparity (.875–.919) pass up to a largest group-rate CV of .50;
    log ratio, between-group variance, Theil and MLD pass up to .30 (at .50: .50–.84);
  - counts: difference and log ratio pass from 20 expected events (.888–.911); the bootstrap index measures
    **fail** (.07–.84) and are exploratory;
  - Kitagawa passes in every cell (.887–.927).
- **Manifest methods `disparity` and `kitagawa`**; rows outside the validated range are refused in confirmatory
  runs.
- **Tool `disparity_measures`** (full profile; 72 tools), also `decompose_areas=[a, b]` for Kitagawa.
- **Recipe**: `health_inequality` gains "Between population groups"; `segregation` links to it. Protocol rule text
  and MCP instructions updated together.
- **Example** (`docs/audits/r76_disparity_example.md`, exploratory): MI/NY county family poverty by race/ethnicity
  and a Wayne–Oakland Kitagawa decomposition (age composition explains 0.3 of a 13.1-point gap).
- **Goldens**: run golden byte-identical; schema golden differs only in the supported-method list
  (`docs/audits/round76_compatibility.md`).

## 0.71.0 (Round 75): manifest support for the Round 73 methods, tract coordinates, recipes, README

No new statistics: every method wired here was validated earlier.

- **Manifest method `multilevel`** (`census/manifest/methods.py`; statistic `coefficient`):
  - `"groups": "county_fips"` fits two levels (Kenward–Roger; replicates; `args.target`, `args.sampling_se`);
  - `"groups": ["state_fips", "county_fips"]` fits three levels (Round 73 fixed-effect intervals, no ACS sampling
    error, no args);
  - `state_fips` and `county_fips` are GEOID prefixes the run adds when an analysis names them.
- **Manifest `"indices"` block** (new run stage `_build_indices`):
  - indicators are ACS variables or derivations, with `"loadings"`, `"pca"` or `"equal"` weights and optional
    `standardize`;
  - full-sample means, SDs and weights stay fixed in every replicate (Rounds 36/73), so the index gets replicate
    rows and a replicate SE;
  - explaining an indicator with its own index is refused (circularity);
  - `run.json` records `indices`, and the methods text describes each index.
- **`expected_count` derivation `person_years`** (an external variable; new run stage `_apply_person_years` after the
  external join):
  - expected = person-years × the ACS age × sex mix × the reference rates (Round 69's construction);
  - replicate rows are rescaled per replicate, and a propagated SE scales with the value.
- **Tract coordinates:** `frame_coordinates` on tract frames without `Year` tries 2020 tracts, then 2010 tracts
  (2019 boundaries), and notes which it used. Otherwise it raises an error asking for a `Year` column. The boundary
  error names the vintage.
- **Recipes:** six new (`policy_change`, `custom_geographies`, `dollars`, `spatial_patterns`, `cross_release`,
  `reporting`; 25 in all). `small_area` gains `spatial_small_area_estimates`, `pums_tests` gains `pums_tabulate`,
  and `preregistered` gains the Round 75 manifest options.
- **README:**
  - the latest-release paragraph;
  - a table of all 25 recipes;
  - routing rows for custom areas, dollars, spatial patterns and cross-release work;
  - the Round 75 manifest options;
  - the tract-ID advisory.
- **Goldens:** the run golden is byte-identical. The schema golden differs only in the "supported methods" list of
  one error message, which now includes `multilevel` (intended).
- Acceptance: 2213 passed, 42 skipped; 0 failures.
- **Local-model evaluation, 2026-11-22** (Gemma 4 e4b and Qwen 3.5 9B, CPU only; `docs/local_models.md`):
  - core tasks 6/6 for both models;
  - the core `get_recipe` description now lists all 25 recipes, which fixed recipe routing for
    `custom_geographies`;
  - the full profile's tool list (~28,500 tokens) needs `num_ctx` ≥ 32768. At 40k, `interrupted_series` passed 2/2
    (Gemma) and 1/2 (Qwen);
  - the new recipes state which MCP profile their tools need;
  - the harness gains two routing tasks (`recipe_custom_geographies`, `recipe_dollars`).

## 0.70.0 (Round 74): replication suite

- `docs/replications/<id>.json` holds five specs: `chr_segregation` (A), `state_gini` (B), `nc_ice` (C),
  `le_variance` (E) and `monnat_d` (D). Each gives the published target, the pre-set rule copied from its Round 66–69
  criterion, the original audit's headline, the MCP engine route and the rerun tolerance fixed in the plan. They are
  labelled "replication rerun", not new registered studies.
- `census/replications.py` and `scripts/run_replications.py [--only id]` rerun each spec through engine routes:
  - A: `segregation_indices`, compared with the CHR file from `context_sources`;
  - B: `test_association(kind="inequality")` with an income expression that clips negatives to zero;
  - C: `fit_model` and `spatial_regression(model="error")`, plus the Round 71 tract SCPC interval (descriptive);
  - E: `multilevel_model(groups=["state", "county"])`;
  - D: `build_analysis_frame` context (CBP, ERS), `read_wonder_export`, `expected_counts`,
    `build_index(method="loadings")` and the spatial error model.
- The runner writes `docs/audits/replication_suite.md`. A run with absent data is reported as skipped, and WONDER is
  never fetched.
- **Live run: all five agree.**

  | Replication | Maximum difference |
  | :--- | :--- |
  | A | 3e-14 against CHR, same 2,055 counties |
  | B | 5e-6 (stored rounding) |
  | C | 0 |
  | D | 2e-14 |
  | E | 1e-10 |

- Recipe `replications`; README "Replications" section.
- Goldens byte-identical. Acceptance: 2203 passed, 42 skipped; 0 failures; live reruns 4 passed.

## 0.69.0 (Round 73): three-level models, published-loading indices, expected counts

- **Validation** (`docs/audits/methods73_validation.md`, criterion `e97e9fc`, kept at tag `criterion-r73`):
  - **M1 passed:** three-level random intercepts (REML), with fixed-effect Wald intervals on t(G_top − 1):
    .904–.913 with 30 or 49 top units, unbalanced, shares (.70, .11, .19) and (.50, .25, .25);
  - **LI passed:** indices with fixed published loadings on Round 36's design: mean per-area coverage
    .897–.899, every area ≥ .878;
  - **M3 screening only:** delete-one-top-unit jackknife share intervals .88–.98 on 100 draws. They stay
    exploratory as pre-set; the parametric bootstrap was dropped before the run.
- **Engine:**
  - `census/multilevel3.py` `fit_three_level`;
  - `multilevel_model(groups=[top, middle], share_intervals=True)`, which refuses `sampling_se`, replicates and
    random slopes for three levels;
  - `build_index(method="loadings", loadings={...}, standardize=False)`, with two or more indicators;
  - `census.wonder_reference.acs_band_populations` and `expected_counts(..., period_years= | person_years=)`,
    which reproduce Round 69's expected deaths to 7.8e-16.
- Example (`docs/audits/r73_three_level_example.md`): replication E through `multilevel_model` gives Round 68's
  shares exactly.
- Goldens byte-identical. Acceptance: 2195 passed, 38 skipped; 0 failures.

## 0.68.0 (Round 71): tract-level spatial intervals

- **Validation** (`docs/audits/tract_spatial_validation.md`, criterion `f947f64`; NC 2018 and MI 2020 tracts,
  Round 22's linear generator, fields correlated over 0–100 km, 1,000 draws per cell):
  - **passed in every cell:** SCPC with rho_bar .20 (.885–.972), .30 (.932–.988) and a distance-set benchmark
    (.935–.989);
  - **failed:** the spatial error ML slope interval (.63–.89; .63–.76 once fields correlate over 20 km) and HC3
    (.10–.89).
- **Engine:**
  - `fit_scpc` and `fit_model(spatial="scpc")` default to rho_bar .20 for tract OLS slopes and mark .20/.30
    validated there. This follows the pre-set rule: the shortest median interval among the passing procedures.
  - Tract Poisson and binomial SCPC stay exploratory.
  - Manifest `spatial_scpc` checks the tract benchmarks when the geography level is tract.
  - `spatial_regression(model="error")` on tract GEOIDs adds an exploratory note.
- **Residual-dependence warning** (`census/residual_dependence.py`; a diagnostic, intervals unchanged):
  - `fit_model(method="replicate")` without a spatial interval tests the OLS residuals with Moran's I on six
    nearest neighbours (999 permutations, at most 5,000 rows);
  - at p < .01 it adds `spatial_dependence` and a note naming the validated route;
  - `spatial_check="auto"` uses cached boundary files only, `"on"` may download them, and `"off"` skips the test.
- **Example** (`docs/audits/r71_tract_example.md`): replication C's OLS slopes with tract SCPC intervals, which are
  3–6 times wider than HC3. All three slopes stay positive.
- Goldens byte-identical. Acceptance: 2185 passed, 38 skipped; 2 Round 61 tests updated for the tract rules (rerun clean).

## 0.67.0 (Round 72): context covariate sources

- New `census/context_sources.py`:
  - `cbp`: County Business Patterns establishments by NAICS, 2012–2022, through the Census API and the query cache;
  - `ers_typology` and `ers_rucc`: ERS 2015 economic types, 2013 rural–urban codes and metro status, from the ERS
    GIS service (CC0), cached;
  - `chr_additional`: CHR additional measures at CHR's pinned calculation-repository commit, cached.
- Interfaces:
  - `build_analysis_frame(context=[...])`;
  - a manifest `"context"` block (validated; joined after external data; `run.json` records provenance; a failed
    join is a `context_join_failed` deviation);
  - `list_health_sources(kind="context")`;
  - recipe `context_covariates`.
- Tract frames take their county's value. Context variables are covariates, never outcomes.
- Plan item "state-wide tract pulls": already the behaviour when no counties are named (`build_entities("tract",
  state)` makes one request per state), so no change.
- Live checks:
  - the CHR v141 file hashes to the value pinned in Round 66;
  - CBP 2012 NAICS 813110 gives Autauga County (01001) 51 establishments, as in Round 69;
  - ERS returns every county, with type codes 0–5.
- Goldens byte-identical. Acceptance: goldens byte-identical; 2179 passed, 38 skipped, 1 core-profile rule failure fixed (affected tests rerun).

## 0.66.0 (Round 70): `.env` discovery and long-job checkpoints

- **N47:** `census/env.py` `load_environment()` replaces the bare `load_dotenv()` in `census/api.py` and
  `mcp_server.py`. Order: `CENSUS_DOTENV`, then `.env` upward from the working directory, then upward from the
  package. It never overrides set variables and never prints values. An engine installed from a wheel now finds
  the project's `.env`.
- **N48:**
  - `run_manifest(..., checkpoint=True)`, also through MCP and the CLI: each finished analysis is pickled under
    `<output_dir>/.checkpoint`, keyed by manifest hash, analysis spec and a hash of the analysed data;
  - a rerun reuses matching checkpoints and ignores stale ones with a note. Results are identical;
  - the folder is removed after a bundle with no failed analysis.
  - Progress lines on stderr: per analysis, every 25 download requests, every 20 replicate refits
    (`CENSUS_PROGRESS=0` silences them).
- Exceptions:
  - MCP progress notifications are deferred: the tools are synchronous, and the stderr lines appear in the server
    log;
  - checkpoints are pickles, not JSON: results hold DataFrames and model objects. They are local files the engine
    wrote itself; never resume from a folder you did not create.
- Goldens byte-identical. Acceptance: goldens byte-identical; 2171 passed, 37 skipped; 0 failures.

## 0.65.0 (Round 69): replication D

- Criterion `20a4c13`, committed after a counts-only build: 3,106 counties and 2,484 with at least 10 deaths, both
  matching the paper.
- **Replicated:** Monnat (2018) Appendix Table D.2 Model 4 analogue. 100 × ln(indirectly standardized drug-related
  mortality 2006–2015) on ACS 2010–2014 covariates with state fixed effects and a spatial error term. Economic
  distress 9.95 (90% CI 7.77–12.12) against 9.62.
- Secondary results:
  - the published age-adjusted rate (> 20 deaths): 12.92;
  - censored NB2 on all counties: 14.69 (beside Model 3's 12.55).
- **S:** spatial error ML slope coverage on 3,103 national counties is .908 (λ .3) and .881 (λ .55): passes.
- The WONDER export guide's Part G was rewritten from the verified Appendix Table A.1: any-cause codes, no X85.
- No engine change; goldens byte-identical. Acceptance: goldens byte-identical; 2163 passed, 37 skipped; 0 failures.

## 0.64.0 (Round 68): replication E

- Criterion `110c22e`, committed after a counts-only data check. That check matched the paper exactly: 65,662
  tracts, 3,020 counties.
- **Replicated:** Boing et al. (2020) headline variance shares of tract life expectancy. A three-level REML null
  model gives 70.0% tract, 10.6% county and 19.4% state, against 70.4/10.7/19.0 published.
- New backlog issue N46: `multilevel_model` is two-level only. No engine change; goldens byte-identical.
- Acceptance: goldens byte-identical; 2162 passed, 37 skipped; 0 failures.

## 0.63.0 (Round 67): replication C and SCPC at tract level

- Plan `e75a41b`; criterion text `14b78b2`. Deviation 2: the criterion file was a placeholder at `daa1d15` because
  of a tool error. Simulation S ran under the plan's rule, and the full text was committed before replication C was
  computed.
- **Replication C, partly replicated:** Mitchell et al. (2022), ln(tract life expectancy) on ICE in 1,971 NC tracts.
  5 of 6 slopes replicate. ICE Race and ICE Income match to the printed digit (adjusted R² 19.60% and 48.19%,
  exact). The combined index's OLS slope is 0.147 against 0.13; its R² differs slightly, which points to a
  definition difference (the paper's text names total population as the denominator).
- **S:** on NC tract geometry, SCPC covers .91–.94 at 0–20 km but .75 (ρ̄ .05) and .81 (.10) at 100 km; HC3
  covers .12–.26. `fit_scpc` now marks tract-level (11-digit GEOID) results exploratory with a note.
- Goldens byte-identical. Acceptance: goldens byte-identical; 2161 passed, 37 skipped; 0 failures.

## 0.62.0 (Round 66): first registered replications

- Criterion `dd48bf6`; deviation 1 (`d30d7ed`) made the descriptive interval part run per county, with the rules
  unchanged.
- **A, replicated:** CHR 2025 "Residential Segregation – Black/White" reproduced exactly in all 2,055 comparable
  counties. CHR's code uses B11002 population in households, with Hispanic Whites included. The engine's
  bias-corrected index is a median 3.5 points lower in the 433 counties checked descriptively.
- **B, replicated:** the Census state Gini (B19083) from 2019–2023 PUMS for 12 states: median |difference| .0008;
  intervals contain it in 10 of 12 (the misses are CA and NC, from a small top-coding bias).
- **S:** Round 52's segregation design on GA, TX and AZ. Isolation and H pass. Bias-corrected D failed the
  [.75, 1) bin on Texas, so `REALISTIC_RANGES` for bias-corrected D is now [.15, .75). Counties in that bin
  become exploratory for D.
- Goldens byte-identical. Acceptance: 2158 passed, 37 skipped; 0 failures.

## 0.61.0 (Round 64): agent access

- No new statistics; goldens byte-identical.
- CLI: `python -m census tool` runs every shared workflow. Ten were added: `compare_groups`, `test_association`,
  `estimate_effect`, `check_agreement`, `combine_estimates`, `rank_areas`, `build_index`, `list_health_sources`,
  `run_variant` and `interrupted_series`.
- MCP:
  - new tool `interrupted_series` (full profile; 71 tools). It refuses non-consecutive years, so overlapping ACS
    five-year releases cannot be used as annual points;
  - `fit_model(model="negbin", exposure=..., censored=...)` routes to the validated interval-censored NB2.
- Rule text:
  - `docs/agent_protocol.md` marks the 16 passages the MCP instructions repeat (`<!-- mcp-rules:A|B -->`);
  - `scripts/sync_rule_text.py` generates them into `mcp_server.py`, and a test fails when they differ;
  - five stale MCP copies were corrected (PUMS ordinal models, manifest EIV covariate cap, agreement and pooling
    details, effective-n correlations).
- Agent checks:
  - core-profile text names only tools the profile has (test);
  - `docs/agent_routing.md` holds 15 research questions with their tool, profile and expected flag, run by
    `tests/test_agent_routing.py`;
  - two interrupted-series tasks were added to `scripts/local_model_eval.py`.
- Acceptance: goldens byte-identical; 2155 passed, 37 skipped; 0 failures (18 new tests).

## 0.60.0 (Round 63): small samples and many covariates

- Freeze the script and the criterion at `ac2f34c`; 30 cells, 2,000 draws each.
- Passed:
  - `interrupted_series(method="bootstrap_t_cons")` (critical values at least the t(n − p − 1) quantile) from 17
    points (.865–.896);
  - `method="bootstrap_t_bb"` (bootstrap-bias-corrected AR coefficient) from 19 points;
  - spatial EIV under the reliability gate (every reliability ≥ .8): G1 with up to 8 error-prone covariates
    (.873–.918) and G2 with up to 7 (.876–.940).
- Failed: every interrupted-series method at 15 points (.849–.855); G2 with 8 covariates (.856). These stay
  recorded limits (N35 below 17 points).
- `spatial_eiv.GATED_MAX_ERROR_COVARIATES`; `small_spatial.ITS_BOOTSTRAP_CONS_MIN_N`/`ITS_BOOTSTRAP_BB_MIN_N`. Goldens
  byte-identical.
- Demonstration (`docs/studies/r63_short_series_demonstration.md`).
- Acceptance: goldens byte-identical; 2137 passed, 37 skipped; 0 failures (5 new tests).

## 0.59.0 (Round 62): leftover failures

- Freeze the script and the criterion at `8f14e39` (generators and targets imported unchanged from Rounds 30–58).
- Passed: binomial SCPC with ρ̄ .15 (.886–.954) and .20 (.909–.966); clipped six-group bias-corrected H at any finite
  noise level. Failed: Theil T with 8,000 households (.858): it stays exploratory.
- `scpc.VALIDATED_RHO["binomial"] = (.15, .20)` (default .15); six-group `CLIP_RANGES`; Theil note. Goldens
  byte-identical.
- Exploratory example (`docs/studies/r62_binomial_scpc_example.md`). Closes N38 (Theil T as a confirmed limit).
- Acceptance: goldens byte-identical; 2132 passed, 37 skipped; 0 failures (5 new tests).

## 0.58.0 (Round 61): manifest routing for spatial methods

- No new statistics. Opt-in manifest arguments for validated methods: `fit_replicate` `args.spatial_scpc` (SCPC naive
  slopes, OLS/Poisson), `regression_calibration` `args.spatial: "clusters"` (calibrated IM-8 Poisson/NB2/binomial
  slopes) and `correlation_matrix` `args.spatial: true` (effective-n intervals, including partial).
- `scpc_core.p_value`: worst-case SCPC p-value over the benchmark grid, consistent with the interval; `fit_scpc`
  reports it.
- Registered manifests and both goldens unchanged. Closes N37.
- Acceptance: goldens byte-identical; 2127 passed, 37 skipped; 0 failures (6 new tests).

## 0.57.0 (Round 60): PUMS inequality repairs

- Freeze `transformed_summary`, `bias_corrected` (in `census/pums_inequality_core.py`), the script and the criterion
  at `60a3b06`. Round 56's generator, cells, incomes and targets.
- Passed with logit-transformed SDR intervals: Atkinson (ε 1) everywhere (.872–.893); Atkinson (ε .5) and the
  top-decile share with at least 7,000 records (≥ .871 at 3,000 households). Failed: Theil T (.820; .859 at 3,000
  households). The SDR bias correction lowered coverage and was not adopted.
- `pums_inequality`: `REPAIRED` measures use the transformed interval and the record gate; new `interval` column.
  Goldens byte-identical.
- Exploratory example (`docs/studies/r60_inequality_repair_example.md`). Closes N32 except Theil T;
  `ROADMAP_BACKLOG.md` Rounds 57–60 complete.
- Acceptance: goldens byte-identical; 2121 passed, 37 skipped; 0 failures (4 new tests).

## 0.56.0 (Round 59): correlations under spatial dependence

- Freeze the new `census/partial_neff_core.py`, the OH/PA targets (Round 33/36 procedures on the OH/PA geometry),
  the script and the criterion at `669a506`. 24 cells.
- Passed: partial correlations with the effective n of the residual series (.869–.971, MI/NY and OH/PA;
  independent-area .689); Round 48's effective-n correlations (.880–.965) and α (.901–.933) on OH/PA.
- `validated_correlations(method="partial", coords=...)` validated (one control, replicates);
  `NEFF_CORRELATION_VALIDATED["partial"]`, `OHPA_REPLICATED`. Goldens byte-identical.
- Exploratory example (`docs/studies/r59_spatial_correlation_example.md`). Closes N29 and the last part of N31.
- Acceptance: goldens byte-identical; 2117 passed, 37 skipped; 0 failures (5 new tests).

## 0.55.0 (Round 58): spatial inference outside MI/NY

- Freeze the new `census/scpc_core.py` (Müller–Watson SCPC: principal components of a worst-case exponential
  correlation, Imhof critical values, size checked by simulation), `rc_im_binomial`, the script and the criterion at
  `e8c6c8c`. 43 cells on MI/NY and OH/PA.
- Passed: SCPC for naive OLS (ρ̄ .05: .861–.930) and Poisson (ρ̄ .10: .863–.934) slopes on both regions; G1/G2 with
  three to five error-prone covariates at reliability .8 (.886–.934); calibrated binomial slopes with IM-8
  (.877–.907). Failed: binomial SCPC; IM-8 OLS in the low-reliability, correlated MI/NY cell (.858 in 10,000 draws).
- New `census.scpc.fit_scpc` and MCP `fit_model(spatial="scpc")`; `models.regression_calibration_clusters` and the
  binomial MCP route; spatial EIV reports reliabilities and applies the .8 gate outside MI/NY; IM-8 OLS note.
  Goldens byte-identical. Manifests have no SCPC option yet (exception).
- Exploratory example (`docs/studies/r58_scpc_example.md`). Closes N31 (except Round 48 designs, Round 59) and N34.
- Acceptance: goldens byte-identical; 2112 passed, 37 skipped; 0 failures (7 new tests).

## 0.54.0 (Round 57): segregation, remaining gaps

- Freeze the six-group truth file (2024 MI/NY B03002), the script and the criterion at `8bcad0b`. Twelve cells:
  clipped replicates on Round 52's race designs, six-group H, same-release county contrasts.
- Passed: clipped counties above .50 for bias-corrected isolation (to .75), two-group H (to 1.0) and four- or
  five-group H (any finite level); six-group bias-corrected H; same-release county contrasts to .50 except
  corrected D (.855). Corrected D with clipped cells stays at .50.
- `CLIP_RANGES` extended; six-group `REALISTIC_RANGES`; `SAME_RELEASE_CONTRAST_RANGES` enforced by
  `segregation_test`; `exclude_tracts`, `group_quarters_tracts` and manifest `args.group_quarters` (definitional
  option). Goldens byte-identical.
- Exploratory example (`docs/studies/r57_segregation_gaps_example.md`). Closes N30 and N33 (except infinite noise).
- Acceptance: goldens byte-identical; 2105 passed, 37 skipped; 0 failures (5 new tests).

## 0.53.0 (Round 56): PUMS income inequality measures

- Freeze the new `census/pums_inequality_core.py`, the targets (2,000,000 reference households), the script and
  the criterion at `d91201b`. Round 32 generator, 8 cells; lognormal, heavier-tailed and zero-inflated incomes.
- Passed with SDR replicate variance: Gini (.861–.908), log P90/P10 and log P80/P20 (.888–.923), Gini difference
  between two groups (.873–.899). Failed: Theil T (.811), Atkinson .5 (.845) and 1 (.858), top-decile share (.850)
  in their worst cells.
- New `census.pums_inequality.pums_inequality`; MCP `test_association(kind="inequality")` (no new tool); zero
  incomes kept for the Gini, negative incomes refused, heaped quantiles flagged. Goldens byte-identical.
- Exploratory Michigan example (`docs/studies/r56_pums_inequality_example.md`). Closes N27; `ROADMAP_BACKLOG.md`
  Rounds 51–56 complete.
- Acceptance: goldens byte-identical; 2100 passed, 37 skipped; 0 failures (6 new tests).

## 0.52.0 (Round 55): short interrupted series and estimated reference populations

- Freeze the new `census/its_small_core.py`, the SMR `reference_population_se` term, the script and the criterion
  at `dd6d6b7`. Six AR(1) series cells (15–25 points) and eight SMR cells.
- Passed: the bootstrap-t with bootstrap series at a bias-corrected AR coefficient for 20+ points (.867–.889; .857
  at 15); SMRs with the sampling variance of survey-estimated reference person-years (.892–.908). Failed: the EWC
  HAR t test (.616–.720).
- `interrupted_series(method="bootstrap_t_bc")` (validated 20+; `ITS_BOOTSTRAP_BC_MIN_N`); `method="ewc"`
  (exploratory); `indirect_standardize(reference_population_se=...)` and manifest `smr` `args.reference_population_se`.
  Goldens byte-identical.
- Demonstration on simulated inputs (`docs/studies/r55_demonstration.md`). Closes N25 for 20+ points and N26.
- Acceptance: goldens byte-identical; 2094 passed, 37 skipped; 0 failures (6 new tests).

## 0.51.0 (Round 54): OH/PA external validity, part 2

- Freeze the script, the within-state 4/6-cluster geometry, the new `census/im_clusters_core.py` and the criterion
  at `e42840d`. 48 cells: naive IM with 4, 6 and 8 clusters on MI/NY and OH/PA; Round 45 IM-8 counts, Round 53
  calibrated counts and G1/G2 with three to five error-prone covariates on OH/PA.
- Replicated on OH/PA: IM-8 count slopes (.891–.911), calibrated count slopes (.875–.912), G2 with three or four
  covariates (.861–.920). Failed there: G1 with three to five (.850–.859) and G2 with five (.807), at reliability
  .7 with correlated fields. Repair failed: IM with 4 or 6 within-state clusters (OH/PA worst cells .827 and .753).
  A fresh-seed MI/NY rerun of naive IM-8 covered .849 in one cell.
- Engine notes only: `geography_notes(kind=...)` (counts replicated; naive IM repair failed), an exploratory note
  for spatial EIV with many covariates outside MI/NY, `IM_CLUSTER_COUNT_REPAIR_VALIDATED`. Goldens byte-identical.
- Exploratory example: OH/PA county child poverty with IM at 4, 6 and 8 clusters (`docs/studies/r54_ohpa_im_example.md`).
  New issue N31.
- Acceptance: goldens byte-identical; 2088 passed, 37 skipped; 0 failures (6 new tests).

## 0.50.0 (Round 53): corrected GLM slopes, part 2

- Freeze `regression_calibration(se_method="jackknife")`, the new `census/rc_spatial_core.py`, the script and
  the criterion at `8d48956`. Round 46's binomial failure was in the SE (bias −.016 to −.001), so the repair is
  a delete-one-area jackknife (≈ HC3; t with n − p df).
- Passed: RC jackknife for binomial (.882–.904), Poisson (.886–.904) and NB2 (.897–.908); pooled calibration with
  IM-8 count slopes under spatial dependence for Poisson (.877–.904) and NB2 (.894–.909; naive IM-8 .349–.890);
  G1/G2 with five error-prone covariates (.864–.925, unstable at reliability .7 with correlated fields). Failed:
  six covariates (.804–.811).
- `RC_VALIDATED_SE`; `fit_count_model(spatial="clusters", calibrate=...)`; `VALIDATED_MAX_ERROR_COVARIATES = 5`;
  MCP `fit_model(se_method=...)` and the calibrated IM-8 route; manifests accept `args.se_method`. Goldens
  byte-identical.
- Exploratory example: county child poverty on income and unemployment (`docs/studies/r53_rc_example.md`).
  Closes backlog 4, N22 and N23 (except binomial under spatial dependence and six or more covariates).
- Acceptance: goldens byte-identical; 2082 passed, 37 skipped; 0 failures (7 new tests).

## 0.49.0 (Round 52): segregation beyond poverty and income

- Freeze the truth file (2024 B03002 for MI/NY/OH/PA, 2024 B17001 for OH/PA, 2015–2019 B17001 for MI/NY; cached
  API responses, byte-reproducible), the script and the criterion at `b19696b`. Seven designs × two group
  correlations; finer noise bins above .50; ranges combine every design judging a bin (group-type blind).
- Passed: bias-corrected D to noise 1.0, isolation at any finite level, two-group H to 1.0; four- and
  five-group bias-corrected H at any finite level (.953–.997); release contrasts with the larger noise level
  below .50 (.869–.971). Failed: naive isolation/H for race groups at .15–.50, which removes their Round 50
  range; naive D; naive multigroup H; bias-corrected D and H above 1.0 for Black/non-Black.
- `REALISTIC_RANGES` widened and extended to four and five groups; new `CONTRAST_RANGES`; `segregation_test`
  validates release contrasts only with two groups and the larger noise level below .50. Infinite noise levels
  are never validated. Goldens byte-identical.
- Exploratory example: race/ethnicity segregation and the 2019–2024 poverty-segregation change in MI/NY
  (`docs/studies/r52_segregation_groups_example.md`). Closes N21; new issue N30 (clipping validated only below
  .50; prison group quarters).
- Acceptance: goldens byte-identical; 2074 passed, 37 skipped; 0 failures (8 new tests).

## 0.48.0 (Round 51): negative replicate estimates

- Freeze the script, the SMR policy argument and the criterion at `2837bfb` before the run. Segregation:
  Round 50's design with Gaussian replicates (negative counts in 2.6–4% of tract-group cells), clipped at zero
  before the refits; Round 50's bin rule plus an affected-draw check. SMR: eight cells with a high-CV band.
- Passed: clipping for bias-corrected D, isolation and H and three-group H, keeping their Round 50 ranges
  (affected county-draws .902–.990); SMR with negative band replicates used as published (.903–.922) or clipped
  (.891–.917). Failed: naive isolation and H with clipped cells (.847–.860).
- `segregation_replicate(negative_replicates=...)`, default `"clip"`, new `clipped_replicates` column and
  `CLIP_RANGES`; `indirect_standardize(negative_replicates=...)`, default `"accept"`. `"refuse"` keeps the
  strict policy. Manifests (`segregation`, `smr`) keep it unless `args.negative_replicates` opts in; goldens
  byte-identical.
- Exploratory example: the ten county-designs Round 50 refused are estimated and validated
  (`docs/studies/r51_negative_replicates_example.md`). Closes backlog N20 and N28.
- Acceptance: goldens byte-identical; 2066 passed, 37 skipped; 0 failures (8 new tests).

## 0.47.0 (Round 50): segregation under realistic ACS error

- Freeze the truth file (2024 MI/NY tract counts and published SEs, built reproducibly from the cache),
  the script and the criterion at `686d121` before the run. Gamma-copula counts and replicates; group
  error correlation 0 and −.3; counties judged by noise level (largest group median tract CV).
- Passed to noise level .50: bias-corrected D (county-bin mean coverage .870–.921; every county ≥ .827),
  isolation (.883–.920) and H (.925–.968), and bias-corrected three-group H (.944–.999). Naive isolation
  and H pass only to .30. Failed: naive D (.713–.870), the Round 28 default, and naive three-group H.
- `segregation_replicate`: every default is now bias-corrected; new `noise_level` column and gate
  (`REALISTIC_RANGES`, `MAX_VALIDATED_MEDIAN_CV = .50`, at least five populated tracts); the Round 28
  max-CV ≤ .15 range still validates. Three-group H can be confirmatory. Manifests use the same gate.
- Exploratory example: county poverty and income segregation in MI/NY, 132 of 140 counties validated
  (`docs/studies/r50_segregation_example.md`). New backlog issues N20 (negative VRE replicates refuse
  some counties) and N21 (race groups untested).

## 0.46.0 (Round 49): survey-weighted PUMS models

- Freeze `census/pums_models_core.py`, the reference targets, the script and the criterion at `c0dfd0a`
  before the run; the generator is Round 32's (household clustering, unequal weights, ACS-style SDR
  replicate weights).
- Passed: ordered logit (.879–.906) and ordered probit (.875–.906), multinomial logit (.879–.912),
  weighted median regression (.887–.915) and probit (.878–.907) with the SDR replicate variance (80
  warm-started refits). Model-based SEs with normalised weights under-cover (.62–.887).
- `census.pums_models.fit_pums_model(formula, df, model)`; MCP `pums_regression(model="ordered_logit" |
  "ordered_probit" | "mnlogit" | "median" | "probit")`.
- Exploratory example: disability with poverty band, insurance and earnings in the Michigan PUMS
  (`docs/studies/r49_pums_models_example.md`).

## 0.45.0 (Round 48): small samples and spatial dependence

- Freeze `census/small_spatial_core.py`, the script and the criterion at `3fb07d3` before the run; the
  problems reuse the Round 33, 36, 37, 38 and 42 generators.
- Passed: Clifford–Richardson–Hémon effective-sample-size intervals for Spearman, Kendall and Pearson
  correlations (.862–.967) and Feldt α (.912–.926) under spatial dependence; Hartung–Knapp for 5–10
  estimates with the variance factor truncated at 1 (.874–.918); Bland–Altman limits with moment-based
  SEs (.884–.936); the AR(1) bootstrap-t for interrupted series with 30+ points (.883–.896).
- Failed: REML AR(1) (.79–.88) and the bootstrap-t below 30 points; IM-8 versions of Spearman, Pearson
  and α.
- `validated_correlations(coords=...)`, `build_index(coords=...)`, MCP `spatial=True`;
  `interrupted_series(method="bootstrap_t" | "reml")`; `combine_estimates` truncates for k > 4 (validated
  up to 10); `check_agreement` limits validated.
- Exploratory example: Round 29 correlations with poverty corrected for spatial dependence
  (`docs/studies/r48_spatial_example.md`).

## 0.44.0 (Round 47): causal and missing-data robustness

- Freeze `census/causal_robustness_core.py`, the script and the criterion at `cbdc97f` before the run.
- Passed: AIPW on confounders calibrated within treatment groups (.889–.905; plain AIPW .77–.87 with
  same-sign noisy confounders); calibrated mediator path (.883–.898; naive .58–.86); Anderson–Rubin
  interval at any first-stage F (.894–.908); chained-equations MI for two incomplete covariates
  (.898–.916; complete case .84 under MAR).
- The pre-set 2SLS Wald cut-off came out at F = 0 (it covered in every bin), so the unvalidated corr < .3
  rule is gone. Below F = 10 the estimate is unstable and the tool points to the AR interval.
- `estimate_effect(calibrate=True)` for treatment and mediation; `iv` reports `ar_interval`;
  `fit_model(impute=["w", "v"])`. Plain AIPW with noisy confounders now reports `validated=False`.
- Exploratory example: instrumented poverty slopes and calibrated metro effects on Round 29 SMRs
  (`docs/studies/r47_causal_example.md`).

## 0.43.0 (Round 46): measurement-error-corrected GLM slopes; spatial EIV with more covariates

- Freeze the validation script and criterion at `4aceb22` before the run (2,000 draws per cell).
- Regression calibration against the true slope: passed for Poisson (.869–.893) and NB2 (.887–.918);
  failed for binomial (.851 at reliability .9 with correlated errors; .851–.889). Naive GLMs .38–.85.
  `models.RC_VALIDATED` and a `regression_calibration_validated` diagnostic; binomial results carry an
  EXPLORATORY note, and manifests refuse binomial regression calibration in confirmatory runs.
- Spatial EIV G1/G2 with three and four error-prone covariates passed (.876–.927);
  `spatial_eiv.VALIDATED_MAX_ERROR_COVARIATES` is now 4. At reliability .7 with correlated fields the
  point estimates were unstable (mean bias up to +.17 on .5; up to 5.7% failed fits); fits with 3–4
  error-prone covariates say so.
- Exploratory example: Round 29 slopes with poverty's sampling error corrected (NB2;
  `docs/studies/r46_rc_example.md`).

## 0.42.0 (Round 45): count-model repairs

- Freeze procedures, script and criterion at `0c368dd` before the run.
- Passed: interval-censored NB2 for hidden 1–9 counts (.869–.898; censored Poisson .83–.86); IM-8 count
  slopes with per-cluster NB2 (full-sample α) or Poisson GLMs (.894–.909; pooled NB2-HC3 .80 under spatial
  correlation); NB2-HC3 with noisy ACS exposures held fixed (.888–.891; Poisson HC3 .83–.86).
- New `census.count_repairs_core` (frozen), `missing_censored_its.fit_censored_negbin`,
  `count_models.fit_count_model(spatial="clusters")`, MCP `fit_model(model="negbin", spatial="clusters")`,
  and `within_states` cluster assignment for adjacent states.
- Exploratory example: Round 29 counts (`docs/studies/r45_count_example.md`).

## 0.41.0 (Round 44): Round 29 under NB2 and an OH/PA re-check of the spatial validations

- Post hoc (author self-review): Round 29's H1–H3 hold under NB2-HC3 in MI/NY and OH/PA; an exploratory
  interval-censored fit of H2's hidden counts gives the same slope. Registered results unchanged.
- OH/PA re-check (criterion `09ecd91`; state-respecting eight-cluster geometry, 155 counties): the
  corrected-slope G1/G2 replicate (.863–.921); naive IM-8 C1 fails with spatially correlated fields
  (.70–.85; independent cells .89–.91). IM-8 fits outside MI/NY and clusters crossing state borders now
  carry notes.
- NB2 alpha falls back to Nelder–Mead when BFGS fails (found on real WONDER counts); identical results
  whenever BFGS converges.
- STATUS "Current release" corrected to v0.39.0.

## 0.40.0 (Round 43): manifest routing and housekeeping

- Manifests can opt in to methods validated in Rounds 33, 35 and 39: `correlation_matrix`
  `args.interval: "validated"`, `fit_replicate` `args.model: "negbin"` (NB2-HC3) and `fit_eiv`
  `args.spatial: "clusters" | "error"`. `validate_manifest` refuses each outside its validated range;
  exploratory correlation pairs and spatial EIV with more than two error-prone covariates are not tested
  in confirmatory runs. Registered manifests and both goldens are unchanged.
- Saturated fits (residual df 0) report missing, not infinite, model SEs; the coefficient plot no longer
  crashes on them (STATUS backlog 7).
- Core-profile MCP instructions rewritten compactly (12,480 to under 4,000 characters, test-bounded at
  8,000); tool counts in README, STATUS and `docs/local_models.md` corrected and tested.
- `estimate_effect` names missing arguments instead of catching `AttributeError`; `impute_and_fit` draws
  the imputations once for all terms (identical results); 2SLS reports the first-stage F and says the
  weak-instrument cut-off is not yet validated.

## 0.39.0 (Round 42): missing data, censored counts and interrupted series

Released as one bundle (owner decision, 2026-11-19): tag `v0.39.0` contains Rounds 31–42.
Versions 0.28.0–0.38.0 below were never tagged or released separately.

- Freeze procedures, script and criterion at `5f81de2` before the run.
- Passed: multiple imputation of one incomplete covariate (Rubin's rules). Failed (exploratory): an
  interval-censored Poisson likelihood for counts hidden as 1–9 (narrowly; better than dropping them) and
  interrupted time-series intervals with 20 annual points (OLS, Newey–West, AR(1) GLS).
- New `census.mci_core` (frozen) and `census.missing_censored_its`; MCP `fit_model(impute=...)`.
- Completes the statistics roadmap (Rounds 31–42).

## 0.38.0 (Round 41): treatment effects, instrumental variables and mediation

- Freeze procedures, script and criterion at `b7464e5` before the run.
- Passed: IPW/AIPW/regression-adjustment treatment effects with precise confounders; 2SLS with an
  independent second measurement as instrument (removes covariate attenuation); Sobel and bootstrap
  mediation with an exact mediator. Mediator sampling error broke mediation coverage. Design
  limitation recorded: the treatment cells did not test residual confounding.
- New `census.causal_core` (frozen), `census.causal`, MCP tool `estimate_effect`, recipe `causal`.

## 0.37.0 (Round 40): beta and median regression

- Freeze procedures, script, criterion and targets at `d5c9b02` before the run.
- Passed and selected: beta regression with the HC0 sandwich; median regression with the kernel SE.
  Failed: beta model-based SEs. Replicate-augmented variants over-cover and are not used.
- New `census.beta_median_core` (frozen), `census.regression_families`; MCP `fit_model(model="beta"|"median")`.
- Deferred: PUMS ordinal/multinomial/weighted quantile regression and GEE.

## 0.36.0 (Round 39): multivariate tests and count models

- Freeze procedures, script, criterion and targets at `0686bc0` before the run.
- Passed: multivariate wild score bootstrap (MANOVA/MANCOVA); NB2 with HC3 for count slopes. Failed:
  Poisson HC3 under strong overdispersion; zero-inflated Poisson.
- New `census.manova_counts_core` (frozen) and `census.count_models`; MCP `compare_groups(outcomes=...)`
  and validated `fit_model(model="negbin")`.
- Exploratory MANOVA example (poverty and share 65+ by metro class).

## 0.35.0 (Round 38): combining evidence

- Freeze procedures, script and criterion at `3edd5f4` before the run.
- Passed: Paule–Mandel + Hartung–Knapp–Sidik–Jonkman pooling for 2–4 estimates; fixed effect only
  without heterogeneity; TOST equivalence; z-test power and minimum detectable effects. Failed:
  DerSimonian–Laird with heterogeneity; HKSJ at 8 studies with heterogeneity (.855).
- New `census.evidence_core` (frozen), `census.evidence`, MCP tool `combine_estimates`, recipe
  `combine_estimates`.
- Exploratory example: pooling Round 29's replications.

## 0.34.0 (Round 37): agreement between sources

- Freeze procedures, script, criterion and targets at `e6d4be6` before the 8-cell run.
- Passed: bias with a t interval, Cohen's kappa of quintile classes. Failed (estimates only):
  Bland–Altman limits of agreement (observed and error-free) and Lin's concordance correlation (plain
  and error-corrected) intervals.
- New `census.agreement_core` (frozen), `census.agreement.check_agreement`, MCP tool `check_agreement`,
  recipe `agreement`.
- Exploratory example: ACS vs Census population estimates for MI/NY counties.

## 0.33.0 (Round 36): composite indices

- Freeze procedures, script, criterion and α targets at `e86907d` before the 8-cell run.
- Passed: per-area index-score intervals with fixed full-sample standardisation and weights (PCA and
  equal); Feldt α interval for independent areas.
- New `census.index_core` (frozen) and `census.composite_index.build_index` (scores with intervals,
  quintile stability, α, optional typology with replicate adjusted Rand index; circularity guard);
  MCP tool `build_index`; recipe `composite_index`.
- Exploratory MI/NY example exposed a construct-validity problem (NYC's car-free housing drives the
  index; α 0.40), recorded in the recipe.

## 0.32.0 (Round 35): corrected EIV slopes under spatial dependence

- Freeze candidates, script and criterion at `46fab40` before the 8-cell run (Round 30's linear design
  plus outcome error correlated 0/0.3 with a covariate's error).
- Passed: G1 (eight fixed clusters, pooled within-cluster reliability correction, t(7)) and G2
  (spatial-error λ̂ by ML, whitening, Fuller EIV). Closes the corrected-slope part of backlog item 1
  for linear models.
- New `census.spatial_eiv_core` (frozen) and `census.spatial_eiv.fit_spatial_eiv`; MCP
  `fit_model(method="eiv", spatial="clusters"|"error")`. Manifests unchanged.
- Post hoc R21b: H1 and H4 hold under both (`docs/studies/r35_posthoc_spatial_eiv.md`).

## 0.31.0 (Round 34): ranking areas

- Freeze procedures, script and criterion at `6286ad9` before the 8-cell run (K 40/145, SNR 0.5/2,
  ties or none).
- Passed: Klein–Wright–Wieczorek individual and joint rank intervals; Holm and simultaneous
  comparisons of each area with a weighted reference that shares their errors. Failed and not
  offered: parametric-bootstrap percentile rank intervals.
- New `census.ranking_core` (frozen), `census.ranking` (API; suppressed values excluded), MCP tool
  `rank_areas`, recipe `rank_areas`.
- Exploratory example: Michigan counties ranked by poverty (`docs/studies/r34_ranking_example.md`).

## 0.30.0 (Round 33): rank methods and model diagnostics

- Freeze procedures, script, criterion and 400,000-area reference targets at `f660e9c` before the
  8-cell run (correlation 0/0.4 × reliability 0.9/0.7 × independent/spatial fields).
- Passed: Spearman and Kendall Fisher-type intervals; Pearson and partial (one control) intervals
  with the ACS replicate variance added; Brunner–Munzel superiority; Kruskal–Wallis. Failed: plain
  Fisher-z Pearson and partial intervals (.84). All correlation intervals under-cover with spatial
  dependence.
- New `census.rank_methods`, `correlation.validated_correlations` (methods pearson, spearman,
  kendall, partial; `validated_intervals` in the MCP correlation tool), `compare_groups(method="rank")`,
  `census.diagnostics.model_diagnostics` (attached to OLS `fit_model` and `compare_groups`), recipe
  `rank_methods`. Manifests unchanged.
- Exploratory MI/NY example (`docs/studies/r33_rank_methods_example.md`).

## 0.29.0 (Round 32): design-based PUMS tests

- Freeze procedures, script, criterion and 2,000,000-household reference targets at `d65d034` before
  the 8-cell run (household ICC 0.1/0.4, weight CV 0.3/1.0, 800/3,000 households; SDR replicate
  weights from a Paley order-80 Hadamard matrix, as the ACS).
- Passed and selected: first-order Rao–Scott independence tests (tables up to 3 × 4), design F and
  z tests for group means, differences of proportions, odds ratios, relative risks, differences of
  means and medians, Korn–Graubard proportions. Failed: design-blind Pearson, Wald proportions,
  design Wald F for 3 × 4 tables.
- New `census.pums_tests` (frozen procedures), `census.pums_inference` (PUMS wrappers), MCP core tool
  `test_association` (core cap 16), recipe `pums_tests`.
- Exploratory Michigan PUMS example; it showed that medians of heaped amounts get zero replicate SEs,
  now detected (`heaping_share`) and labelled exploratory.

## 0.28.0 (Round 31): omnibus tests and group comparisons

- Freeze candidates, script and criterion at `3e3094a` before the 36-cell run (6 designs × 3
  models × 2 fields; 2,000 null and 500 alternative draws per cell).
- F references (W1, HTZ W2) failed everywhere. The wild score bootstrap (W3) passed OLS factor
  tests and binomial/Poisson spline tests; IM-8 Hotelling T² (W4) passed OLS/Poisson factor tests.
  Holm pairwise passed all models; simultaneous max-|t| passed OLS only.
- New manifest statistic `joint_test` (variable or term; two-sided) with confirmatory refusals for
  unvalidated combinations and fewer than 145 areas. `joint_wald` unchanged and exploratory.
  Binomial/Poisson splines are confirmatory with `joint_test` hypotheses.
- New `census.group_compare.compare_groups` and MCP tool `compare_groups` (core profile; cap 15):
  t-test, one-way ANOVA, ANCOVA and two-way interactions with ACS replicates, adjusted means,
  Holm or simultaneous pairwise differences, partial η²/ω², Brown–Forsythe and classical
  comparison diagnostics. Recipe `group_comparison`.
- Exploratory MI/NY example (county poverty by metro class); outputs in `r31_example_outputs.tar.gz`.

## 0.27.0 (Round 30): IM-8 with ACS sampling error

- Freeze script, criterion and twelve 400,000-area beta-star references at `2774140`
  and push before the 2,000-draw/cell run. C1 passed all linear/binomial/Poisson
  cells (.8690–.9235); C2 EIV failed (.0695–.9035), with unstable corrected moments.
  No criterion, seed, target, draw count or cluster count changed afterwards.
- Enable C1 via existing `spatial_clusters` for unweighted OLS/binomial/Poisson,
  population target and fixed Poisson offsets. Independent ACS error enters the
  between-cluster spread; no additive ACS variance or measurement-error correction.
  Report `se_cluster_mean`, t(7), unweighted cluster-mean coefficients. Uniformly
  constant nuisance terms are absorbed/not estimable; partial constancy is refused.
  Failed C2 remains refused, including exploratory manifests; no naive fallback.
- Post hoc, cached/hash-verified R21b/R22/R29 MI/NY checks with HTTP blocked:
  R21b unavailable; R22 H1/H2 retained, H3 unsupported; R29 H1/H3 retained,
  overdose H2 not retained (Holm p=.169). Registered manifests/results unchanged.
  Report is author self-review, not independent. OH/PA not re-checked.
- Acceptance: 1886 passed, 37 skipped, 4 warnings and 50 subtests; zero failures,
  26 new tests. Both goldens byte-identical (640 snapshots; 29 scenarios).
- R29 coefficient-only outputs pass disclosure audit; local output archive
  key-scanned. No new MCP tools/dependencies, WONDER/private-export access,
  GitHub CI, merge into defaultBranch, tag or release.

## 0.26.0 (Round 29): manual WONDER mortality studies

- Remove the WONDER API client, fetch script, API tests and XML fixture. All inputs
  are owner-supplied, pinned manual exports; no WONDER network access.
- Inventory all 62 files, including wrapped footers, optional population/rate
  columns, older unreliable markers, cause-code equivalence and MCD filters.
- Read national age × sex references, combine the two youngest groups, refuse
  suppressed reference cells and check hashes/periods. Add a disjoint B01001
  template and expected-count derivations with all 80 ACS replicates.
- Separate geographic join failures from suppressed outcomes and unsuppressed
  missing values. Mask protected county values throughout bundles/snapshots/maps;
  reject unverifiable complementary totals and scan study outputs before archiving.
- Register MI/NY and geography-only OH/PA mortality manifests together at
  `150e172`, before outcomes. All three poverty coefficients are positive and
  supported after Holm correction; all replicate. The overdose conclusion holds
  under both registered endpoint-assignment sensitivities. Reports distinguish
  fixed-offset model inference, reference-aware SMR intervals, descriptive EB
  maps and exploratory SII/RII; spatial dependence remains unresolved.
- Acceptance: 1860 passed, 37 skipped, 4 warnings and 50 subtests; zero failures.
  Twenty new synthetic tests; all legacy schema snapshots and all non-WONDER
  execution scenarios unchanged (`docs/audits/round29_compatibility.md`).
- No new dependencies or MCP tools. Version prepared on the branch; no tag or release.

## 0.25.0 (Round 28): segregation indices and reference-aware SMR

- Fixed, committed-and-pushed validations: segregation `4791763` (8,000 draws;
  audit `43cbedf`), SMR reference uncertainty `134bf7f` (12,000 draws; audit
  `8335199`). No seeds or criteria retuned after results.
- Add county D, isolation and Theil H from tract counts, strict 80-replicate
  uncertainty and the preset I-4(mean(Ir)-I) correction. Defaults selected by
  passing coverage: naive D, corrected isolation and corrected H. Failed
  variants and multigroup H remain exploratory. No negative clipping/dropping;
  zero tracts and undefined absent groups are noted.
- Register `segregation` through one MethodSpec; within-release county contrasts
  preserve shared replicate covariance, non-overlapping releases add variances.
  Explicit one-area nulls and release selectors prevent silent comparison choices.
  One-sided tests center on estimate-null. Add a recipe and matching agent/MCP rules.
- Extend SMR with hashed period_years and reference_counts. Rates per person-year
  scale expected counts by period; combined intervals add Poisson reference-rate
  variance. Shared band contributions are pooled before squaring. Internal-reference
  conservatism is noted. Fixed-E exact limits still exclude uncertainty in E.
- Reference-aware SMR passed coverage 0.8995–0.9105; omitting the reference term
  reached 0.7240 in the sparse-reference E=100 cell. Reference person-years remain
  fixed. Existing SMR defaults and execution golden remain unchanged.
- Range gate (review fix): a county with any tract group-count CV above .15, the
  validated simulation range, is marked not validated (`max_count_cv` reported);
  confirmatory hypotheses on it are refused (`hypothesis_not_tested`), exploratory
  manifests still test it. No 2018-2022 MI/NY county's white/Black tract counts
  meet the range, so segregation is effectively exploratory pending a
  realistic-error validation.
- No new dependencies or MCP tools (63); version 0.25.0.

## 0.24.0 (Round 27): descriptive EB rates and exploratory nonlinear tests

- Commit and push both fixed protocols before their full simulations: EB criterion
  `d4dec47` (8,000 datasets, 200 bootstrap refits each), joint criterion `376ce69`
  (16,000 null datasets plus fixed-alternative power draws). Audits retain all results.
- Poisson–Gamma ML includes interval-censored count probabilities. Both 90% procedures
  passed the six required cells: posterior coverage 0.8813–0.9000, Laird–Louis
  0.8718–0.8914. Posterior remains default. Outputs preserve suppression and GEOID,
  expose shrinkage, posterior ratios/limits, optional rates and validation metadata.
  This is descriptive only; fixed expected counts/rates, independent areas.
- Natural splines and full-covariance joint chi-squared tests **failed** the preset
  size criterion (0.1055–0.1825; four cells above 0.13). Both remain exploratory;
  confirmatory manifests refuse them. Do not retune the frozen experiment.
- Centered cr(df=3/4/5) bases freeze full-sample knots in replicate refits and influence
  checks. Joint hypotheses select standalone columns by variable, apply R2 and reject
  singular covariance. W reports df and has no coefficient CI or odds ratio.
- Expose term-labelled full sampling covariance and HC3 joint-model covariance.
  These additive diagnostic fields and dependent bundle hashes are the documented
  golden exception; existing numerical coefficient/hypothesis results stay unchanged.
- Mirror usage and restrictions in the small-area recipe and agent/MCP guidance.
  Existing maps accept eb_ratio. No new dependencies or MCP tools (63).

## 0.23.0 (Round 26): spatial-cluster inference and validation

- Pre-register and run 12,000 datasets on the unchanged Round 22 spatial design. IM with
  eight clusters passed all six cells (coverage 0.886–0.912); CR1-t at 8/12 clusters and
  999-Webb-weight restricted bootstrap at 12 clusters failed and remain exploratory.
- Add fixed geographic clustering (50 seeded EPSG:5070 restarts, >=5 analysed units/group),
  recorded assignments, and per-method/count manifest gates without new MCP tools.
- IM reports cluster-mean coefficients and t(7) intervals using `se_cluster_mean`; it has
  no additive full-sample model SE. IM/WCR require population target and refuse analysed
  variables with ACS replicates. Unweighted OLS/binomial only; EIV/Poisson/WLS unsupported.
- Cache-only post hoc report preserves original results and records the requested IM
  re-checks as unavailable under the retained protocol. The additional authorized R21b
  OLS sensitivity keeps ACS replicates with conservative combined SEs and is unclustered.
  Original residual Moran I: 0.195464 / 0.183552. Cluster map remains a release artifact.
- Mirror restrictions in recipes and agent/MCP guidance. Existing schema/run goldens
  remain byte-identical for old arguments; no unrelated bug fixes or registered-manifest edits.

## 0.22.1 (Round 25): staged manifest execution

- Split `run_manifest` into a 7-line driver over named stages sharing a typed `RunState`,
  retaining stage functions and monkeypatch lookups in `census.manifest.run`. The longest
  stage is 77 lines; `run.py` remains 896 lines. Public signature/docstring and `run_variant`
  are unchanged; no statistical method, test file, dependency or MCP change.
- Capture offline execution before refactoring: 29 deterministic run-golden scenarios,
  returned results and normalised text-artifact SHA-256s, covering all 19 blocking
  deviation kinds. Both this corpus and the 516 schema snapshots remain byte-identical.
  Execution-build stamps, output paths and wall-clock creation times are documented
  exclusions; scientific values and registered manifest hashes are retained.
- Full suite unchanged: 1703 passed, 37 skipped, 49 subtests. Existing suppression/join
  and saturated-fit plotting observations are recorded in the plan, without fixes.

## 0.22.0 (Round 24): method registry and public-health inequality

- Centralize manifest execution, method-specific validation, statistics and methods text in
  `MethodSpec`; preserve all 478 refactor snapshots and the existing public constant ordering.
- Add weighted area ridits, SII, log RII and concentration with independent-area HC3 and strict
  ACS replicate uncertainty; concentration ranks from least to most deprived (the reverse of
  the usual income-ranked sign). Warn about rank-error attenuation above median CV 15%.
- Add indirect SMR, pooled counts/expected counts, fixed-E Garwood intervals and combined
  Poisson/ACS log intervals; require explicit per-person reference rates and a hashed citation.
  Negative ACS band replicates are refused under the fixed validation domain, even with positive E.
- Both pre-specified validations passed: inequality conservative coverage 0.876–0.905 in
  required CV<=15% cells; SMR combined coverage 0.893–0.909. High-error inequality cells
  remain outside the validated range (coverage as low as 0.638 at rank CV 30%).
- Register both manifest methods without adding MCP tools (63). Extend circularity to ranked
  external outcomes, add log-scale ratio columns, explicit complete-case exclusion records,
  public library exports and the `health_inequality` recipe across agent guidance.
- Cache-only exploratory MI/NY LBW example: 144 complete counties, rank CV 6.63%; all
  conservative intervals include their null. Outputs remain a separate local archive.

## 0.21.1 (Round 23): internal package split

Internal: `census.manifest` split into a package (no behaviour change; golden snapshot identical)

## 0.21.0 (Round 22): count outcomes and spatial standard errors

- Label registered exploratory manifests and their analysis provenance explicitly.
- Add Bartlett Conley standard errors for EIV and binomial/Poisson replicate GLMs;
  fixed coverage validation FAILED, so spatial SEs remain exploratory only.
- Support external count/proportion outcomes with explicit trials/exposure,
  Pearson dispersion scaling and binomial odds ratios; register CHR v037.
- `fit_replicate(scale="robust")`: HC3 sandwich SEs for binomial/Poisson GLMs, valid under between-area
  overdispersion. Fixed pre-registered validation PASSED (coverage 0.879-0.897 at nominal 0.90; Pearson X2
  0.689-0.899). Manifests with external count outcomes now require `scale: "robust"`; `"X2"` is refused except
  for the three registered Round 22 manifests (`LEGACY_X2_MANIFESTS`).
- Held-out OH/PA apportionment re-test PASSED (ratio 0.9128); add opt-in dominant
  parent share >=0.95, preserving the missing default.
- Study: `docs/studies/r22_mi_ny_county_low_birth_weight.md`, MI/NY county low birth weight (CHR&R 2025,
  NCHS natality 2017-2023) against the Round 20 determinants. As registered: poverty (H1) and cost burden (H2)
  supported, no vehicle (H3) not supported. Post hoc (X6): robust SEs are 1.8-2.6x the quasi-binomial ones,
  which the study's own simulation shows under-cover. With robust SEs H1 holds and H2 would not
  (Holm p 0.117; 0.320 with the validated HC3 option, under which H1 still holds at 0.049). Exploratory: without NYC, no vehicle turns positive; with race composition, cost burden turns negative.

## 0.20.0 (Round 21): external health outcomes (Step 2)

- `census.health_sources`: registry of external health sources and the CDC PLACES connector (2025 release,
  tract and county). Keyless Socrata CSV exports filtered to states, measures and crude values; pages cached
  with SHA-256 sidecars; the dataset revision stamp (`rowsUpdatedAt`) recorded with the download it describes;
  `CENSUS_HEALTH_OFFLINE`; SE from the published 95% interval.
- Manifest `external` variables: joined on GEOID after the ACS frame; outcome-only for `fit_eiv`,
  `fit_replicate` and `fh_regression`; single release; tract vintage checked (or `harmonize_tracts_to`);
  blocking `external_unavailable` and `external_join_failed` deviations; `create_manifest` notes covariates that
  are inputs of the source's model (circularity); provenance, citation and methods text.
- `fit_eiv`: `fixed_variables` (an outcome from another survey, no replicates), `cluster="GEOID.str[:N]"`, the
  independence SE kept in the diagnostics when clustered. Cluster-robust SEs validated by simulation
  (`docs/audits/eiv_cluster_validation.md`, `scripts/eiv_cluster_validation.py`).
- `analysis_frame` builds its columns at once (no pandas fragmentation warnings).
- Study: `docs/studies/r21_mi_ny_places_disability_validation.md`: PLACES 2025 adult disability against the
  ACS 2020-2024 direct estimate, MI/NY tracts. H1-H3 supported (slope about 0.8 after correcting ACS error,
  within counties and beyond age); levels differ by about 13 points; exploratory E2 shows the circularity of
  determinant studies with a PLACES outcome.
- Part 2 (owner request): the circularity rule is enforced and stated in the MCP. `create_manifest` refuses
  (R1) an external outcome whose construct the ACS measures directly (PLACES DISABILITY: B18101) unless the
  analysis compares it with that ACS measure, and (R2) a tested term built from the outcome model's inputs
  unless the hypothesis carries a written `circularity_justification`. The rule is in the server instructions,
  the core profile, `docs/agent_protocol.md` section 16, the recipe `external_health_outcome` and the new tool
  `list_health_sources`.
- New sources: USALEEP tract life expectancy (2010 tracts; fully predicted tracts dropped by default;
  `apportion_to: 2020` by population-weighted rate apportionment, split tracts left missing because
  inheritance failed validation, `docs/audits/rate_apportionment_validation.md`); County Health Rankings &
  Roadmaps 2025 county data (direct NCHS mortality measures; PLACES-based measures flagged; ACS-derived columns
  refused); CDC WONDER exports (`census.vital_records`: pinned by SHA-256, footer required, suppressed counts
  censored, exact Poisson intervals).
- `fit_eiv(cluster_se="jackknife")`: delete-one-cluster jackknife, validated beside CR1; `make_map`
  `scheme="diverging"`; `run_variant` (exploratory refits of a finished run, MCP tool).
- Study (Part 2): `docs/studies/r21b_mi_ny_county_premature_mortality.md`: county premature age-adjusted
  mortality (CHR&R 2025, NCHS 2020-2022) against the Round 20 determinants, MI/NY counties. Poverty (H1) and
  disability (H4) supported; no-vehicle (H2, reversed by New York City) and cost burden (H3) not supported.
  The exploratory crude-adult re-run corrects the Part 1 E2 education ratio to 1.4×.
- Supported versions: Python 3.11 or later (3.10 reached end of life in October 2026) and SciPy 1.16 or later;
  CI tests Python 3.11-3.13.
- Multi-start optimizers (`census.optim.best_start`, used by the spatial Fay-Herriot fit, the multilevel model
  and the study-only `me_sem_fit`) prefer a converged start whose objective ties the minimum. `me_sem_fit` also
  judges convergence by the projected score, so an ABNORMAL line-search exit at the optimum no longer reports
  a fit as unconverged. This was the long-standing Python 3.10 failure in `test_spatial_lambda_correction`
  (SciPy 1.15: two starts reached the same optimum and the flagged one was 2e-13 lower).

## 0.19.0 (Round 20): public-health determinants

- Age standardization: `census.standardize` with the bundled 2000 U.S. standard population (NCHS/SEER single
  ages, SHA-256 checked, `scripts/update_standard_populations.py`), `standard_weights`, `direct_standardize`
  and the Fay-Feuer interval for age-adjusted rates from counts. Manifest derivation `age_standardized`
  (bands, standard; `create_manifest` fills the weights before hashing; exact replicate SEs).
- `fit_eiv` (`census.models`, manifest method `fit_eiv`, `fit_model` method `eiv`): least squares corrected for
  ACS sampling error in covariates and outcome, including their correlated errors, with error covariances from
  the replicates (Fuller 1987); sandwich SEs, optional `cluster`. Simulation validation in
  `docs/audits/eiv_validation.md` (`scripts/eiv_validation.py`).
- `fit_replicate` reports covariate reliability (overall and per factor group) and notes low or uneven
  reliability, pointing to `fit_eiv` (or regression calibration for GLMs).
- `aggregate_then_derive` collects the codes of `age_standardized` groups.
- Study: `docs/studies/r20_mi_ny_disability_determinants.md` (H1 supported; H2 not supported pooled but clear
  outside New York City, exploratory; H3 not supported, opposite sign; friction log F1-F10).
- PLAN_ROUND_20 also tracks Step 2 (external health data, no API keys needed) and Step 3 (count outcomes).

## 0.18.0 (Round 19): one complete preregistered study

- Manifests: `geography.harmonize_tracts_to` puts tract panels across the 2010/2020
  redraw on one tract vintage (block housing-unit/population weights); Census VRE
  replicates are apportioned through the same crosswalk, giving exact replicate SEs for
  apportioned estimates (`census.tract_harmonization`).
- RPP `areas: "county_metro"` at tract level (a tract takes its county's RPP area).
- `run_manifest` writes the analysed frame and replicates to `<output>/analysed/`, with
  SHA-256s in `run.json`, so follow-up analyses use exactly what the models saw.
- Review fixes: tract harmonization reuses `harmonize_panel`'s GEOID recodes (ACS 2011/2012
  renumberings were missed); unexplained unmatched tracts (`harmonization_incomplete`) and
  replicate/estimate mismatches (`harmonization_mismatch`) are blocking deviations; known
  ACS boundary changes and targets without apportioned rows are recorded; no crosswalk
  downloads when nothing needs apportioning; stricter validation (suffix, concept ids,
  pre-2010 releases, unverifiable codes); a failed analysed-data copy never loses the run.
- First complete preregistered study: `docs/studies/r19_mi_ny_tract_income_change.md`
  (H1 and H3 supported, H2 not supported; run history, friction log F1-F12 and review).
  The review (author self-review at the owner's request) adds an errors-in-variables check
  of H2 (`scripts/r19_review_eiv.py`).

## 0.17.0 (Round 18): metadata integrity

- Verify bundled variable/group archives before use or API fallback, including
  legacy lookups; return metadata-specific integrity failures across interfaces.
- Record consumed JSON hashes, custom-source status and group metadata identity;
  isolate caches by resolved archive root and preserve explicit cache resets.
- Stop manifest execution on corrupt metadata before current-run output, preserve
  typed workflow failures, and extend the stored-input reference workflow checks.
- Keep archived research data and Round 17 model evidence unchanged. No estimator,
  dependency or archive format changes.
- Review fixes:
  - integrity errors are no longer `ValueError`s, so input handlers cannot
    report corruption as a bad argument; every MCP tool translates them to
    `BUNDLED_DATA_INTEGRITY` at registration;
  - manifest analysis ids are checked as portable, case-distinct filenames
    when the manifest is validated, not after every model has run;
  - an occupied output folder is reported as an `output_dir` problem (run_manifest)
    and keeps the completed verification result (verify_proposition);
  - clearing the metadata cache no longer empties dicts callers still hold;
  - the model benchmark accepts omitted arguments for tools with no required
    arguments;
  - the archive cache no longer retains raw bytes; release labels are matched once
    per distinct value.

## 0.16.0 (Round 17): exact claims and bound evidence

- Exact operator-pinned proposition evidence with full digests, reviewed
  formalizations, a small typed matrix rule domain, rational witnesses,
  evidence replay, and opt-in CLI/MCP verification. No new dependencies.
- Preserve ACS1 analysis identity and refuse incompatible five-year replicates;
  reject stale bundle destinations without deleting prior artifacts.
- Correct disattenuation/aggregation input guards, validate model SE signs,
  redact API-key errors, and preserve errata archives on incomplete refresh.
- Run mandatory exact verification tests before tag-triggered publication,
  rejecting missing or skipped required checks.
- Preserve malformed benchmark tool arguments as protocol failures; distinguish
  runtime failures, exhausted tool loops and empty final answers in new results.
- Reject malformed Unicode with typed verification errors; prevent MCP schema
  version coercion and check binding/revocation through the real stdio transport.
- Preflight bundle artifact names to prevent path traversal, writes outside the
  bundle, and case-insensitive filename collisions; preserve valid display labels.
- Include nested `bundle.json` payloads in bundle hashes and reject final figure
  filename collisions before bundle writes, including rendered/copied combinations.
- Add offline frozen-prompt preparation and bound-evidence transcript scoring
  for verification benchmarks, separate from proof authority and live model runs.
- Add injected async verification-client controls for two model phases, shared
  deadlines and replay-checked duplicate suppression; no default model connection.
- Wire an opt-in loopback runtime adapter with verification-only MCP, exact
  model preflight, bounded raw traces and separate declared/observed metadata.
- Archive the Round 17 model study with raw evidence, checksums and replay
  instructions. Preserve primary failures separately from the JSON-mode follow-up.

## 0.15.1 (patch): B01003 total from B01001 for firewall-blocked VRE files

- **`fetch_vre` substitute for the total-population VRE file.** census.gov's firewall
  rejects the 2015-2019 Michigan tract B01003 file for every client (support ID
  13979921158196382640). When a B01003 file is rejected or returns HTTP 404, `fetch_vre`
  now reads line 1 ("Total:") of the B01001 file for the same release, geography and
  state, and relabels it as B01003_001.
  - Only this pair is substituted (`VRE_TOTAL_FALLBACKS`). On the 2015-2019 New York
    tract files the two lines are identical in every cell. A live test
    (`CENSUS_LIVE_TESTS=1`) re-checks this.
  - The substitution is never silent. It issues a warning and is recorded in
    `attrs["substitution"]`: requested URL, reason, the B01001 URL and its SHA-256, and
    the verification. Manifest replicate records and methods text carry it.
  - Other B01003 lines, other tables or failures, `allow_substitute=False`, or an
    unavailable B01001 file still raise the original error. A new `lines=` argument
    keeps only the requested table lines.
- **Michigan 2015-2019 population covariance completed**
  (`docs/audits/acs_sampling_covariance.md`), using the B01001 substitute. Results match
  2020-2024 and New York, so the conclusions are unchanged.
  - Order 1 within county is -0.075 [-0.103, -0.046] (2020-2024: -0.081).
  - Across county it is -0.005 [-0.014, 0.004].
  - The county aggregation ratio is 0.000.
  - Split-half pair reliability is 0.64.

## 0.15.0 (Round 16): spatial methods validated under ACS sampling error

- Project renamed **Census Research Engine** (github.com/cafeTechne/Census-Research-Engine);
  the distribution name `census-acs-toolkit` is unchanged.
- **Lag-model effects:** `spatial_regression(model="lag")` reports direct, indirect and
  total effects first (delta-method and replicate SEs; verified against the S(W) algebra
  and spreg's multipliers), with notes that beta is not the marginal effect and that a
  rho = 0 test is not a specification test. Coverage and a heavy-tail caveat at high rho
  are measured (`docs/audits/spatial_regression_validation.md`).
- **New option `spatial_regression(model="error", correct_outcome_error=True, se_col=...)`:**
  corrects lambda for outcome sampling error using spatial Fay-Herriot (REML). Lambda
  coverage is 0.86-0.93 against 0.003-0.85 uncorrected, measured on the shipped estimator.
  - Assumes errors independent across areas. Warns when errors are correlated, and when
    the outcome is a controlled total, where the sign of the bias depends on the release.
  - Limited to 2,000 areas.
- **ACS sampling-error covariance measured from VRE replicates** (Michigan and New York,
  2015-2019 and 2020-2024; `docs/audits/acs_sampling_covariance.md`):
  - neighbour error correlation is about 0 for rates, shares, medians and most counts;
  - controlled totals are correlated within county, with a sign that can differ by
    release.
- **LISA validation:** under ACS error (`docs/audits/lisa_validation.md`), with no default
  change.
  - The Round 15 "38%" caveat is corrected: it counts maps with at least one significant
    area, not contiguous false clusters.
  - Replicate stability and Fay-Herriot reruns are shown not to be false-positive checks.
- **Common-factor and specification studies:** LR size measured in Juhl's design; Koley &
  Bera score tests shown not to identify SEM vs SDM. All new studies are info-only and
  run on demand.
- **Polite census.gov downloads:** one shared helper (`census/http.py`) with
  - backoff and Retry-After on 429/5xx;
  - per-host pacing;
  - a clear error for the firewall "Request Rejected" page, with the support ID and the
    cache path for a manual download;
  - validation of manually placed files.
- **Literature:** full-text reading notes with verification levels
  (`docs/literature/full_text_reading_notes.md`). Remote-access planner decisions are
  recorded in `docs/remote_access_decisions.md`.
- **CI:** the weekly live-validation cron moved off the hour (Mondays 06:17 UTC).

## 0.14.0 (Round 15): studies across releases, spatial coverage, 2020 Census

- Confirmatory studies across releases: CPI conversion to a declared `dollar_year`, then
  each release's own RPP (`rpp_years`); `"replicates": {"source": "census_vre"}` fetches
  Census VRE tables (URLs and SHA-256 recorded). Overlapping releases are refused for any
  replicate source; `replicate_scope: "covariates_only"` is an explicit, hashed exception
  for outcomes without replicates. Example: MI/NY change in CPI- and RPP-adjusted mean
  household income, 2015-2019 to 2020-2024: +$3,111 per county, 90% CI [2,709, 3,513].
- Spatial coverage studies (info): `spatial_regression_coverage`, `local_morans_size`.
  **Default changes (owner decisions):** the spatial lag model now defaults to GMM (ML rho
  coverage under ACS sampling error was 0.48 at rho 0.3 and 0.003 at 0.6; GMM 0.89-0.90);
  local Moran's I now reads p-values two-sided with 9999 permutations (per-area false
  positive rate 0.20 to 0.10). Previous behaviour: `method="ml"`;
  `sided="folded", permutations=999`. Caveats with measured numbers in both tools'
  outputs (error-model lambda attenuation; false clusters under spatially patterned
  sampling error).
- spreg's per-fit stdout print is suppressed at its source, so it can no longer corrupt
  the MCP stdio stream.
- 2020 Decennial Census: P.L. 94-171 (`dec/pl`) and DHC (`dec/dhc`) through the existing
  pipeline. Counts are "not sample-based (MOE undefined)", never MOE 0, with a
  disclosure-avoidance advisory; sampling tests refuse decennial-only input; ACS vs
  census comparisons treat the count as a fixed reference. New live check F11
  (invariants and block-to-tract/county hierarchy, 5,492 values); 11/11 checks pass live.
- Remote access decisions recorded (`docs/remote_access_decisions.md`); no networking
  changes in this release.

## 0.13.0 (Round 14): confirmatory multi-state analyses

- Pre-registered manifests take several states (`geography.states`, 2-digit FIPS; not
  with ZCTAs), derivations evaluated on replicates, and a declared RPP adjustment step
  (`adjustments`, shared with `place_adjust_frame`; `rpp_year` required, filled in by
  `create_manifest` into `<name>.completed.json` when omitted; exclusions run first;
  RPP provenance recorded). The Michigan/New York study runs confirmatorily
  (`examples/manifests/mi_ny_income_education.json`) and reproduces Round 13 exactly
  (pct_bachelors 811.0, 90% CI [684.3, 937.7]).
- Validation battery adds Michigan (26); all 10 checks pass live and offline.
- PUMS memory measured (`scripts/pums_memory_benchmark.py`, `docs/audits/pums_memory.md`;
  risk R2 closed): peak about 275 MiB + 2.8 KB per person record. Avoidable weight-matrix
  copies removed (1.9M rows: 6.4 to 5.4 GiB peak, results bit-identical); grouped medians
  gather each group once.
- MCP `cache_import` (full profile) with the CLI's safety rules; pandas 4 deprecation in
  `format_dataframe` fixed.
- Review fixes: `run_manifest` records replicate-derivation errors as deviations instead
  of raising; ACS refs with E/PE suffixes match their replicates; methods text reports how
  many units received replicate SEs.

## 0.12.0 (Round 13): real data, end to end

- Live verification: the full battery against Census-published values passes live (10/10
  checks, `docs/audits/validation_report.md`); stale F5 expected-failure marker and
  criterion text fixed (the first dispatched CI live run failed only on that marker).
- Live case study for Michigan and New York counties (`docs/case_study_mi_ny.md`): RPP-adjusted
  median household income, journal maps with an uncertainty layer, a regression with
  replicate refits, a results bundle; CLI only. New tools `place_adjust_frame` (county RPP by
  CBSA membership, applied to estimates, SEs, and replicates) and `make_results_bundle`;
  `build_analysis_frame` takes several input and replicate files; `tool ... --save PATH`.
- The Round 12 reference workflow runs entirely from the CLI: `python -m census cache import`
  (atomic; a synthetic import into the default cache needs `--allow-default-cache`;
  `cache clear` also removes the synthetic marker) and `run_manifest --arg replicates_path=...`
  with Python/CLI/MCP parity tests.
- Provenance: extraction metadata records the observed data source; bundles take it from
  their inputs (`census_api`, `synthetic`, `mixed` with a warning, or `unknown`), not from
  the cache present at bundle time. Failed saved results are refused.
- Bundled price index and RPP tables are verified against their SHA-256 at load (risk R1
  closed); custom tables are recorded with their hash and marked unverified. New error
  code `BUNDLED_DATA_INTEGRITY`.
- Validation: a fast smoke gate (band widened by 3 Monte Carlo SE) runs on pull requests;
  the full gate is a release step and now runs in parallel (`--jobs`), with BLAS pinned to
  one thread, which also makes its results independent of the machine's thread count.
  New info-only study `did_ar1_sensitivity`: DiD coverage stays near nominal under AR(1)
  errors up to rho 0.9 in 4-5 period panels.
- Fixes: map legends stay inside journal-width figures and do not split identifiers;
  `_load_frames` rejects missing GEOID/Year keys; pandas-3 integer replicate columns.

## 0.11.0 (Round 12): verifiable and reproducible workflows

- Independent dense reference checks for the multilevel GLS layer and two-group DiD.
- `scripts/inference_validation.py --gate`; `docs/audits/CHECK_MAP.md`. The gate also
  requires the default multilevel and DiD coverage studies (`multilevel_known_variance`,
  `multilevel_random_slope`, `did_two_group`, `did_event`); replicate-refit and
  serial-correlation variants remain on demand.
- `census.results.interval_description`: every output (tables, figures, methods,
  tool and adapter results) states the same estimand, interval basis, level, and
  distribution; method-aware estimand text (PUMS, DiD, area-level); undefined
  uncertainty shown as undefined.
- `docs/reference_workflow.md`: an offline, rerunnable reference analysis with a
  blocked case, checked by an independent second reader.
- Manifests: `confirmatory_incomplete` for runs with blocking deviations (including
  failed calls); synthetic labels follow the actual data source, with mismatch
  deviations; caller-supplied replicates described and hashed identically across
  pandas/numpy versions; hypothesis results kept in bundles; `run_manifest` tool
  accepts replicates and returns the run status.
- CLI tool runner accepts `--arg KEY=VALUE` (portable paths).

## 0.10.1 (Round 11): audit decisions

- **Q2 incomplete replicates:** `replicate_policy="flag"|"strict"` on replicate-based
  models; pre-registered manifests run strict; exploratory results say when sampling
  SEs may be understated.
- **Q1 DiD serial correlation:** coverage measured under AR(1) area shocks (0.896-0.905
  at rho 0.5 and 0.8, default population target); no estimator added; assumption
  documented in `census.did`, with a not-validated warning for panels over 4 periods.
  The non-default these-areas target is conservative under serial correlation
  (coverage 0.90-0.965).
- **R2 PUMS memory:** measured ~3.6 GB peak at California scale; warning for all-column
  reads of large files.
- **R1 price-data integrity:** documented guarantee (verified at generation and by tests,
  not at each load).
- pandas 3 read-only array fixes in `census.models`, `census.did`, `census.analysis`.

## 0.10.0 (Round 10): microdata, 1-year estimates, research designs; Round 11 audit fixes

- **PUMS microdata** (A, B): `census.pums` tabulations, crosstabs, weighted
  medians, and survey-weighted regression with 80 replicate weights; reproduces
  all 32 Census PUMS verification estimates and SEs for Wyoming (2024 1-year and
  2020-2024 5-year). PUMA boundaries.
- **ACS 1-year** (C): `product="1-year"` across planning and extraction;
  2005-2025 metadata archive (no standard 2020 release); 65,000+ geography checks;
  1-year vs 5-year comparisons refused; product-aware overlap.
- **Designs** (D): `census.multilevel` (Kenward-Roger intervals) and `census.did`
  (non-overlapping periods, full replicate refits); simulation coverage 0.89-0.91.
- **Regional price parities** (E): `census.rpp`, BEA RPPs for states, metro and
  nonmetro portions, and MSAs; never applied by default.
- **Carryovers** (F): ZCTA and place crosswalks, self-contained interactive HTML
  maps, local-model harness tasks for maps and spatial tools.
- **Round 11 audit fixes** (C1-C7 in `PLAN_ROUND_11.md`): undefined PUMS
  replicates no longer report zero uncertainty; zero-weight records no longer move
  weighted medians; spatial replicates are aligned to the estimate's release;
  scalar SE/CV decode Census sentinels; two-group DiD requires a pre-treatment
  reference; regression outputs name the SE behind each interval.
- Concept DOI for citation: [10.5281/zenodo.23925301](https://doi.org/10.5281/zenodo.23925301).

## 0.9.1 (hotfix): Zenodo metadata

- Zenodo archiving: add `.zenodo.json` with an explicit creator name (Zenodo could not build creators from the alias-only `CITATION.cff` author), so releases are archived and receive a DOI. No code changes.

## 0.9.0 (Round 9): geography, maps, spatial inference, data quality, packaging

- **Geography and maps** (workstreams A-E): cartographic and TIGER/Line boundaries
  with vintage-checked joins, static journal maps that report class separability
  and mark low-reliability areas, spatial statistics and models that carry ACS
  sampling error, block-population-weighted crosswalks, block groups and custom areas.
- **ACS errata and user notes** (F): `census.errata` and `data/acs_errata.json`,
  generated by `scripts/fetch_acs_errata.py` from the Census errata and user-notes
  pages (source URL and retrieval date per record). `errata_for(table, years)`
  looks up notes that name a table; `check_urls` confirms every cited note resolves.
- **Controlled-estimate MOEs** (G1): `clean_census_sentinels` now keeps a
  controlled MOE (`-555555555`) as `0` and adds a boolean `<base>_CONTROLLED`
  column (behavior change; `preserve_controlled=False` restores NaN). Validation
  check F1 accepts exactly this representation.
- **Slim core download** (G2): `workflows.download_table(table_code, geography,
  state_code, years, variables, output_dir)` plans, stops if the plan would block,
  then downloads a panel with codebook and SE/CV columns. It replaces
  `batch_download` in the `core` MCP profile (the full profile keeps it). Round 7
  workflow tools return native `summary` and `next_step`; `run_validation`'s
  per-check tally moved from `summary` to `checks_summary`.
- **Tract CV profile** (G3): the simulation tract profile is derived from real
  2023 tract MOEs (`tests/fixtures/cv_profile`, `simulation.derive_cv_profile`)
  instead of an assumed one.
- **Packaging** (H): `pyproject.toml` (`pip install -e .` from a clone, extra `dev`), console
  scripts `census-acs` and `census-acs-mcp`, this changelog, a tag-triggered
  release workflow, and `CITATION.cff` 0.9.0.

## 0.8.0 (Round 8): inference that respects ACS sampling error

Analysis frames with SE columns and replicates; replicate-refit regression
(OLS/WLS/GLM), regression calibration, SIMEX and reliability screening;
Fay-Herriot small-area estimation (reproduces the R `sae` example); power and
minimum detectable differences; GLS trend tests on non-overlapping releases;
correlation matrices; journal figures and tables; preregistration manifests;
MCP tool profiles (`core`, `review`, `full`), recipes, and coverage simulations.

## 0.7.0 (Round 7): derived statistics verified against Census

Proportions, ratios, products, percent changes, aggregation of geographies,
medians from distributions, all with 90% MOEs; Variance Replicate Estimates for
exact variances; batch significance with multiple-comparison corrections; the
F1-F10 validation battery against Census-published values; table-scoped
concordance rules; the 2010/2020 tract crosswalk; nationwide extraction;
extraction replay; C-CPI-U; `CITATION.cff`; continuous integration.

## Round 6: vintage-safe variables and R-CPI-U-RS

Cross-release variable concordance (concept IDs, reviewed overrides, continuity
checks that block unsafe panels), metadata archive per vintage, constant dollars
with R-CPI-U-RS (the Census Bureau's ACS index), and an agent-first interface.

## Round 5: research-grade pipeline

Tidy GEOID x Year panels, Parquet export, codebooks, sentinel cleaning with
notes, SE/CV/reliability columns, inflation adjustment, and a query cache.

## Round 4: MCP server

FastMCP server exposing table search, variable lookup, and batch download to agents.

## Round 3: headless library

The `census` package: API client, geography, tables, export, and statistics
separated from the GUI, with a command-line interface.

## Round 2: research usability

Improvements to the desktop downloader for research workflows (table search,
multi-year batches, output formats).

## Round 1: foundation

Initial stabilization of the original batch downloader.

## Releasing

1. Bump `census/__init__.py` `__version__` (and `PACKAGE_VERSION` in
   `census/pipeline.py`), update this file and `CITATION.cff` (`version`,
   `date-released`).
2. Tag and push: `git tag v0.9.0 && git push origin v0.9.0`. The `Release`
   workflow (`.github/workflows/release.yml`) builds the sdist and wheel, checks
   the tag matches the package version, and creates a GitHub release with both
   files attached.
3. Zenodo: the repository owner enables the repository once in Zenodo
   (Account > GitHub > toggle the repository on). Zenodo then archives every
   published GitHub release and mints a version DOI plus a concept DOI that
   always resolves to the latest version. After the first release, add the
   concept DOI to `CITATION.cff` (`doi:`) and the README badge.

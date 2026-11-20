# Backlog roadmap: repairs and follow-ups after the statistics roadmap (Rounds 43–56)

**Status: drafted 2026-11-19, after v0.39.0 (Rounds 31–42, DOI 10.5281/zenodo.24371310); Rounds 43–50
merged 2026-11-19; Rounds 51–56 (section 5) added and merged 2026-11-19.** The source
from which `PLAN_ROUND_43.md` onward are drafted; it is not itself a plan. **Implementing agents: do not
read this file unless the owner asks; implement only the lowest-numbered `PLAN_ROUND_<n>.md`.** Update
the status column in section 3 when a round merges.

Ground rules carry over from `ROADMAP_STATISTICS.md` section 7: validation first (criterion committed
before the full run), failed methods stay exploratory, each statistical round ends with an exploratory
MI/NY example, MI/NY test states and OH/PA replication states, goldens byte-identical unless a round
says otherwise, no automated WONDER access and no sub-national counts 1–9 in any output.

## 1. Where the backlog comes from

Two sources: the STATUS backlog that predates Round 31 (items 1–7), and issues found while
implementing Rounds 31–42. The second group was never collected in one place; it is below.

## 2. Issues found in Rounds 31–42

| # | Issue | Found in | Kind | Round |
| :--- | :--- | :--- | :--- | :--- |
| N1 | Core-profile MCP instructions grew from 5,953 to 12,480 characters (23 numbered rules); no test bounds them, though the core profile exists for small local models | R31–R42 | usability | 43 |
| N2 | Tool counts in README and STATUS are stale (say 63 full / 14 core; actual 70 / 16, core_spatial 17; a README tree line says 32) | R31–R42 | docs | 43 |
| N3 | `estimate_effect` catches `AttributeError`, which hides engine bugs as "invalid input" | R41 | code | 43 |
| N4 | `impute_and_fit` reruns all 20 imputations once per term (k × 20 fits); same seed so results agree, but wasteful | R42 | code | 43 |
| N5 | The weak-instrument cut-off (corr < 0.3) that sets `validated=False` for 2SLS was never validated: every validation cell had a strong instrument | R41 | validation gap | 47 |
| N6 | Treatment-effect cells let residual confounding from noisy confounders cancel (opposite-sign effects on treatment); robustness to error-prone ACS confounders is untested | R41 | validation gap | 47 |
| N7 | Mediation fails with an error-prone mediator (.69–.72); no corrected alternative | R41 | failed method | 47 |
| N8 | Multiple imputation was validated with one incomplete covariate and no ACS sampling error; multi-variable chained equations and imputation combined with replicate SEs are untested | R42 | validation gap | 47 |
| N9 | Interval-censored Poisson for hidden WONDER counts fails narrowly (.839–.856) because of overdispersion; a censored NB2 likelihood is the obvious repair | R42 | failed method | 45 |
| N10 | Interrupted time-series intervals fail with 20 annual points (OLS, Newey–West, AR(1) GLS: .47–.81); small-sample corrections untried | R42 | failed method | 48 |
| N11 | Poisson HC3 under-covers with strong overdispersion (.81–.87); Round 29's registered mortality models used it | R39 | study caveat | 44 |
| N12 | Correlation intervals (R33) and Cronbach/Feldt α (R36) under-cover under spatial dependence; no spatially robust version | R33, R36 | failed method | 48 |
| N13 | HKSJ meta-analysis validated only for k ≤ 4; DerSimonian–Laird failed; Bland–Altman limits and CCC failed | R37, R38 | failed method | 48 |
| N14 | Statsmodels-based tools (treatment effects, beta, median, count models) take no survey weights; PUMS ordinal, multinomial, weighted-quantile models and GEE were deferred | R40, R41 | missing capability | 49 |
| N15 | Validations are MI/NY-specific (145 counties, the R26 cluster assignment); none of Rounds 31–42 was re-checked on OH/PA | R31–R42 | external validity | 44 |
| N17 | Pooled k-means clusters can straddle adjacent states (OH/PA), leaving a state term partly constant; the engine now flags it, but has no state-respecting option | R44 | missing capability | 45 |
| N18 | NB2 alpha's default optimizer fails on large counts with little overdispersion (real WONDER data); fixed with a Nelder–Mead fallback | R44 | code (fixed) | 44 |
| N19 | Naive IM-8 (Round 30 C1) failed the OH/PA re-check with spatially correlated fields; corrected G1/G2 replicated | R44 | external validity | 45 |
| N20 | 2024 tract VRE files contain negative replicate estimates (B17001: 5 NY counties incl. Bronx, Kings; B19001: Wayne, Bronx, Kings and 2 MI counties); the strict segregation policy refuses those counties | R50 | data / failed input | 51 |
| N21 | Realistic-error segregation was validated on poverty and income groups only; sparse race/ethnicity groups, four or more groups and contrasts untested (the noise gate applies, but structure may differ) | R50 | external validity | 52 |
| N16 | ZIP and beta model-based SEs failed; Kruskal–Wallis passed but rank bootstrap (R34 R3) failed | R34, R39, R40 | failed method (low priority) | closed: validated alternatives (HC0 beta, NB2-HC3, KWW rank intervals) |
| N22 | Binomial regression calibration failed narrowly (.851–.889); no likelihood-based correction tried | R46 | failed method | 53 |
| N23 | Corrected GLM slopes are validated for independent areas only; corrected linear EIV only up to four error-prone covariates | R45, R46 | validation gap | 53 |
| N24 | Rounds 45–48 (count repairs, regression calibration, calibrated causal tools, effective-n intervals) were validated on MI/NY geometry only | R45–R48 | external validity | 54 |
| N25 | Interrupted series below 30 annual points still fail (REML AR(1) .79–.88; bootstrap-t below 30) | R48 | failed method | 55 |
| N26 | SMR intervals treat the reference population as fixed; an ACS-estimated reference denominator (backlog 6) is untested | R24, R28 | validation gap | 55 |
| N27 | No microdata inequality measures (Gini, Theil, Atkinson, percentile ratios) with SDR replicate variance (backlog 6) | R49 | missing capability | 56 |
| N28 | SMR refuses negative band replicates although the expected count is linear in the bands | R24 | code / failed input | 51 |
| N30 | Clipped negative replicates are validated only below noise .50 (Round 51); race-group counties usually have noise above .50 and clipped cells, so 11–32 of 145 MI/NY counties per race design stay exploratory. Rural highs are driven by prison group quarters, which the engine does not separate | R52 | validation gap | not planned |
| N31 | Round 54: naive IM outside MI/NY has no validated repair (4 or 6 within-state clusters failed on OH/PA); G1 with three to five and G2 with five error-prone covariates failed on OH/PA at low reliability with correlated fields; a fresh-seed MI/NY IM-8 rerun covered .849 in one cell; Round 48 effective-n intervals were not re-checked on OH/PA (targets are MI/NY-specific) | R54 | external validity | not planned |
| N29 | IM-8 versions of correlation and α intervals failed; partial correlations under spatial dependence exploratory; PUMS GEE deferred (SDR replicates already carry the design) | R48, R49 | failed method / deferred | not planned |

Pre-Round-31 backlog items (STATUS "Open backlog"): 1 spatial routing and GLM EIV, 2 NB2 for R29,
3 manifest correlation intervals, 4 GLM measurement-error correction, 5 WONDER child-age reference
rule (needs a registered study rule, not a round), 6 realistic-error segregation validation, 7
saturated-model bundle crash.

## 3. Rounds

| Round | Theme | Covers | Status |
| :--- | :--- | :--- | :--- |
| 43 | Manifest routing and housekeeping | backlog 1 (routing), 2 (manifest NB2), 3, 7; N1–N4 | merged (v0.40.0) |
| 44 | Post hoc sensitivity and replication checks | backlog 2 (R29 NB2), N11, N15 | merged (v0.41.0) |
| 45 | Count-model repairs | N9, N17; NB2 with IM-8 clusters; Poisson-offset uncertainty (backlog 1) | merged (v0.42.0) |
| 46 | Measurement-error-corrected GLM slopes | backlog 1 and 4; linear EIV with 3–4 error-prone covariates | merged (v0.43.0) |
| 47 | Causal and missing-data robustness | N5–N8 | merged (v0.44.0) |
| 48 | Small samples and spatial dependence | N10, N12, N13 | merged (v0.45.0) |
| 49 | Survey-weighted PUMS models | N14 | merged (v0.46.0) |
| 50 | Segregation with realistic error | backlog 6 (realistic-error validation, multigroup H) | merged (v0.47.0) |

### Round 43: manifest routing and housekeeping (no new statistics)

Route already-validated methods into manifests as **opt-in** arguments (registered manifests keep
their bytes and outputs: both goldens byte-identical, plus new golden cases for the new options):
validated correlation intervals, `fit_replicate` NB2, `fit_eiv` spatial G1/G2. Fix the saturated-model
bundle crash. Bound and shorten the core-profile instructions (N1), refresh tool counts (N2), and the
two code issues (N3, N4).

### Round 44: post hoc sensitivity and replication

Author self-review, labelled post hoc; registered results unchanged. (a) R29 mortality H1–H3 refit
with NB2-HC3 (and NB2 with IM-8 where Round 45 validates it; otherwise flagged), MI/NY and OH/PA. (b)
R29 with the exploratory interval-censored likelihood as a sensitivity for complete-case dropping
(coefficients only; disclosure audit). (c) Re-run the Round 33, 35 and 39 validation designs on the OH/PA
county geography (fixed seeds, pre-set criterion) to test external validity of the MI/NY results.

### Round 45: count-model repairs

Validate an interval-censored NB2 likelihood for hidden 1–9 counts; NB2 under IM-8 clusters; Poisson and
NB2 with an uncertain (ACS) exposure offset. Compare with complete case and the Round 42 censored Poisson.

### Round 46: corrected GLM slopes

Replicate-informed regression calibration and SIMEX for binomial, Poisson and NB2 covariates, judged
against the error-free slope; extend linear EIV G1/G2 to 3–4 error-prone covariates. Closes backlog 4 if
any procedure passes.

### Round 47: causal and missing-data robustness

Same-sign confounding cells with noisy confounders, plus a corrected-confounder propensity (regression
calibration inside AIPW); weak-instrument cells (first-stage F from 2 to 30) to set a validated cut-off;
an EIV-corrected mediator path; multiple imputation with two incomplete covariates (chained equations)
and with ACS replicate error.

### Round 48: small samples and spatial dependence

ITS: restricted-likelihood AR(1) with t reference, Prais–Winsten with small-sample df, and a residual
(sieve) bootstrap, at 15, 20 and 30 points. IM-8 cluster versions of correlation intervals and α.
HKSJ for k = 5–10, and a Bland–Altman limits repair with replicate-based error variance.

### Round 49: survey-weighted PUMS models

Ordinal and multinomial logit, weighted quantile regression and GEE-style clustered models with SDR
replicate weights (Fay's method), validated by resampling a synthetic population with the PUMS design.

### Round 50: segregation with realistic error

The realistic-error validation the STATUS backlog asks for: heterogeneous tract CVs from real MI/NY
MOEs, non-negative counts, correlated group errors; two-group D/isolation and multigroup H.

## 4. Decisions for the owner (defaults assumed unless changed)

1. Order as above (housekeeping first; it shrinks the agent-facing text before more is added).
2. Round 44's post hoc R29 checks report alongside, never replace, the registered results.
3. Releases: proposed to bundle at milestones (as with v0.39.0); each release still needs the owner's yes.

## 5. Rounds 51–56 (drafted 2026-11-19, after Rounds 43–50)

Same ground rules (section 1 above). Open issues N19–N28 plus the remaining STATUS backlog items 1, 4 and 6.

| Round | Theme | Covers | Status |
| :--- | :--- | :--- | :--- |
| 51 | Negative replicate estimates | N20, N28 | merged (v0.48.0) |
| 52 | Segregation beyond poverty and income | N21 (race/ethnicity groups, 4–5 groups, period contrasts, OH/PA) | merged (v0.49.0) |
| 53 | Corrected GLM slopes, part 2 | N22, N23 (binomial repair, corrected counts under IM-8, 5–6 error-prone covariates) | merged (v0.50.0) |
| 54 | OH/PA external validity, part 2 | N19, N24 (Rounds 45–48 re-checked; naive IM-8 repair outside MI/NY) | merged (v0.51.0) |
| 55 | Short series and estimated reference populations | N25, N26 | merged (v0.52.0) |
| 56 | Microdata inequality measures | N27 | merged (v0.53.0) |

### Round 51: negative replicate estimates

The 2024 VRE files contain negative replicate estimates for small tract cells (B17001: 7 NY rows; B19001:
656 rows). Segregation refuses any county with one; SMR refuses any negative band replicate. Validate, under
Gaussian replicate perturbations that produce negatives at small counts, (a) clipping replicate group counts at
zero for segregation and (b) accepting negative band replicates for SMR when every replicate expected count is
positive (the expected count is linear in the bands). Judge coverage in affected counties and overall.

### Round 52: segregation beyond poverty and income

Round 50's design with real B03002 tract counts and MOEs: two-group race/ethnicity contrasts (e.g. Black vs
all others, Hispanic vs non-Hispanic), four- and five-group Theil H, the difference between two non-overlapping
five-year periods (2015–2019 vs 2020–2024), and the OH/PA counties (B17001 and B03002) for external validity.

### Round 53: corrected GLM slopes, part 2

Round 46's audit shows the binomial failure is in the standard error (RC bias −.016 to −.001, coverage .851–.889),
so the repair is a delete-one-area jackknife SE (≈ HC3) with a t reference rather than a new estimator; regression
calibration combined with IM-8 clusters for Poisson and NB2 under spatially correlated fields; G1/G2 with five
and six error-prone covariates.

### Round 54: OH/PA external validity, part 2

Re-run the geography-dependent designs on OH/PA geometry with fixed seeds and a pre-set criterion: Round 45
IM-8 counts, Round 53 calibrated IM-8 counts, G1/G2 with three to five error-prone covariates (independent-area
designs do not depend on geography; Round 48's effective-n designs need OH/PA reference targets and are left).
Repair naive IM-8 outside MI/NY (N19) with fewer, larger within-state clusters (G = 4, 6), judged on both
geometries.

### Round 55: short series and estimated reference populations

Interrupted series at 15–29 points: the Round 48 bootstrap-t with a bias-corrected AR coefficient, and an
equal-weighted cosine (fixed-smoothing) HAR t test. SMRs whose reference population is itself an ACS estimate (internal and external
standardization) with the reference variance in the combined interval.

### Round 56: microdata inequality measures

Gini, Theil T, Atkinson (ε = 0.5, 1), P90/P10 and P80/P20 ratios and top-decile share from PUMS income with
the SDR replicate variance, and differences between groups or states; validated by resampling a synthetic
population with the PUMS design, as in Round 49.

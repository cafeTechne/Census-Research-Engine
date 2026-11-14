# Round 19: One Complete Study, End to End

**Date:** 2026-11-14
**Status:** Implemented; study awaiting owner review (section 8)
**Baseline:** v0.17.0 (Round 18 plus review fixes)
**Owner role:** independent reviewer of the finished study (section 6)

## 0. Why this round

Since Round 12 the engine has gained the pieces a study needs:
- preregistered manifests, several states, several releases;
- CPI and RPP adjustment;
- Census VRE replicates;
- spatial methods with measured limits;
- exact verification and metadata integrity.

It has never carried a real research question from preregistration to a finished, reviewable result. The county studies in `docs/case_study_mi_ny.md` are **worked examples**: their manifests were registered *after* exploratory analysis of the same data (its Limitations section says so), and they stop at county level.

This round runs one study properly:
- the hypotheses are registered and committed **before** any of the study's data are pulled;
- it runs at **tract** level, where "where did change happen" is answerable;
- it produces a reviewable report;
- every point where the engine gets in the way is logged as evidence for the backlog, in place of speculative proposals.

## 1. The study

**Question.** Between 2015–2019 and 2020–2024, did real household income rise across Michigan and New York neighbourhoods (census tracts), and did it rise more where the share of adults with a bachelor's degree was higher, i.e. did the neighbourhood income–education gradient steepen?

| Item | Choice | Why |
| :--- | :--- | :--- |
| Releases | ACS 5-year 2019 and 2024 | Non-overlapping periods, so the two samples are independent and replicates may be combined (overlap rule) |
| Units | All tracts in Michigan (26) and New York (36), on **2020 tract geography** | 2019 is published on 2010 tracts; it must be harmonized to compare the same areas |
| Outcome | Mean household income = aggregate household income `B19025_001` / households `B19001_001` | Both tables are on the VRE list at tract level, so the outcome has exact replicate SEs (median `B19013` has none) |
| Covariate | Bachelor's degree or higher, % of adults 25+: `B15002` (`_015`..`_018` + `_032`..`_035`) / `_001` x 100 | On the VRE list; standard area-level human-capital measure |
| Prices | R-CPI-U-RS to 2024 dollars, then BEA RPP of the tract's county area (MSA, or the state's nonmetro part), each release's own RPP year | As in case study section 8; county-metro areas need the A3 extension at tract level |
| Replicates | `census_vre`: 80 replicates per release, apportioned to 2020 tracts with the same weights as the estimates (A2) | Exact sampling SE for the apportioned 2019 values |
| Reliability | CV screen at 30% on the outcome, **flag** only | Preregistered: no tract is dropped for noise; sensitivity analysis drops flagged tracts |
| Missing | Complete case (e.g. tracts with no households) | |
| Correction | Holm across all three hypotheses, 90% intervals | ACS convention |

**Hypotheses** (`examples/manifests/r19_mi_ny_tract_income_change.json`):
- **H1** (m1, `mean_hh_income ~ C(Year)`, target `these_areas`): real mean household income was higher in 2020–2024 than in 2015–2019. The estimand is the unweighted mean of tract changes, one-sided `greater`.
- **H2** (m2, `mean_hh_income ~ C(Year) * pct_bachelors + C(state)`, target `conservative`): the cross-tract slope of real mean income on the bachelor's share was steeper in 2020–2024. The test is on the interaction `C(Year)[T.2024]:pct_bachelors`, one-sided `greater`. `conservative` adds model and sampling variance because the claim is about a relationship, not only these tracts.
- **H3** (m3, `mean_hh_income ~ C(Year) * C(state)`, target `these_areas`): the mean tract change differed between New York and Michigan. Two-sided.

**What the authors had seen before registering.** County-level change in mean household income for the same states and releases (case study section 8: +$3,100), and the tract-level structure of ACS sampling-error correlation (Round 16 C1). Neither shows tract-level income change, the tract education gradient, or the state difference. The report states this.

## 2. Engine work the study needs (P0, offline tests first)

**A1. Tract harmonization in manifests.**
- `geography.harmonize_tracts_to: 2020 | 2010`, valid only for `level: "tract"`.
- Estimates of releases on the other tract vintage are apportioned with the existing `census.geo_crosswalk` machinery:
  - block **housing-unit** weights for household/housing tables and population weights otherwise (`weight_for_variable`);
  - per state;
  - targets covered below 99% dropped and reported.
- Validation refuses non-additive variables (medians, percentages): only counts can be apportioned. It also refuses `aggregation` combined with harmonization.
- `run.json`/`bundle.json` record the crosswalk source and hash, the weight type per variable, the notes, and dropped or unmatched tracts. `methods.md` states it.

**A2. Replicate apportionment (the methodological piece).**
- Each of the 80 VRE replicates is a count, so it is apportioned with the **same crosswalk weights** as its estimate. The apportioned replicates then give the exact replicate SE of the apportioned estimate, including the covariance between source tracts that the published-MOE route ignores: `apportion` combines MOEs as sqrt(sum (w*MOE)^2), assuming independence.
- Implement `census.replicate.apportion_replicates` on top of `geo_crosswalk.apportion`, so the arithmetic is shared, not duplicated.
- In `run_manifest`, the 2019 VRE rows are apportioned *before* being matched to the analysis units.
- Self-check, recorded in `run.json`: the apportioned VRE `estimate` column must reproduce the harmonized frame estimate (published values, so rounding-level agreement).
- Offline tests:
  - an apportioned estimate via the replicate path equals `harmonize_panel` exactly;
  - weight-1 targets keep their source replicate SE;
  - under simulated independent replicates, a split target's replicate SE converges to sqrt(sum w^2 SE^2);
  - an end-to-end manifest on a frozen two-state toy crosswalk with network refused.

**A3. County-metro RPP areas for tracts.** A tract lies in one county (GEOID[:5]), so `areas: "county_metro"` is allowed at tract level and maps each tract to its county's RPP area. Validation and the methods text are updated.

**A4. Study outputs outside the tree.** Run outputs (bundle, frames, replicates) are attached to the GitHub release as an archive, not committed. The repository keeps the manifest, the report, small summary tables and the figures. This follows the Round 17 repo-hygiene note.

## 3. Study protocol

1. A1–A3 merged and released (v0.18.0 dev on the branch); full gate green.
2. Write the manifest, `create_manifest` (resolve on), and **commit it alone** (the preregistration commit). Record the commit SHA and manifest hash in this plan and the report. No study data are pulled before this commit.
3. `run_manifest` live with the owner's API key into `studies_output/r19/` (ignored by git).
4. Pre-specified **exploratory** analyses, labelled exploratory with the manifest hash:
   - **E1:** maps of tract change in each state, with CV-flagged tracts hatched or marked.
   - **E2:** local Moran's I of the change (Round 16 defaults: two-sided, 9,999 permutations, BH 0.10), with the Round 16 caveats on heterogeneous sampling variances.
   - **E3:** sensitivity:
     - drop CV-flagged tracts;
     - household-weighted (WLS by households);
     - nominal dollars;
     - state price areas instead of county-metro.
   - **E4:** for apportioned tracts, the replicate SE against the independence-approximation SE. This shows how wrong the approximation is in practice.
5. Report `docs/studies/r19_mi_ny_tract_income_change.md`:
   - question;
   - preregistration (commit, hash, what was seen before);
   - data and provenance;
   - methods;
   - confirmatory results;
   - exploratory results (labelled);
   - limitations;
   - reproduction commands;
   - reviewer checklist.
6. **Friction log** in the report: every workaround, wrong error, slow step or missing tool hit while running the study, each marked fixed-in-round or backlog.

## 4. Acceptance

- Manifest committed before the first study data request (git history shows it).
- `analysis_status` is `confirmatory`, or `confirmatory_incomplete` reported as such with its deviations. A failed or blocked hypothesis is reported, never dropped.
- Every number in the report traces to a bundle file or an exploratory output with its hash.
- A1–A3 have offline tests. Fast gate and full suite pass on Python 3.14 and 3.10 (excluding the known local-only 3.10 spatial λ test, which fails identically on the baseline). CI is green.

## 5. Out of scope

- New estimators;
- spatial regression in the confirmatory set;
- SSH or remote access;
- more verification rules;
- model benchmarking.

The friction log decides what comes next.

## 6. Owner review

The owner reviews the report as independent reviewer: question, preregistration timing, deviations, interpretation, limitations. Review comments go into the report's review section before release.

## 7. Release

v0.18.0 with a Zenodo DOI after `/code-review high`, the fixes, the full gate, and Python 3.10 and 3.14 runs. The study output archive is attached to the release.

---

## 8. Implementation status (2026-11-14)

| Item | Result |
| :--- | :--- |
| A1–A3 | `geography.harmonize_tracts_to`, replicate apportionment (`census.tract_harmonization`), tract `county_metro` RPP areas; offline tests in `tests/test_tract_harmonization.py` and `tests/test_manifest_multistate.py` |
| Preregistration | Manifest SHA-256 `8f205f51…fb126`, committed alone at `3f0b1fe` (2026-11-14T20:33:49Z) and pushed before any study data request |
| Run | `confirmatory`, 0 deviations. The reproduction run gave byte-identical `hypotheses.json`. Apportioned VRE estimates match the apportioned API estimates exactly (difference 0.0) |
| Results | H1 +$3,458 [3,093, 3,824] supported; H2 −$65.6/pp [−122.7, −8.4] not supported (opposite sign); H3 NY − MI +$3,867 [3,232, 4,503] supported |
| Exploratory | Sensitivity agrees across all real-dollar variants. Per-tract change mostly noise (1% significant after BH). Weak global autocorrelation of the change. Replicate SE ≈ independence SE for apportioned tracts (within 1.3%) |
| Friction | F1–F4 fixed in round; F5–F10 backlog (report section 11) |
| Report | `docs/studies/r19_mi_ny_tract_income_change.md` |

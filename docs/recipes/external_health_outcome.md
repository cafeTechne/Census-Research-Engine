# External health outcome (CDC PLACES, USALEEP, County Health Rankings, WONDER)

Goal: a pre-registered study whose outcome comes from outside the ACS, without circularity.

**The rule.** Determinant studies keep using the ACS's own measure as the outcome (for disability: `B18101`), and use external sources for measures the ACS lacks, such as diabetes (PLACES `DIABETES`) or mortality. Never test a model-based outcome against the inputs of the model that produced it.

1. Call `list_health_sources` and read the measure's `kind` and `acs_equivalent`:
   - `acs_equivalent` is set (PLACES `DISABILITY` and the six disability types, `ACCESS2`, `FOODSTAMP`; CHR `v180`): the ACS measures this directly. Use the ACS table as the outcome. The external measure is allowed only in a **measurement comparison**: the model contains the ACS measure and only that term is tested (Round 21 Part 1 design).
   - `kind: "direct"` (CHR mortality `v001`, `v127`, `v147`, ...; WONDER exports): death records, no model inputs. Determinant studies are fine.
   - `kind: "model_based"` (all PLACES measures; CHR `v060` diabetes and other BRFSS measures) or `"partly_model_based"` (USALEEP): read `model_covariate_tables`. Within a county, PLACES varies only with age, sex, race/ethnicity and education composition; USALEEP's predicted death rates come from income, race/ethnicity, education and density. Do not test a term built from those tables. Use them as controls only, or write a `circularity_justification` (20+ characters) on the hypothesis if testing the model's reproduction is the point.
2. Add the outcome to the manifest: `"external": [{"name": "diab", "source": "places", "release": 2025, "measure": "DIABETES"}]`.
   - USALEEP: `{"source": "usaleep", "release": 2018, "measure": "E0"}`. It is on 2010 tracts: use ACS 2011-2019 releases, or add `"apportion_to": 2020` (population-weighted, an approximation). Fully predicted tracts (flag 2) are dropped unless `"include_predicted": true`.
   - County Health Rankings: `{"source": "chr", "release": 2025, "measure": "v127"}` at county level. Non-commercial research use; cite CHR&R.
   - WONDER: export the county table yourself from wonder.cdc.gov (the engine never contacts WONDER; national files are manual too), then `{"source": "wonder", "measure": "age_adjusted_rate", "file": "path/to/export.txt", "sha256": "<sha256 of the file>"}`. Tick the age-adjusted rate standard error. Suppressed counts stay censored (1-9), never zero.
3. Use the external variable only as the outcome of `fit_eiv` (held fixed; ACS covariates corrected for sampling error), `fit_replicate` or `fh_regression`; for area inequality or indirect ratios, follow the `health_inequality` recipe (`inequality` / `smr`). For tract PLACES outcomes, cluster by county: `"args": {"cluster": "GEOID.str[:5]"}` (PLACES shares county random effects).
4. `create_manifest`: errors **R1** (same construct as an ACS measure) and **R2** (tested term from the model's inputs) block. Read the notes: they list overlapping controls and the rule. Commit the manifest alone, then `run_manifest`.
5. In the report, state the source's model (methods.md does), its uncertainty type, the join counts in `run.json` (`external`), and that within-county PLACES variation is composition only.


Count example (CHR 2025 direct natality outcome; ACS determinants are predeclared):

```json
{"id":"m1","method":"fit_replicate","formula":"lbw ~ pov_rate + C(GEOID.str[:2])",
 "args":{"model":"binomial","trials":"lbw_denominator","scale":"robust","target":"population"}}
```

Declare `{"name":"lbw","source":"chr","release":2025,"measure":"v037"}` in
`external`. Use proportions, not percentages. Poisson cross-checks use
`lbw_numerator` with `exposure: "lbw_denominator"` and `scale: "robust"`.
Spatial HAC failed its fixed validation and is exploratory only. To register an
exploratory study, set top-level `exploratory: true`; it remains exploratory even
when deviations block parts of the analysis. USALEEP may opt into `split: "dominant"`
for children holding >=95% of parent population (held-out OH/PA validation passed);
the split default stays `missing`.

For an explicitly selected spatial-cluster fit, follow the restrictions in
`regression_sampling_error`: only IM with eight groups passed, only for OLS/binomial
and population target without analysed ACS replicates. It replaces the ordinary
binomial robust covariance; `scale: robust` and spatial clusters are mutually
exclusive. Do not drop existing ACS uncertainty to force this fit.

**Hidden WONDER counts (Round 42, exploratory).** `census.missing_censored_its.fit_censored_poisson` uses
counties whose counts are hidden as 1-9 as interval information instead of dropping them; it never estimates
or outputs a hidden value. Its interval under-covered slightly (.84-.86): use it as a sensitivity analysis.
Prefer the validated interval-censored NB2 (Round 45): `fit_model(input_path=..., formula="deaths ~ x",
model="negbin", exposure="expected", censored="hidden")`, where `hidden` is true for counts suppressed as 1-9
(their count cell may be empty). Hidden counts enter only as "between 1 and 9"; nothing is estimated for them.

**Overdispersed counts in manifests (Round 43).** `fit_replicate` accepts `"model": "negbin"` for a
`<name>_numerator` outcome with exposure `<name>_denominator`, the same way as Poisson; Poisson HC3
under-covered with strong overdispersion in Round 39, so prefer NB2 for new registrations.

**Round 29 under NB2 (Round 44, post hoc).** All three Round 29 associations hold with NB2-HC3 in MI/NY
and OH/PA (`docs/studies/r44_posthoc_r29.md`), so the Round 39 Poisson caveat does not change them. For
spatial inference outside MI/NY, prefer the corrected-slope `fit_eiv` `spatial` options (replicated on
OH/PA with up to two error-prone covariates, and G2 with up to four; Round 54) or, for counts, IM-8 count
slopes (replicated on OH/PA, Round 54); naive IM-8 failed the OH/PA re-checks with spatially correlated fields,
also with 4 or 6 clusters (Round 54). For naive OLS, Poisson and binomial slopes use SCPC (`spatial="scpc"`, validated on
both regions in Round 58; binomial since Round 62).

**Hidden counts and spatial clustering (Round 45).** Prefer
`census.missing_censored_its.fit_censored_negbin` (validated) to dropping counties whose WONDER counts are
hidden as 1–9; it never estimates or reports a hidden value. For spatially correlated counties,
`fit_model(model="negbin", exposure=..., spatial="clusters")` gives IM-8 slopes (validated on MI/NY; for
adjacent states use `within_states=True` in the library). Holding ACS-based expected counts fixed is fine
for NB2 (validated); Poisson HC3 under-covers.

## Years of potential life lost and unusual years (Round 95; CDC SS1000 lessons 3-5)

- **YPLL from a national WONDER export** grouped by ten-year age groups and sex:
  `demography_analysis(kind="ypll", input_path=path, end_age=75)` (full profile; library
  `census.surveillance.ypll_from_wonder(path, end=75)`) gives the annual YPLL, the crude rate and the age-adjusted
  YPLL rate per 100,000 person-years (2000 US standard over ages below the end point), with a Fay–Feuer interval
  (validated, .888–.963).
  - The end point must be a band boundary (65 or 75).
  - Infants (<1) and ages 1–4 are kept apart.
  - Exports with suppressed cells (1–9 deaths) give bounds only.
- **Area tables:** `demography_analysis(kind="ypll", input_path=..., death_columns=..., population_columns=..., bands=...)`
  (or `ypll_table(...)`) takes band death and population columns. Areas with suppressed bands get bounds,
  never imputed counts.
- **Is the latest year unusual?**
  - `joinpoint(..., aberration="historical_limits")` compares it with the previous 5 years (mean ± 2 SD, adding the
    current year's sampling error). `"ears_c2"` uses a 7-year baseline with a 2-year guard.
  - Both keep false alarms at .005–.016 on flat series (validated).
  - A trend inflates false alarms (to .10 and .24 at 3% a year), so look at the joinpoint segments first.
  - `deviation_chart(...)` draws the CDC-style deviation chart.

## Life tables, life-expectancy decomposition and age-data quality (Round 101; IUSSP Tools for Demographic Estimation)

- **Life tables:** `demography_analysis(kind="life_table", input_path=path)` (full profile; library
  `census.demography.life_table_from_wonder(path)`) builds an abridged life table from a national
  WONDER all-cause export (ten-year bands; <1 and 1–4 separate; 85+ open).
  - e₀ and eₓ come with Chiang II 90% intervals, validated (.895–.910) from 50,000 person-years.
  - `census.demography_core.life_table(starts, deaths, person_years)` takes any banded data.
- **Why life expectancy changed:** `demography_analysis(kind="arriaga", input_path=all1, comparison_path=all2,
  causes=causes1, comparison_causes=causes2)` (library `arriaga_from_wonder`) splits the e₀ change into
  age-band and cause contributions (Arriaga 1984); they add up exactly.
  - Use mutually exclusive underlying causes. Overdose, firearm and alcohol-induced overlap other categories.
  - Suppressed national cells count as 0, and the notes say so.
- **Age-data quality:** `demography_analysis(kind="age_quality", pop_by_age=...)` (or `input_path=...` for PUMS
  with replicate SEs; library `age_quality` / `age_quality_pums`) gives Whipple's and
  Myers' indices and the UN age-sex accuracy index. Uneven birth cohorts raise the UN index without any data error.
- **Census-survival net migration by age** between two censuses: `demography_analysis(kind="survival_migration",
  pop1=..., pop2=..., life_table_L=...)` (library `census_survival_net_migration`, descriptive).


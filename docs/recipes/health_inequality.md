# Area health inequality and indirectly standardized ratios

1. Choose an area-level question. Register a manifest before inspecting associations;
   use `exploratory: true` when reusing an outcome association already examined.
   These indices describe area associations, not individual inequality or causal effects.
2. For `inequality`, declare `outcome`, `rank_by`, positive population `weights`, and
   `args.higher_is_more_deprived` explicitly. Rank areas from least to most deprived;
   tied values share their weighted mid-ridit. External outcomes are allowed, with
   `weights: "<outcome>_denominator"` for their published denominator (for example live births).

   ```json
   {"id":"ineq","method":"inequality","outcome":"lbw","rank_by":"pov_rate",
    "weights":"lbw_denominator","args":{"higher_is_more_deprived":true,"target":"conservative"}}
   ```

3. Hypotheses name `sii`, `log_rii`, or `concentration_index`, without a `term`.
   SII is the WLS slope on ridit; log RII is log((intercept+slope)/intercept),
   undefined if either fitted endpoint is nonpositive. Positive indices mean higher
   outcomes among more deprived areas. **Concentration has the reverse sign of the
   usual income-ranked convention.** Outcome proportions give SII in proportion units;
   multiply SII and both limits by 100 for percentage points. Exponentiate log RII
   and its limits for the relative index (`ratio` columns do this).
4. Declare ACS VRE replicates for noisy ranks, weights or outcomes. Every refit
   recomputes weighted ridits; declared external outcomes and external denominators
   stay fixed. Missing stochastic-variable/area replicates are refused. Population
   intervals use HC3; `these_areas` uses sampling SE only; default `conservative`
   combines both by quadrature. External outcomes cannot use `these_areas`.
   Median rank CV <=15% is the validated range. Above it, estimates may be
   attenuated by rank error; wider intervals do not correct that bias. HC3 assumes
   independent areas and does not cover spatial residual dependence.
5. For `smr`, use observed **integer counts**, `population_bands` (distinct manifest
   variables), positive `reference_rates` in **events per person-year**, in the same band
   order, and a non-empty `reference_source` citation. Convert rates per 100,000
   to per person-year before registration. Set positive integer `period_years` (default 1)
   to the study count period: E=period_years*sum(population*annual_rate). Use a
   representative annual/period-average population, not summed person-years, when
   multiplying by period_years. Source, rates and period are hashed. Optional
   `reference_counts` gives the positive integer reference deaths behind each rate,
   one per band, and is also hashed; zero reference deaths are refused.

   ```json
   {"id":"smr","method":"smr","observed":"deaths_numerator",
    "population_bands":["pop_young","pop_old"],"reference_rates":[0.001,0.02],
    "reference_source":"Named standard, years, age bands; annual deaths per person-year",
    "period_years":5,"reference_counts":[500,2000],
    "args":{"target":"conservative"}}
   ```

6. Test `statistic: "log_smr"` with `geoid` equal to one GEOID or `"all"` (pool
   counts and expected counts first). The null is log SMR=0; ratio columns show
   SMR and its combined limits. Exact Garwood limits condition on fixed expected
   counts. Tests use Poisson variance plus ACS expected-count replicate variance;
   only `target: "conservative"` is supported. Without replicates, expected-count
   uncertainty is zero and explicitly noted. At zero observed counts, the combined
   test is undefined; report the exact fixed-E interval only. Reference-rate
   uncertainty is excluded unless `reference_counts` is supplied. With it, add
   sum_b (E_b/E)^2/D_b to log variance, treating reference person-years as known.
   Reference rates stay fixed during ACS refits. For pooled studies, sum band
   contributions before squaring: the same reference rates are shared across
   counties. Do not average per-county variances as if they were independent.
   If study areas are included in the reference, ignoring the positive covariance
   makes the interval conservative; this is noted, not refused. Reference
   denominators' uncertainty and spatial dependence remain excluded. Negative ACS
   band replicates are used as published (Round 51 validated; the expected count is
   linear in the bands); every replicate expected count must be positive. Registered
   manifests refuse them unless `args.negative_replicates` is `"accept"` or `"clip"`.
   No age-specific real death-count example is bundled;
   WONDER exports remain manual.
7. Circularity R1 applies to external outcomes/counts. R2 treats `rank_by` as the
   tested term for inequality; model-input overlap requires the existing written
   justification. Read the methods, diagnostics and join counts, and report
   unadjusted interval confidence separately from multiplicity-adjusted tests.

Reproducible validation: `docs/audits/inequality_validation.md` and
`docs/audits/smr_validation.md` and `docs/audits/smr_reference_validation.md`.
The new reference procedure passed 0.8995–0.9105 coverage in its fixed six-cell
study (50/500/5000 reference deaths per band, E=10/100, band CV .05). That does
not establish coverage for very sparse reference deaths or arbitrary covariance. Exploratory MI/NY example:
`examples/manifests/r24_mi_ny_lbw_inequality.json`.


Round 29 manual WONDER references: all county and national files are manual
exports; the engine never contacts WONDER. `acs_age_sex_bands` builds the fixed
20-band B01001 order (male youngest–oldest, then female). `smr` may replace literal
rates/counts with `reference_export: {file, sha256}`; `period_years` must match the
footer. Optional `ages_under: 75` selects the registered under-75 standard.
National suppressed reference cells are refused after dropping Not Stated;
state references require explicit `state` registration and are refused at runtime
if suppressed. No invented reference counts. `expected_count` derivations use
the same population bands, pinned reference and period, including ACS replicates.
Poisson offsets remain fixed during regression refits; reference-aware SMR
combined intervals provide the separate sensitivity, not corrected slope inference.
Matched suppressed outcomes are distinct from unmatched GEOIDs and unsuppressed
missing outcomes. Complete-case regressions/SMRs exclude suppressed counties,
record county IDs and [n,9n] excluded-death bounds. EB is descriptive only.
WONDER outputs: no sub-national counts 1–9 or values derived from them; no raw
exports in the repo or releases. Keep study states only, omit national death-count
vectors/complementary totals, mask censored counties in every product and run
`census.wonder_outputs.audit_outputs` before packaging. Sensitivity endpoint
assignments stay internal and output coefficients only; they are not strict bounds.

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
   variables), positive `reference_rates` in **events per person**, in the same band
   order, and a non-empty `reference_source` citation. Convert rates per 100,000
   to per person before registration. Source and rates are hashed with the manifest.

   ```json
   {"id":"smr","method":"smr","observed":"deaths_numerator",
    "population_bands":["pop_young","pop_old"],"reference_rates":[0.001,0.02],
    "reference_source":"Named standard, year, age bands; annual deaths per person",
    "args":{"target":"conservative"}}
   ```

6. Test `statistic: "log_smr"` with `geoid` equal to one GEOID or `"all"` (pool
   counts and expected counts first). The null is log SMR=0; ratio columns show
   SMR and its combined limits. Exact Garwood limits condition on fixed expected
   counts. Tests use Poisson variance plus ACS expected-count replicate variance;
   only `target: "conservative"` is supported. Without replicates, expected-count
   uncertainty is zero and explicitly noted. At zero observed counts, the combined
   test is undefined; report the exact fixed-E interval only. Reference-rate
   uncertainty is not included. No age-specific real death-count example is bundled;
   WONDER exports remain manual.
7. Circularity R1 applies to external outcomes/counts. R2 treats `rank_by` as the
   tested term for inequality; model-input overlap requires the existing written
   justification. Read the methods, diagnostics and join counts, and report
   unadjusted interval confidence separately from multiplicity-adjusted tests.

Reproducible validation: `docs/audits/inequality_validation.md` and
`docs/audits/smr_validation.md`. Exploratory MI/NY example:
`examples/manifests/r24_mi_ny_lbw_inequality.json`.

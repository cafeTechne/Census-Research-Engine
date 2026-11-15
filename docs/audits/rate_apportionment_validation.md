# Rate apportionment from 2010 to 2020 tracts: validation

Generated 2026-11-15 16:30 UTC by `scripts/rate_apportionment_validation.py`. PLAN_ROUND_21 Part 2, C2 (the method behind USALEEP `apportion_to: 2020`).

States 26, 36. ACS 2015-2019 crude disability prevalence (B18101, all ages, 2010 tracts) apportioned to 2020 tracts with `census.health_sources.apportion_rates` (2010 block population masses; targets below 90% covered mass left missing), compared with ACS 2016-2020 on native 2020 tracts. z = (apportioned - native) / sqrt(se_a^2 + se_n^2). The two releases share four sample years, so |z| is smaller than for independent samples; the test compares relationship types.

Apportionment record: 8253 targets, 9 below coverage, 1147 from several sources, 1593 source tracts split across targets.

| target type | n | median abs z | share abs z > 1.645 | mean difference (points) | correlation |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 1:1 | 5433 | 0.487 | 0.025 | +0.02 | 0.902 |
| merged/complex | 1131 | 0.513 | 0.039 | -0.03 | 0.823 |
| split | 1626 | 0.647 | 0.093 | -0.22 | 0.738 |

Ratios of median |z| to the 1:1 targets: split 1.33, merged/complex 1.05.

**Acceptance** (each ratio at most 1.25): **FAILED**.

**Consequence (engine default).** `apportion_rates(split="missing")`, the default for USALEEP `apportion_to`, leaves split targets missing; `split: "inherit"` keeps the parent's value and is documented as not validated. The validated part (1:1 and merged/complex targets) passes.

**Post hoc** (not part of the pre-specified test; added after it failed): split targets by the share of the parent's population they hold.

| parent share | n | median abs z | share abs z > 1.645 |
| :--- | ---: | ---: | ---: |
| 0.95 or more | 496 | 0.472 | 0.032 |
| 0.5 to 0.95 | 541 | 0.665 | 0.096 |
| below 0.5 | 589 | 0.766 | 0.143 |

Reading: a split tract inherits its parent's rate, so its apportioned value misses the within-parent difference between children; merged targets average their sources by population. If those errors were large next to sampling error, split and merged targets would show larger |z| than 1:1 targets. For life expectancy the approximation is cruder still (e(0) is not additive), so USALEEP values on 2020 tracts remain an approximation, stated in every methods text that uses them.

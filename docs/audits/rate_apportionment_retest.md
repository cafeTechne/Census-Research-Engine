# Held-out split-tract apportionment re-test (Round 22)

**Pre-registered hypothesis:** split targets that hold at least 95% of their parent tract's 2010 population behave like 1:1 targets. Held-out states: Ohio (39), Pennsylvania (42). Criterion: high-share split median |z| / 1:1 median |z| <= 1.25. The script and hypothesis were committed before this run; registration commit is recorded below.

**Acceptance: PASSED**. Parent share >= 0.95: n=499, median |z|=0.461130, 1:1 median=0.505183, ratio=0.912797 (fixed limit 1.25).

Consequence: add opt-in split=dominant for parent share >=0.95; default remains missing.

Pre-run script/hypothesis commit: `d8ad3600d3d7edc6f58da2304bef3dea89f42180`. Other parent-share bands below are descriptive; they do not change the decision.

Generated 2026-11-15 20:39 UTC by `scripts/rate_apportionment_validation.py`. PLAN_ROUND_21 Part 2, C2 (the method behind USALEEP `apportion_to: 2020`).

States 39, 42. ACS 2015-2019 crude disability prevalence (B18101, all ages, 2010 tracts) apportioned to 2020 tracts with `census.health_sources.apportion_rates` (2010 block population masses; targets below 90% covered mass left missing), compared with ACS 2016-2020 on native 2020 tracts. z = (apportioned - native) / sqrt(se_a^2 + se_n^2). The two releases share four sample years, so |z| is smaller than for independent samples; the test compares relationship types.

Apportionment record: 6566 targets, 0 below coverage, 1172 from several sources, 1450 source tracts split across targets.

| target type | n | median abs z | share abs z > 1.645 | mean difference (points) | correlation |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 1:1 | 4033 | 0.505 | 0.030 | -0.04 | 0.873 |
| merged/complex | 1169 | 0.518 | 0.034 | +0.07 | 0.895 |
| split | 1353 | 0.626 | 0.094 | -0.10 | 0.757 |

Ratios of median |z| to the 1:1 targets: split 1.24, merged/complex 1.03.




| parent share | n | median abs z | share abs z > 1.645 |
| :--- | ---: | ---: | ---: |
| 0.95 or more | 499 | 0.461 | 0.030 |
| 0.5 to 0.95 | 400 | 0.680 | 0.098 |
| below 0.5 | 454 | 0.860 | 0.161 |

Reading: a split tract inherits its parent's rate, so its apportioned value misses the within-parent difference between children; merged targets average their sources by population. If those errors were large next to sampling error, split and merged targets would show larger |z| than 1:1 targets. For life expectancy the approximation is cruder still (e(0) is not additive), so USALEEP values on 2020 tracts remain an approximation, stated in every methods text that uses them.

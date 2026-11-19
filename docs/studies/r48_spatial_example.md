# Round 48 exploratory example: Round 29 correlations corrected for spatial dependence

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r48_spatial_example.py` reads the verified Round 29 bundles (MI/NY and OH/PA)
and the cached 2020 county boundaries, with HTTP blocked.

**Disclosure.** The WONDER disclosure audit passed in both regions, and only coefficients are output.
The outputs are archived at `/tmp/r48_example_outputs.tar.gz` (sha256 `0b44cde8…db512bdd`).

**What is computed.**
- Spearman correlations of county poverty with the log SMRs. Counties whose counts are hidden or zero
  are dropped pair by pair.
- Each correlation gets two 90% intervals: the Round 33 interval, which assumes independent counties,
  and the Round 48 effective-sample-size interval.

| Region | Outcome | n | ρ | Independent | Spatial | n_eff |
| :--- | :--- | ---: | ---: | :--- | :--- | ---: |
| MI/NY | H1 premature, all causes | 145 | 0.588 | (0.487, 0.673) | (0.470, 0.685) | 109.1 |
| MI/NY | H2 drug overdose | 132 | 0.272 | (0.129, 0.404) | (0.123, 0.408) | 122.7 |
| MI/NY | H3 heart disease | 145 | 0.392 | (0.265, 0.505) | (0.256, 0.512) | 126.9 |
| OH/PA | H1 premature, all causes | 155 | 0.761 | (0.697, 0.813) | (0.649, 0.842) | 58.8 |
| OH/PA | H2 drug overdose | 152 | 0.554 | (0.451, 0.643) | (0.394, 0.682) | 69.5 |
| OH/PA | H3 heart disease | 155 | 0.524 | (0.417, 0.616) | (0.370, 0.650) | 79.6 |

**Effect of the correction.** Spatial dependence shrinks the effective sample by up to 62%. The loss
is largest in OH/PA, where 155 counties carry the information of about 60–80 independent ones. Every
interval widens, but none reaches zero.

**Internal consistency of the three log SMRs** (Feldt α; this is not a deprivation index):

| Region | α | Independent interval | Spatial interval | n_eff |
| :--- | ---: | :--- | :--- | ---: |
| MI/NY | 0.706 | (0.624, 0.772) | (0.578, 0.800) | 59.8 |
| OH/PA | 0.829 | (0.785, 0.865) | (0.735, 0.894) | 40.8 |

**Limits.**
- The correlations are between ACS estimates as observed, so they are attenuated by sampling error.
- They describe association only.
- The effective sample size assumes a stationary spatial correlation across the region.

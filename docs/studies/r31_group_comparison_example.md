# Round 31 example: county poverty by metro class, Michigan and New York (exploratory)

**Exploratory; author self-review, not independent. Not registered.** The example shows that
`compare_groups` works as intended on real data; it is not a confirmatory finding.

## Data

- ACS 2018–2022 county poverty rate (B17001) and the share aged 65+ (B01001), with all 80 VRE
  replicates, for the 145 MI/NY counties. Read from the v0.26.0 release attachment
  `r29_study_outputs.tar.gz` (ACS columns only; checksums verified against its `run.json`). No
  WONDER data are used.
- Groups from CBSA membership (2024 CBSA file, OMB 2023 delineation; committed fixture
  `tests/fixtures/mi_ny_manifest/cbsa_membership.csv`): **large metro** (counties in a
  metropolitan CBSA whose MI/NY counties total 1 million+ people; 28 counties), **other metro**
  (39) and **nonmetro** (micropolitan or outside any CBSA; 78). Groups are a fixed published
  classification, not cut points of a noisy estimate.
- Reproduce: `scripts/r31_group_comparison_example.py r29_study_outputs.tar.gz OUT_DIR`.

## Results

Poverty rate (%), 90% intervals; conservative target (model + ACS sampling error).

| Group | One-way mean (90% CI) | ANCOVA mean, adjusted for share 65+ (90% CI) |
| :--- | :--- | :--- |
| Nonmetro | 13.9 (13.3–14.5) | 14.3 (13.6–14.9) |
| Other metro | 12.6 (11.7–13.5) | 12.3 (11.4–13.2) |
| Large metro | 11.6 (10.0–13.1) | 10.9 (9.5–12.4) |

| | One-way | ANCOVA |
| :--- | :--- | :--- |
| Joint test (wild score bootstrap, validated for OLS factor tests) | p = 0.010 | p = 0.005 |
| Nonmetro − large metro | −2.3 points (−4.0 to −0.7); Holm p = 0.061; simultaneous p = 0.051 | −3.3 (−4.9 to −1.7); Holm p = 0.002 |
| Nonmetro − other metro | −1.3 (−2.3 to −0.2); Holm p = 0.091; simultaneous p = 0.108 | −2.0 (−3.2 to −0.8); Holm p = 0.011 |
| Large metro − other metro | +1.0 (−0.7 to 2.8); Holm p = 0.33 | +1.3 (−0.3 to 3.0); Holm p = 0.18 |
| Partial η² / ω² (descriptive) | 0.069 / 0.055 | 0.107 / 0.093 |

Differences are "first group minus second" as printed. Brown–Forsythe residual spread by group:
p = 0.14 (information only). Holm and simultaneous intervals are both validated for OLS; the
simultaneous adjustment is slightly stricter for the nonmetro–other-metro pair, as expected.

**What a small local model sees** (the guided MCP result):

> Joint test of poverty across 3 groups of metro_class: p = 0.01 (validated); 2 of 3 pairwise
> differences significant (holm). Next step: report the joint test, then the pairwise differences.

## Spatial check

The IM-8 version (`spatial=True`) is **unavailable**: some of the eight fixed MI/NY clusters
contain no large-metro county, so the group effect cannot be estimated within every cluster and
the engine refuses rather than dropping clusters. This is the same limit the validation found for
designs with many or clustered groups. The non-spatial p-values above therefore assume
independent counties, which spatial dependence can make too small.

## Limits

- Exploratory: groups and covariate were chosen for illustration, not pre-registered.
- Counties are treated as independent (see the spatial check).
- The share aged 65+ has sampling error; the ANCOVA adjustment uses the ACS estimates as observed,
  so the adjusted differences can be slightly biased.
- Areas, not people: county poverty rates are unweighted by population.
- Outputs: `r31_example_outputs.tar.gz` (results JSON and the ACS-only frame and replicates;
  key-scanned), attached to the release.

# Residential segregation within counties

1. Register the tract coverage, releases, mutually exclusive group definitions and
   hypotheses before examining results. Use tract geography. Select counties through
   existing extraction/exclusion controls; `within: "county"` computes each county
   separately from the first five digits of its eleven-digit tract GEOIDs. Do not
   pool counties into an undeclared area or call this a metro/CBSA index.
2. Declare at least two ACS count variables in `groups`. Their sum defines each
   tract's population. Dissimilarity and isolation require exactly two groups;
   isolation describes **group one**, so group order matters. Theil H supports
   multiple groups; bias-corrected three-group H passed Round 50, while four or more
   groups and naive multigroup H are exploratory.
   Do not use overlapping race/ethnicity categories, rates, medians or percentages
   as group counts; the engine cannot infer mutually exclusive definitions.
3. Supply all 80 ACS VRE replicates for every declared group and tract, either
   through the existing VRE source or an explicit Year-labelled replicate file.
   Missing rows/groups/columns, negative full-sample counts and undefined refits are
   refused. Negative **replicate** group counts (small 2024 tract cells) are set to
   zero before the index refits by default (`negative_replicates="clip"`, Round 51);
   the count SEs and noise level use the unclipped replicates. Manifests keep the
   strict refusal unless they set `args.negative_replicates: "clip"`. Do not clip
   anything else, silently keep missing groups fixed, or discard
   failed refits. Zero-total tracts contribute nothing in the full-sample index;
   totals are recomputed in every replicate. An absent county group makes the
   index undefined, with a note, and its hypothesis is not tested.

   Analysis fragment:

   ```json
   {"id":"seg","method":"segregation",
    "groups":["group_one","group_two"],"within":"county","replicates":"required"}
   ```

4. Choose `dissimilarity`, `isolation` or `theil_h`. Since Round 50 every default is
   **bias-corrected**: naive D failed under realistic ACS error (it was the Round 28
   default).
   Correction is I-4(mean(Ir)-I); the factor four accounts for the replicate
   deviations' quarter sampling variance. The same raw-replicate SE is used for
   both variants. `args.bias_correction: true/false` overrides all indices in that
   analysis; a variant with no validated range requires `exploratory: true`. Naive D
   is validated only in the Round 28 range (every tract CV <= .15); naive isolation
   and H only at noise levels .15-.30. Inspect each
   output row's `validated` field and notes; unregistered auxiliary indices are
   not confirmatory hypotheses.
5. A one-county hypothesis requires a finite **pre-registered `null_value`**:

   ```json
   {"id":"H1","analysis":"seg","statistic":"dissimilarity",
    "geoid":"26001","null_value":0.2,"direction":"two-sided"}
   ```

   For a difference, add `compare_geoid` (another five-digit county GEOID). The
   estimate is first county minus comparison; the default contrast null is zero.
   Within-release SE uses each replicate difference before squaring, preserving
   shared ACS replicate structure. It does not assume county errors independent.
   One-sided tests center on estimate minus null, not on the sign of the index.
6. With multiple releases, hypotheses must specify `release`. A cross-release
   difference additionally gives `compare_release`; omit `compare_geoid` to compare
   the same county across years. Each release needs its own Year-labelled replicates.
   Only non-overlapping five-year periods are allowed (release gap >=5); their
   variances add, instead of pairing replicate labels across independent samples.
   County/release self-comparisons are refused.
7. Report the definitions, selected variant, sampling SE and unadjusted confidence
   interval, alongside multiplicity-adjusted hypothesis tests. Corrected points
   and normal intervals are **not clipped** to [0,1]. These describe segregation
   among the observed tracts, not causal effects or superpopulation uncertainty.
8. **Validated range (Round 50).** The realistic-error validation used the real
   2024 MI/NY tract counts and published MOEs (poverty: two groups; household
   income: three groups), non-negative Gamma counts and replicates, and correlated
   group errors. Each row reports the county's **noise level** (`noise_level`: the
   largest, over groups, of the median tract CV from the replicates; a zero count
   has infinite CV). A row is validated when the noise level is below .50 for
   bias-corrected D (from .15), isolation and H (two or three groups), or below .30
   for naive isolation/H (from .15), with at least five populated tracts. The Round
   28 range (every tract CV <= .15, `max_count_cv`) also still validates. Otherwise
   rows are exploratory and confirmatory hypotheses are refused
   (`hypothesis_not_tested`). With 2024 poverty or income groups, 132 of 140 MI/NY
   counties are validated (the rest have under five tracts). Race and ethnicity groups,
   which are sparser, were not in the validation: check their noise level, and treat
   counties above .50 as exploratory. A county with a negative replicate estimate in
   any tract (2024: the Bronx, Kings, Wayne and seven others) is estimated with clipped
   replicates (Round 51) and validated in the same noise range for the bias-corrected
   versions only (`clipped_replicates` > 0); naive isolation and H with clipped cells
   failed and are exploratory. Contrasts
   have covariance checks but no separate coverage experiment. Wider intervals
   are not a remedy for an unsupported error model.

Existing manifest tools execute this recipe; no new MCP tool is needed.
Python entry points are `census.segregation_indices(counts)` and
`census.segregation_replicate(frame, groups, replicates)`; the latter retains
raw replicate indices for contrasts. Preserve leading-zero GEOIDs and explicit
release labels. See `docs/audits/segregation_validation.md` (criterion `4791763`) and
`docs/audits/segregation_realistic_validation.md` (Round 50, criterion `686d121`).
References: Duncan & Duncan (1955), ASR 20:210–217; Massey & Denton (1988),
Social Forces 67:281–315; Reardon & Firebaugh (2002), Sociol Methodol 32:33–67.

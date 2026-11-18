# Residential segregation within counties

1. Register the tract coverage, releases, mutually exclusive group definitions and
   hypotheses before examining results. Use tract geography. Select counties through
   existing extraction/exclusion controls; `within: "county"` computes each county
   separately from the first five digits of its eleven-digit tract GEOIDs. Do not
   pool counties into an undeclared area or call this a metro/CBSA index.
2. Declare at least two ACS count variables in `groups`. Their sum defines each
   tract's population. Dissimilarity and isolation require exactly two groups;
   isolation describes **group one**, so group order matters. Theil H supports
   multiple groups computationally, but three-or-more-group H is exploratory only.
   Do not use overlapping race/ethnicity categories, rates, medians or percentages
   as group counts; the engine cannot infer mutually exclusive definitions.
3. Supply all 80 ACS VRE replicates for every declared group and tract, either
   through the existing VRE source or an explicit Year-labelled replicate file.
   Missing rows/groups/columns, negative counts and undefined refits are refused.
   Do not clip negative counts, silently keep missing groups fixed, or discard
   failed refits. Zero-total tracts contribute nothing in the full-sample index;
   totals are recomputed in every replicate. An absent county group makes the
   index undefined, with a note, and its hypothesis is not tested.

   Analysis fragment:

   ```json
   {"id":"seg","method":"segregation",
    "groups":["group_one","group_two"],"within":"county","replicates":"required"}
   ```

4. Choose `dissimilarity`, `isolation` or `theil_h`. Defaults follow the fixed Round
   28 coverage result: **naive D**, **bias-corrected isolation**, **bias-corrected H**.
   Correction is I-4(mean(Ir)-I); the factor four accounts for the replicate
   deviations' quarter sampling variance. The same raw-replicate SE is used for
   both variants. `args.bias_correction: true/false` overrides all indices in that
   analysis; a failed variant requires `exploratory: true`. In particular,
   corrected D and naive isolation/H failed the fixed criterion. Inspect each
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
   The fixed validation used two groups, 20/100 tracts and group CV .15, with
   independent Gaussian count errors. CV .30 performed poorly, largely because
   negative draws/refits were invalid; it is not a validated extension. Contrasts
   have covariance checks but no separate coverage experiment. Wider intervals
   are not a remedy for an unsupported error model.

Existing manifest tools execute this recipe; no new MCP tool is needed.
Python entry points are `census.segregation_indices(counts)` and
`census.segregation_replicate(frame, groups, replicates)`; the latter retains
raw replicate indices for contrasts. Preserve leading-zero GEOIDs and explicit
release labels. See `docs/audits/segregation_validation.md` (criterion `4791763`).
References: Duncan & Duncan (1955), ASR 20:210–217; Massey & Denton (1988),
Social Forces 67:281–315; Reardon & Firebaugh (2002), Sociol Methodol 32:33–67.

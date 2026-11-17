# Round 27 compatibility review

Author self-review, not independent. Base: `74dddf2` (merged Round 26).
Both snapshot tools ran before and after the implementation. Snapshot artifacts
remain in `/tmp`; the tools' normalization rules were not changed.

- `scripts/refactor_golden.py`: 516 snapshots from 12 manifests. Thirty string
  occurrences changed, all supported-statistics errors for deleted hypotheses'
  statistics: `hypotheses[0]`, `[1]` or `[2]`, each ending in
  `statistic None not available from fit_replicate (supported: ('coefficient', 'joint_wald'))`.
  The former supported tuple was `('coefficient',)`. No other schema difference.
- `scripts/run_golden.py`: 29 offline scenarios covering all 19 blocking deviation
  kinds. Seventy-eight added diagnostic fields (six fields in 13 returned model
  records) and 55 dependent artifact-digest occurrences changed. The fields are
  `sampling_covariance`, `joint_model_covariance`,
  `joint_model_covariance_estimator`, `joint_has_replicates`, `joint_full_rank`
  and `joint_columns`. Covariance serialization retains both axes' term labels.
- All pre-existing numerical estimates, SEs, confidence intervals, test statistics,
  p-values, hypothesis decisions, input/manifest hashes, existing diagnostics,
  methods prose and other artifacts compared equal, treating NaN as equal to NaN.
  The only changed digest paths refer to model-result JSON, bundle JSON/reference
  digests and the variant-result JSON containing the same added metadata.

The plan's requirement that *only* error messages differ is incompatible with its
requirement to expose full covariance in output diagnostics. Under section 0.6,
additive metadata and its dependent digests are the least-change exception.
No normalization was added to either golden tool to conceal those additions.
Existing non-spline coefficient model-SE conventions are retained. Joint tests
use explicitly labelled HC3; spline coefficient model SEs also use HC3.

The fixed validation kernels are separate from delivery code, so pre-run commits
can be reproduced independently. Tests compare the frozen EB kernel to production
(including bootstrap quantiles), and compare the joint experiment's batched OLS
and binomial coefficients, full HC3 and 80-refit sampling covariance against
production statsmodels refits. Additional WLS/Poisson reference tests cover
weights/exposure handling. These are computational checks, not additional claims
of successful inferential validation.

The map helper already accepts arbitrary numeric columns, including `eb_ratio`.
Its regression check confirms values survive rendering and no ACS MOE is invented.
The plan refers to `census/figures` map helpers; the actual helper is
`census.maps.choropleth`. No new mapping subsystem was needed.

# Pool replications, test equivalence, plan power

1. **Pool** several estimates of the same effect (e.g. the same coefficient in MI/NY and OH/PA):
   `combine_estimates("pool", estimates=[...], ses=[...])`. The default (Paule-Mandel with the
   Hartung-Knapp interval) is validated for up to 10 estimates (from 5 on, the variance factor is truncated
   at 1; Round 48); with 2 it is valid but very wide.
   Fixed-effect pooling is validated only if you declared, before seeing results, that the studies
   share one effect (`assume_homogeneous=True`). DerSimonian-Laird is not validated.
2. Pooling states is a new analysis: register it, or label it exploratory. It never changes what a
   registered study found.
3. **Equivalence:** to claim two estimates are practically the same, set a margin in advance and use
   `combine_estimates("equivalence", estimates=[a, b], ses=[sa, sb], margin=...)` (TOST). A
   non-significant difference is not evidence of equivalence.
4. **Power:** `combine_estimates("power", se=..., effect=...)` gives the power of a two-sided z test,
   and the minimum detectable effect at 80% power. Use planned SEs from MOEs (SE = MOE/1.645).
5. Validation: `docs/audits/evidence_validation.md` (Round 38).

## Heterogeneity, prediction, influence and moderators (Round 102; Harrer et al. 2021)

- Every pooled result now reports a **Q-profile interval for τ²** (validated, .889–.953). Report τ², I² and that
  interval together; the Q test alone says little with few estimates.
- **Prediction interval** for one more estimate (another state or release) is reported but **exploratory**: it
  under-covered (.76–.89) at moderate heterogeneity.
- `leave_one_out=True` re-pools without each estimate. Use it to show whether one state drives the result.
- `moderators=[...]` (one value per estimate; **10 or more estimates**) adds a meta-regression with Knapp–Hartung
  intervals and a permutation p-value. It is exploratory: intervals .82–.92; permutation p kept its size (≤ .10).
- `small_study_test=True` (10 or more estimates) gives Egger's test, which is exploratory (size up to .12 with high
  heterogeneity). Pooled area estimates are not publications, so read asymmetry as size-related heterogeneity.


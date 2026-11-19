# Pool replications, test equivalence, plan power

1. **Pool** several estimates of the same effect (e.g. the same coefficient in MI/NY and OH/PA):
   `combine_estimates("pool", estimates=[...], ses=[...])`. The default (Paule-Mandel with the
   Hartung-Knapp interval) is validated for up to 4 estimates; with 2 it is valid but very wide.
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

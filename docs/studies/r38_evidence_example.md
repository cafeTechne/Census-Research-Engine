# Round 38 example: pooling Round 29's two replications (exploratory)

**Exploratory; author self-review, not independent.** Pooling MI/NY with OH/PA is a new analysis,
not a reinterpretation of Round 29's registered results. Inputs: the registered poverty
coefficients (log mortality ratio per percentage point of poverty) and their conservative SEs from
the v0.26.0 attachment. Reproduce: `scripts/r38_evidence_example.py r29_study_outputs.tar.gz OUT_DIR`.

| Outcome | MI/NY | OH/PA | Pooled, HKSJ (validated) | Pooled, fixed effect | I² | Equivalent within ±0.01? |
| :--- | :--- | :--- | :--- | :--- | ---: | :--- |
| Premature deaths | 0.0270 (0.0055) | 0.0350 (0.0048) | 0.032 (0.006 to 0.057) | 0.032 (0.026 to 0.038) | 18% | not shown (p = .39) |
| Drug overdose | 0.0384 (0.0152) | 0.0588 (0.0049) | 0.054 (−0.002 to 0.109) | 0.057 (0.049 to 0.065) | 38% | not shown (p = .74) |
| Heart disease | 0.0132 (0.0060) | 0.0228 (0.0041) | 0.019 (−0.011 to 0.049) | 0.020 (0.014 to 0.025) | 43% | not shown (p = .48) |

- With two replications the validated random-effects interval is very wide (t on 1 degree of freedom),
  so it excludes zero only for premature deaths. The fixed-effect interval is far narrower, but it is
  valid only if the two state pairs share one effect, which would have to be declared in advance; the
  moderate I² values make that assumption doubtful.
- No pair is shown to be equivalent within ±0.01: the replications agree in direction, but the data
  cannot show they agree in size.
- Planning: MI/NY's SE for premature deaths gives a minimum detectable effect of 0.014 at 80% power
  (two-sided α = .10); for overdose, 0.038, so a third replication should expect to detect only
  effects of that size or larger.

Limits: exploratory; within-pair counties are not independent of space (Round 30); two studies.

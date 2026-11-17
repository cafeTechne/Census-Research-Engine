# Round 26 post hoc spatial-cluster re-checks

**Post hoc; author self-review, not independent. Registered results are unchanged.**

Only IM with eight clusters passed the fixed validation (coverage 0.886–0.912). IM requires population-only inference and refuses analysed inputs with ACS replicates. Both registered studies have those replicates; Round 21b also uses EIV, outside the validated model families. **The requested IM comparisons are unavailable under the retained protocol. No clustered p-values or claims that hypotheses still hold are manufactured.**

## R21B

Registered m2 residual Moran's I: **0.195464**, permutation p=0.0010, n=145; queen contiguity, row standardized, 999 permutations (seed 20261126).

| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM? |
|:---|---:|:---|:---|
| H1 (m1: pov_rate) | 2.61919e-18 | unavailable | not assessed |
| H2 (m2: no_vehicle) | 0.947005 | unavailable | not assessed |
| H3 (m2: cost_burden) | 0.474521 | unavailable | not assessed |
| H4 (m3: asdp) | 7.16656e-27 | unavailable | not assessed |

Reason: the registered method is EIV, and analysed inputs have ACS replicates.

## R22

Registered m2 residual Moran's I: **0.183552**, permutation p=0.0010, n=144; queen contiguity, row standardized, 999 permutations (seed 20261126).

| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM? |
|:---|---:|:---|:---|
| H1 (m1: pov_rate) | 2.65109e-12 | unavailable | not assessed |
| H2 (m2: cost_burden) | 0.00498352 | unavailable | not assessed |
| H3 (m2: no_vehicle) | 0.923584 | unavailable | not assessed |

Reason: analysed inputs have ACS replicates; the IM population-only procedure cannot incorporate them.

## Additional authorized OLS sensitivity for Round 21b

**Exploratory, unclustered OLS; not an EIV correction and not a substitute for the unavailable IM re-check.** This uses the exact cached formulas and complete cases, keeps the external outcome fixed during ACS covariate refits, and retains all cached ACS replicates with conservative combined SEs. Holm adjustment uses the original hypothesis family. Measurement-error bias and residual spatial dependence remain. The original EIV outputs are unchanged.

| Hypothesis | Registered EIV Holm p | OLS conservative/ACS Holm p |
|:---|---:|---:|
| H1 (m1: pov_rate) | 2.61919e-18 | 1.88407e-16 |
| H2 (m2: no_vehicle) | 0.947005 | 0.86784 |
| H3 (m2: cost_burden) | 0.474521 | 0.559973 |
| H4 (m3: asdp) | 7.16656e-27 | 2.02491e-26 |

## Scope and artifacts

The cluster map is a release attachment (`im8_cluster_map.png` / `.pdf`), showing the frozen validation geometry; it does not imply an IM estimate was available for either registered study. The map and computed outputs are in `/tmp/round26-study-outputs.tar.gz`, not committed datasets.
No sources were downloaded. Cached analysed-file SHA-256 values and registered manifest hashes were checked; original files were not modified. Supporting an ACS-compatible spatial re-check or EIV/Poisson inference requires separate validation.

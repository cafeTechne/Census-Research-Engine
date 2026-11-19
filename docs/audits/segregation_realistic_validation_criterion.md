# Round 50: pre-set criterion (segregation under realistic ACS error)

**Frozen before the full run:**
- `scripts/segregation_realistic_validation.py` and `census/segregation.py`, whose `_indices` is used
  as is.
- The truth file `docs/audits/segregation_realistic_counts.csv.gz`, built from the cached 2024 API
  responses by `scripts/segregation_realistic_counts.py`. The build is byte-reproducible.
- This document.

**Truth.** The 2024 five-year tract counts of MI and NY (8,414 tracts, 145 counties), with
SE = published MOE / 1.645.
- **Two groups:** below poverty (B17001_002) vs at or above (B17001_031).
- **Three groups:** households with income below $35k, $35k–99,999 and $100k or more (B19001 bands
  summed; their SEs combined in quadrature).

Counties with fewer than five populated tracts are excluded and listed (8). The target is each county's
index on the true counts.

**Observation model.**
- **Observed count:** a Gamma draw with mean = truth and SD = SE.
- **Replicates:** each of the 80 is a Gamma draw with mean = the observed count and SD = SE/2, so that
  4/80 · Σ(r − x)² estimates SE², as for ACS replicates.
- **Dependence:** both draws use a Gaussian copula with equicorrelation ρ between the groups of a tract.
- **Rounding:** draws are rounded to whole counts, as ACS estimates and replicates are.
- **Zeros:** a zero truth or a zero observed count stays zero in every replicate, as an ACS zero (no
  sample cases) does.

**Cells.** {two groups, three groups} × ρ ∈ {0, −.3}; 2,000 draws per cell, run in chunks of 250. Draw d
of cell c uses `default_rng([20270801 + c, d])`.

**Procedures.** Each index uses the engine's formulas: SE = √(4/80 · Σ(I_r − I)²); the bias-corrected
estimate is I − 4(mean I_r − I), with the same SE; the interval is normal at 90%.
- **Two groups:** D, isolation (of the below-poverty group) and Theil's H, each naive and bias-corrected.
  All six are judged separately.
- **Three groups:** multigroup H, naive and bias-corrected.

**Noise level.** A county's noise level is the largest, over groups, of the median tract CV of that
group: published SE / true count over tracts with a positive total, with a zero count giving CV ∞. The
bins are [0, .15), [.15, .30), [.30, .50) and [.50, ∞). The pre-run tally (counties per bin) is
0 / 88 / 49 / 0 for two groups and 9 / 117 / 11 / 0 for three groups.

**Acceptance.**
- A bin is judged when it has ≥ 5 counties.
- It passes when, in both ρ cells, (a) mean county coverage ≥ .86 and (b) at least 90% of its counties
  cover ≥ .80.
- The validated range runs from the lowest bin up to the first failing judged bin. Unjudged bins below
  the first judged bin are included; an unjudged bin after a judged one ends the range.
- Failed draws (undefined index or replicate) count as non-coverage.
- The engine default for each index is the variant with the widest validated range. Ties go to the
  Round 28 default.

**Changes made after the 40-draw smoke runs, before freezing.**
- **Replicate SD.** The plan said SD = SE, which makes the 4/80 formula estimate 4·SE² (SE/SD 2–4).
  It is now SE/2.
- **Rounding.** Draws are rounded to whole counts: a first-stage draw of about 1e−301 gave a replicate
  Gamma shape that underflowed to 0 (NaN).
- **Judging.** All six two-group variants are judged, not only the Round 28 defaults. The smoke run
  suggested naive D may fail where bias-corrected D does not.

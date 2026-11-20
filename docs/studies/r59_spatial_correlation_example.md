# Round 59 exploratory example: OH/PA county correlations with the spatial correction

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r59_spatial_correlation_example.py` uses Round 54's frame: cached 2024 county B17001, B19013 and
B23025 for Ohio and Pennsylvania, 155 counties, ACS only. Coordinates are Round 44's representative points.
Outputs are archived at `/tmp/r59_example_outputs.tar.gz` (sha256 `1e4eb350…1abfd70`).

## Results (90% intervals)

| Correlation | Independent areas | Effective n (spatial) | n_eff |
| :--- | :--- | :--- | ---: |
| Spearman, child poverty and unemployment | 0.48 (0.37 to 0.58) | 0.48 (0.36 to 0.59) | 137 |
| Spearman, child poverty and log income | −0.68 (−0.75 to −0.60) | −0.68 (−0.77 to −0.56) | 78 |
| Spearman, unemployment and log income | −0.36 (−0.47 to −0.23) | −0.36 (−0.48 to −0.21) | 125 |
| Partial (Pearson), child poverty and unemployment given log income | 0.37 (0.25 to 0.48), exploratory | 0.37 (0.22 to 0.51), exploratory | 95 |

## Findings

- Child poverty and log income are spatially clustered, so their effective sample size is about half the 155
  counties (78). The spatially corrected interval is about 50% wider than the independent one. Since Round 59 that
  interval is validated on OH/PA as well as MI/NY.
- The partial correlation of child poverty and unemployment given income stays clearly positive with the spatial
  correction. Here it is exploratory only, because the validated partial interval needs ACS replicates and no OH/PA
  county replicate files are cached.

## Limits

Correlations of ACS estimates as observed (attenuated by sampling error); descriptive.

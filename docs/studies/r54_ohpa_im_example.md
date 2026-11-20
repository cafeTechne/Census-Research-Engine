# Round 54 exploratory example: OH/PA county child poverty with IM using 4, 6 and 8 clusters

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r54_ohpa_im_example.py` reads cached 2024 five-year county API responses for Ohio and
Pennsylvania (155 counties; fetched with the owner's key for this round): B17001 (child poverty rate, percent),
B19013 (median household income) and B23025 (unemployment rate, percent). ACS only; no WONDER data. Outputs
are archived at `/tmp/r54_example_outputs.tar.gz` (sha256 `9e9f1700…19fec9ea`).

**Model.** OLS of the child poverty rate on log median income and the unemployment rate (naive slopes on the
ACS estimates as observed). Uncertainty is shown four ways:
- HC3, with a PA term;
- naive IM with 4, 6 and 8 clusters (t(G − 1)). The 4 and 6 clusters are within-state; the 8 clusters are
  Round 44's state-respecting assignment. The state term is absorbed by the clusters.

## Results (90% intervals)

| Method | Log income | Unemployment (per point) |
| :--- | :--- | :--- |
| OLS, HC3 | −18.5 (−21.6 to −15.5) | 1.41 (0.82 to 1.99) |
| IM, G = 4 | −17.8 (−21.7 to −13.9) | 1.25 (−0.14 to 2.63) |
| IM, G = 6 | −18.6 (−22.1 to −15.2) | 1.08 (−0.07 to 2.23) |
| IM, G = 8 | −18.6 (−21.4 to −15.8) | 1.22 (0.47 to 1.97) |

## Findings

- The income slope is large and stable under every method.
- The unemployment slope's interval depends on the cluster count: with 4 or 6 clusters it includes zero, with
  8 it does not.
- **None of the IM intervals is validated on OH/PA.** IM-8 under-covered there with spatially correlated fields
  in Round 44. IM with 4 or 6 within-state clusters also under-covered in Round 54, with worst cells at .827 and
  .753, although it covered on MI/NY. On OH/PA these intervals are descriptive only; HC3 ignores spatial
  dependence altogether.
- The validated routes for OH/PA in this setting are the corrected-slope estimators (G1/G2 with at most two
  error-prone covariates, or G2 with up to four). They estimate the error-free slope, a different estimand from
  the naive slope here.

## Limits

Cross-sectional and descriptive. Income and unemployment carry ACS error, so the naive slopes are attenuated.
Child poverty is the ACS's own measure, so the circularity rule is respected.

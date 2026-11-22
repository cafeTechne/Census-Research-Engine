# Round 84 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round84`, branch `phase84/epi-measures`; defaultBranch
(Rounds 82–83) merged in, so the criterion commit `c5f6266` (tag `criterion-r84`) stays an ancestor. Version 0.80.0.

## Behaviour changes

- `fit_model` gains `marginal`, `marginal_values` and `dose_levels` (binomial with trials only); `pums_regression`
  gains `marginal` (logit only). Without them nothing changes. No new tool (76); goldens expected byte-identical.

## Exceptions

1. **No manifest statistics** (`marginal_rr`, `marginal_rd`, `paf`, `dose_trend`). The plan added them if the area
   quantities passed (they did), but manifest binomial results do not carry the frame and trials the
   g-computation needs; this needs a result-object change and is left for a later round (tool and library now).
2. **`trend_test(kind="dose_response")`** became `fit_model(dose_levels=...)`: the dose-response test needs the
   fitted model, and trend_test takes release estimates only.
3. **Default contrast**: without `marginal_values` the exposure's 25th and 75th percentiles are compared.

# Round 31 omnibus-test validation: pre-set criterion

Frozen with `scripts/omnibus_validation.py` and `census/omnibus.py` before the full run
(PLAN_ROUND_31 sections 1–2). Nothing below changes after this commit.

## Candidates

- **W0** χ²(q) Wald with HC3 + 4/80 replicate covariance (Round 27; comparison only).
- **W1** the same W/q against F(q, n − p).
- **W2** HC2 + replicate covariance, W/q scaled by (ν − q + 1)/ν against F(q, ν − q + 1); ν from the
  Hotelling-T² (HTZ) approximation with each area its own cluster, under the working model.
- **W3** restricted score statistic with a Rademacher wild score bootstrap (399 draws).
- **W4** Hotelling T² on the eight fixed MI/NY cluster estimates (Round 30 C1, naive target),
  F(q, 8 − q).
- **P1** Holm-adjusted pairwise t(n − p) tests; **P2** max-|t| simultaneous tests by Monte Carlo
  (20,000 draws, seed `SeedSequence([20261218, 31])`).

## Design

- 145 MI/NY counties; coordinates and the k = 8 assignment from `docs/audits/im_acs_beta_star.json`.
- Fields: independent, and Gaussian with exponential correlation, range 100 km (Round 22 generator).
- Groups fixed per cell: (spatial field + independent noise)/√2, split into equal-sized groups.
- Designs and tested columns: `oneway4` (q = 3), `oneway6` (5), `ancova4` (3; covariates with
  reliability 0.7, generated independently of the groups), `twoway` 2 × 3 interaction (2),
  `spline3` (3) and `spline5` (5) centered natural splines (patsy `cr`, full-sample knots frozen in
  replicates; covariate reliability 0.85). Every design includes an NY indicator.
- Models: linear (outcome with sampling error, reliability 0.85, replicates), binomial and Poisson
  (external outcomes; trials and expected counts as Rounds 22 and 30).
- 36 cells (model × design × field). 2,000 null and 500 alternative draws per cell. Cell seed
  `20261218 + cell`; replicate RNG `SeedSequence([20261218, cell, draw, 7])`; bootstrap RNG
  `SeedSequence([20261218, cell, draw, 9])`.

## Acceptance

- Per candidate × model × design family (factor: `oneway4`, `oneway6`, `ancova4`, `twoway`;
  spline: `spline3`, `spline5`): nominal-.10 null size within [.07, .13] in every judged cell.
  W0–W3 are judged on independent cells; W4 on all applicable cells.
- A failed fit counts as a rejection. For W4, a design the engine refuses before fitting (a tested
  term constant in some clusters, so groups are missing from a cluster) is **not applicable**; cells
  with fixed groups are either always or never applicable. A family with no applicable cell fails.
- Pairwise (P1, P2), per model: familywise error at .10 ≤ .13 under the global null in the
  independent `oneway4` and `oneway6` cells, using HC3 + replicate covariance.
- Selection: per model and family, the simplest passing non-spatial candidate (W1, then W2, then
  W3); W4 separately where it passes. Size at .05, power and spatial-cell sizes of W0–W3 are
  informational.

# Round 63 demonstration: a 17-point interrupted series

**Status: demonstration with simulated input; not a data example and not a study. Author self-review, not
independent.**

**Input.** `scripts/r63_demonstration.py` simulates one 17-point annual series with a fixed seed: AR(1) errors with
φ .5, a level change of 1 and a slope change of .2, and the interruption at point 9. Outputs are archived at
`/tmp/r63_example_outputs.tar.gz` (sha256 `5e2407c0…6fc9746c`).

## Results (90% intervals)

| Method | Level change | Slope change | Validated at 17 points |
| :--- | :--- | :--- | :--- |
| `bootstrap_t_cons` (Round 63) | 0.14 (−1.04 to 1.31) | 0.354 (0.156 to 0.577) | yes (17+) |
| `bootstrap_t_bb` (Round 63) | 0.14 (−1.01 to 1.17) | 0.354 (0.151 to 0.574) | no (19+) |
| `bootstrap_t_bc` (Round 55) | 0.14 (−1.04 to 1.31) | 0.354 (0.166 to 0.577) | no (20+) |
| `reml` | 0.14 (−0.84 to 1.12) | 0.354 (0.157 to 0.551) | no |

## Reading it

- Only the conservative bootstrap-t is validated at 17 points.
- Its intervals are never narrower than the Round 55 method's. Here they differ only at the slope's lower end, where
  the t(12) floor is wider than the bootstrap quantile.
- The level-change interval contains the true value 1, but the estimate is far from it: one short series is noisy.

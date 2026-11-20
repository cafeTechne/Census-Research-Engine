# Round 60 exploratory example: Michigan earnings and income inequality with the repaired intervals

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** Round 56's script (`scripts/r56_pums_inequality_example.py`) re-run with the Round 60 engine on the cached
2019–2023 Michigan person file (HTTP blocked). Outputs are archived at `/tmp/r60_example_outputs.tar.gz` (sha256
`76e203d6…051c9b18`).

## What changed since Round 56

| Measure | Earnings 25–64 (191,811 records) | Income 25+ (369,184 records) | Validated now |
| :--- | :--- | :--- | :--- |
| Atkinson (ε = 1) | 0.359 (0.356–0.362) | 0.382 (0.380–0.384) | yes (logit interval) |
| Atkinson (ε = .5) | 0.179 (0.177–0.180) | 0.199 (0.197–0.200) | yes (≥ 7,000 records) |
| Top-decile share | 0.329 (0.327–0.331) | 0.370 (0.368–0.371) | yes (≥ 7,000 records) |
| Theil T | 0.378 (0.374–0.382) | 0.432 (0.429–0.436) | no (exploratory) |

The Gini, the quantile ratios and the Gini difference are unchanged from Round 56. The earnings P90/P10 is still
flagged for heaped dollar amounts.

## Findings

- With state-sized samples, the logit-transformed intervals are almost identical to Round 56's normal intervals.
  The repair matters in small domains: a county's or a subgroup's few thousand records. There, Atkinson .5 and the
  top share stay exploratory below 7,000 records.
- The top 10% of Michigan adults aged 25+ received 37% of personal income (zero incomes included).

## Limits

Person-level measures without an equivalence scale; Theil T remains exploratory.

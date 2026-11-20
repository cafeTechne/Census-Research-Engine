# Replication B: Census Bureau state Gini index (B19083) from PUMS

**Status: registered numeric replication (criterion `dd48bf6`, deviation 1 at `d30d7ed`; the deviation did not
touch B). Author self-review, not independent.** Audit: `docs/audits/r66_numeric_replication.md`.

## Target

The Census Bureau's published household-income Gini index (B19083) for ACS 2019–2023, with its margin of error,
for 12 states fixed in advance: WY, VT, DE, NM, MS, AZ, GA, MI, NY, TX, CA, NC. Census computes it from the full
internal ACS sample.

## Our estimate

- 2019–2023 PUMS housing records: households only, with `HINCP` adjusted by `ADJINC`;
- household weights with the 80 replicate weights;
- the engine's `pums_inequality` Gini and its validated 90% interval;
- negative incomes set to 0 (primary; the secondary analysis drops them).

## Result: replicated

| Rule (fixed in advance) | Result |
| :--- | :--- |
| Median absolute difference ≤ .005 | .0008 |
| Interval contains the published value in ≥ 10 of 12 states | 10 of 12 |

Our Gini is lower than the published one in 9 of 12 states (mean difference −.0008), the direction predicted in
advance. PUMS top-codes the highest incomes and is a subsample of the internal file, which compresses the top of
the distribution slightly. The two misses are the largest-sample states, California (−.0011) and North Carolina
(−.0018), where the interval is narrowest relative to that small bias.

## What this establishes

The PUMS inequality method reproduces the Census Bureau's own published Gini to within about one thousandth.
For small and medium states, its intervals contain the published value. For the largest states, the
top-coding bias is comparable to the interval width; reports for such states should say so.

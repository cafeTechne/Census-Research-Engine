# Round 66 numeric replications A and B

Criterion commit: `d30d7ed`.

## A. CHR 2025 county Black/White dissimilarity

- Counties compared: 2055 (ours only: 0; CHR only: 0).
- Median |difference|: 0.0000 points; within 1 point: 1.0000; largest: 0.0000.
- Counties more than 2 points apart: 0.
- **Outcome: replicated** (pre-set: median <= 0.5, share within 1.0 >= 0.9).
- Interval part (descriptive; B03002 non-Hispanic groups, VRE replicates): 563 counties, 308 validated.

## B. Census state Gini (B19083) from PUMS

| State | Published (MOE) | PUMS Gini (90% CI) | Difference | Contains |
| :--- | :--- | :--- | ---: | :--- |
| 56 | 0.4483 (0.0089) | 0.4459 (0.4396-0.4521) | -0.0024 | True |
| 50 | 0.4522 (0.0053) | 0.4527 (0.4469-0.4584) | +0.0005 | True |
| 10 | 0.4495 (0.0057) | 0.4503 (0.4439-0.4567) | +0.0008 | True |
| 35 | 0.4774 (0.0034) | 0.4759 (0.4723-0.4795) | -0.0015 | True |
| 28 | 0.4840 (0.0033) | 0.4843 (0.4813-0.4872) | +0.0003 | True |
| 04 | 0.4624 (0.0023) | 0.4616 (0.4594-0.4638) | -0.0008 | True |
| 13 | 0.4779 (0.0020) | 0.4770 (0.4753-0.4788) | -0.0009 | True |
| 26 | 0.4639 (0.0015) | 0.4632 (0.4617-0.4647) | -0.0007 | True |
| 36 | 0.5152 (0.0015) | 0.5139 (0.5124-0.5153) | -0.0014 | True |
| 48 | 0.4765 (0.0014) | 0.4760 (0.4749-0.4772) | -0.0005 | True |
| 06 | 0.4887 (0.0009) | 0.4876 (0.4867-0.4885) | -0.0011 | False |
| 37 | 0.4760 (0.0017) | 0.4742 (0.4726-0.4758) | -0.0018 | False |

Median |difference| 0.0008; contained 10 of 12; mean difference -0.0008. **Outcome: replicated** (pre-set: median <= 0.005, contained >= 10).

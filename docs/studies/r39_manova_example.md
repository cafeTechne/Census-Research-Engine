# Round 39 example: poverty and age structure by metro class, MANOVA (exploratory)

**Exploratory; author self-review, not independent. Not registered.**

Data: the Round 31 example frame (145 MI/NY counties, ACS 2018–2022 poverty rate and share aged 65+,
with replicates; metro classes from the 2024 CBSA file). Reproduce:
`scripts/r39_manova_example.py r31_example_outputs.tar.gz OUT_DIR`.

| | Nonmetro | Other metro | Large metro |
| :--- | ---: | ---: | ---: |
| Poverty rate (mean of counties) | 13.9% | 12.6% | 11.6% |
| Share aged 65+ | 23.3% | 19.2% | 17.4% |

- **Joint test** of metro class on both outcomes (multivariate wild score bootstrap, validated):
  p = 0.0025. Pillai's trace (iid, comparison only) is 0.35 with p ≈ 3 × 10⁻¹¹: ignoring sampling
  error and using the normal-theory F makes the evidence look far stronger.
- Per outcome (Round 31 joint tests): poverty p = 0.010; share 65+ p = 0.0025, with all three pairs
  different after Holm.
- The joint test is the right first step when several outcomes are compared: it controls the error
  rate before the per-outcome tests.

The count-model part of the round (negative binomial) has no example here: the natural one, death
counts, belongs to registered studies under the WONDER rules.

Limits: exploratory; counties treated as independent.

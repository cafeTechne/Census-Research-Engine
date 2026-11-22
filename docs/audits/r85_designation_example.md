# Round 85 example: designating Michigan tracts with poverty of at least 20% (2019-2023 ACS)

Exploratory; author self-review, not independent. 2884 tracts; expected number truly at or above 20%: 608. Probabilities are Fay-Herriot posteriors (validated); expected accuracy is exploratory.

| Rule | Designated | Expected sensitivity | Expected specificity | Expected PPV | Expected NPV |
| :--- | ---: | ---: | ---: | ---: | ---: |
| point | 682 | 0.870 | 0.933 | 0.776 | 0.964 |
| lower | 314 | 0.493 | 0.994 | 0.954 | 0.880 |
| prob50 | 579 | 0.796 | 0.958 | 0.837 | 0.946 |
| prob80 | 373 | 0.574 | 0.990 | 0.937 | 0.897 |

Tracts whose status differs between the point rule and the probability-.8 rule: 309. Tracts with a point estimate at or above 20% but a probability below .5 of truly being there: 103.

# Round 27: empirical-Bayes rate interval validation

Area-averaged 90% coverage >= 0.86 in every gamma cell and both lognormal CV .15 cells, separately for posterior and laird_louis.

Pre-run criterion: `d4dec47`. 1,000 draws/cell; 200 hyperparameter bootstrap refits/draw.

Passed: posterior **True**, Laird–Louis **True**. Default: `posterior`.

| n | Truth | CV | Posterior coverage | Laird–Louis coverage | Lowest-E posterior / LL | MSE EB / raw (uncensored) | Suppressed share | Failures |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 145 | gamma | 0.15 | 0.88379 | 0.87503 | 0.87714 / 0.86831 | 0.013022175747789796 / 0.07244795973940478 | 0.2425 | 0 |
| 145 | gamma | 0.3 | 0.89365 | 0.88500 | 0.89059 / 0.88066 | 0.027392758780588534 / 0.06096807149685658 | 0.2957 | 0 |
| 145 | lognormal | 0.15 | 0.88130 | 0.87183 | 0.87728 / 0.86541 | 0.013971339056858 / 0.0703037752477043 | 0.3039 | 0 |
| 145 | lognormal | 0.3 | 0.89615 | 0.88757 | 0.89417 / 0.88528 | 0.02926589411361555 / 0.07105429283578008 | 0.2783 | 0 |
| 1000 | gamma | 0.15 | 0.89721 | 0.88815 | 0.89509 / 0.88611 | 0.013230526155811674 / 0.0634373706478192 | 0.2703 | 0 |
| 1000 | gamma | 0.3 | 0.89973 | 0.89091 | 0.89932 / 0.89067 | 0.026926517431350206 / 0.06579026485513707 | 0.2794 | 0 |
| 1000 | lognormal | 0.15 | 0.90002 | 0.89137 | 0.90111 / 0.89257 | 0.01314928757746942 / 0.06713428555582533 | 0.2733 | 0 |
| 1000 | lognormal | 0.3 | 0.90255 | 0.89360 | 0.90616 / 0.89721 | 0.027823556048397313 / 0.06402432500314517 | 0.2788 | 0 |

Lognormal CV .30 is informational. Failed draws count as zero coverage; any fit failure also fails acceptance. Areas are independent, E is fixed and known, and theta has population mean one. This does not validate causal inference or spatial smoothing.

Bootstrap intervals use 200 equal-weight posterior-mixture draws; the Monte Carlo quantile approximation is part of the assessed procedure. Poisson-limit boundary-fit counts are in the JSON. See the frozen criterion for numerical conventions.

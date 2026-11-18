# Round 27 joint Wald criterion: fixed before outcomes

The eight cells are linear / binomial-robust × centered natural spline df 3/5 ×
x sampling error absent / standardized-scale SE .15. Each has 145 independent
areas and 2,000 draws, seed 20261128 + cell in that nesting order. All eight
conservative chi-squared joint tests must have empirical size in [.07,.13] at
nominal .10. Any null fit failure fails acceptance and counts as non-rejection,
never dropping a draw. No tuning after the full run. Power is informational.

For each draw, true x and independent control z are standard normal. Observed x
is true x plus independent normal sampling error with SE .15 (or zero). This is
CV .15 on a unit standardized scale, avoiding a meaningless CV at x=0 or negative
x. Replicates use census.simulation.make_replicates exactly, including its 4/80
variance convention. Full-sample patsy cr(x, df=q, constraints="center") supplies
the basis for all 80 refits. Centering removes the otherwise redundant intercept;
it preserves natural cubic splines and default quantile knots. Production cr(x,
df=q) uses this centered convention. Replicate outcomes and z are fixed.

Linear y=1+.5*z+epsilon, epsilon standard normal. Binomial logit(p)=-2.6+.3*z+
.5*epsilon, with independent area overdispersion epsilon standard normal and
fixed trials drawn once/cell from lognormal(log(3900),1), rounded, at least one.
The fixed alternative adds .3*sin(true x) to the mean or logit. Null/alternative
share x,z,replicates and area epsilon. Binomial counts are conditionally
independent. Covariance is full-sample HC3 plus the uncentered 4/80 sum of
replicate coefficient-deviation outer products. No centering across replicates,
no pseudo-inverse or denominator-df correction of chi-squared. Rank-deficient
joint covariance is a failed test. q is the number of spline columns.

The script uses batched full-rank OLS and binomial IRLS to finish 16,000 draws
without 2.56 million statsmodels object constructions. These kernels must agree
with delivered statsmodels refits and HC3 in numerical-parity tests, including
noisy-x replicates. Binomial IRLS tolerance is 1e-9, maximum 80 iterations.
No change to script/DGP/seeds/acceptance after the full run; this document and
script must be committed and pushed first. Smoke runs <=20 draws/cell write no
audit. Parallel workers have separate deterministic RNG streams.

Implementation clarifications, fixed before results: the plan's two_sided spelling
is an alias for existing two-sided, only for joint_wald; no one-sided joint tests.
Spline and joint confirmatory gating follow the joint validation result; EB is
always descriptive and carries a validation note. Non-spline coefficient outputs
retain their earlier model-SE convention; joint tests use explicitly labelled HC3
covariance. Full sampling and joint-model covariance metadata are additive output
changes necessary for the requested statistic; legacy numerical results must stay
identical. Registered manifest bytes are never changed.

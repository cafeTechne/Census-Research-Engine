# Round 30: frozen criterion before the full validation

Each candidate × model passes iff 90% interval coverage is >=0.86 in EVERY
required cell. C1: linear/binomial/Poisson separately; C2: linear only. Twelve
cells in model (linear, binomial, Poisson), range (0,100 km), reliability (.9,.7)
order. Exactly 2,000 draws/cell, seed 20261201+cell. No failed fit is removed
from the denominator. No changes, extra draws, alternative seeds or other k
after the first full run. Smoke: 1–20 draws/cell, no audit files.

Geometry and k=8 labels are the Round 26 frozen 145 MI/NY counties. Cached 2020
representative points only, checked before targets; coordinates/assignments are
embedded in im_acs_beta_star.json. HTTP is blocked. No data-dependent clustering.
State is constant within each frozen cluster, and its effect is absorbed by
the cluster intercept. Terms constant in only some clusters are refused.

Import Round 22's simulation_setup and simulation_draw: use its linear Gaussian
draw to obtain x1 and error, then x2=.5*x1+sqrt(.75)*a third independent spatial
field. Covariance is exp(-distance/range), diagonal jitter 1e-10; range 0 uses
independent areas. Marginal field variance is one, used in reliability scaling.
Both slopes .5 for linear, .3 for GLMs. Linear intercept 1 and NY .3; binomial
intercept -2.6 and NY .2; Poisson intercept 0 and NY .2. Error SD is 1 linear,
.15 on GLM link scales. Trials follow Round 22 (median 3900, log SD 1, min 50),
drawn once per cell. Poisson E=max(5,round(lognormal(log100,1))), once per cell.
E is known/fixed. External outcomes have no ACS sampling errors or replicates.

SEs: independent lognormal(0,.5) profiles for both covariates, fixed per cell;
each column scaled to mean(se^2)=(1-reliability)/reliability. Gaussian sampling
errors are independent across counties with cross-variable correlation .3,
matching the specified replicate correlation. make_replicates(observed,se,rng,
corr=[[1,.3],[.3,1]]) generates all 80 replicates. Auxiliary RNG is independent
SeedSequence([20261201,cell,draw,7]); replicates then null draws consume it in
fixed C1/C2 order and never perturb the main simulation RNG.

Before full simulation, one dataset of 400,000 independent areas per cell fixes
C1 beta*. Independent Gaussian true covariates have covariance [[1,.5],[.5,1]].
Sample county indices uniformly to reproduce the cell's joint empirical state,
SE profile and trial/exposure marginal distribution. Generate actual outcomes
from the same marginal model, including errors. Reference seed is
SeedSequence([20261201,cell,400000,7]). Linear beta* must agree within .005
with (Sigma_x+Sigma_u)^-1 Sigma_x beta; Sigma_u diagonals are mean(se_j^2)
and off-diagonal .3*mean(se1*se2). Commit both reference and closed-form values.
The reference coefficient, not a later retuned value, is C1's fixed target.

C1 cluster fits are unweighted OLS, grouped-binomial likelihood or Poisson
likelihood with fixed log E. C2 uses each cluster's own .05*sum_r deviations
outer products in Fuller's corrected moment equations, with zero outcome
sampling covariance. Non-positive-definite corrected matrix invalidates the
whole C2 fit. All eight clusters must be full rank with >=5 rows. IM estimate
is the unweighted mean; SE=sd(cluster estimates)/sqrt8, t(7) intervals/tests.
No additive ACS SE, fallback estimator, cluster deletion or extra cluster count.

Informational: C1 true-beta coverage, C2 failure rate, finite-interval mean
widths, and one-sided greater-null size at .05. Null C2 sets beta1=0 retaining
the noisy x2 control; null single-covariate C1 sets both slopes to zero and
omits x2 from the fit. They retain the state effect and same spatial error.
GLM null outcomes are freshly drawn on the auxiliary RNG. Failures are shown
separately; size denominator includes all draws. None of these alter acceptance.

Frozen files are enumerated in the script, including this criterion, beta*
values, numerical kernel, generators and Round 26 assignments. A full run must
match every file at --criterion-commit and refuses existing audit outputs.
Commit and push these files before running it. Failed candidate/model flags
remain false in the engine; unavailable post hoc checks have no invented p.

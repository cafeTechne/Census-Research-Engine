# Round 27 EB validation: fixed before outcomes

The eight cells, 1,000 draws, seeds 20261127 + cell, 90% coverage >= .86 acceptance
in all gamma cells and lognormal CV .15 cells are exactly PLAN_ROUND_27 section 1.
The two interval types are judged separately, without retuning or rerunning seeds.
Gamma and lognormal theta have mean one and the stated CV. Expected counts are
drawn once/cell. Counts 1–9 are interval censored, zero counts remain observed.
Every ML failure counts as zero coverage and makes acceptance fail; it is never
silently dropped. Other diagnostics are informational.

Numerical implementation frozen with this document: vectorised damped-Newton NB
maximum likelihood; exposure-weighted pooled mean and bias-corrected between-area
variance give Marshall-style moment starts (midpoint of censored intervals for
initialisation only). The exact likelihood sums the censored count probabilities.
Shape is limited to exp(18), an explicitly reported numerical Poisson-limit
boundary, not a moment fallback. Log-rate limits are [-24,36]; log-shape lower
limit -12. Likelihood/gradient convergence tolerances and maximum iterations are
in the script. A boundary fit is retained and its coverage assessed. All-zero data
are refused in the library because a finite positive Gamma ML fit is unidentified.

Posterior quantiles use exact Gamma inversion, or 38 bisections of the finite
censored Gamma-mixture CDF. Laird–Louis intervals use 200 parametric NB datasets,
reapplying suppression at 1–9, and refit both hyperparameters for every dataset.
For each fitted pair, draw once from each area's posterior conditional on its
original observed or censored count. Percentiles of these 200 equal-weight
posterior-mixture draws define the interval (NumPy linear quantiles). This explicit
Monte Carlo approximation, including its precision, is part of validation. A
bootstrap failure raises; no failed bootstrap is omitted. Bootstrap RNG uses one
integer drawn from the cell stream per outer draw. No reference-rate uncertainty
or spatial dependence is asserted. No guarantee of interval containment is made.

Smoke runs have <=20 draws/cell and write no audit. Full-run scripts require this
commit's hash and verify their bytes against it. The commit must be pushed before
full execution. Parallel workers do not affect any RNG stream. Audits are committed
separately after the full run.

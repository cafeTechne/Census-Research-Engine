# Fixed Round 28 SMR reference-rate criterion

Six cells: reference deaths per band 50/500/5000 × true expected study count
10/100; independent band-population CV .05. 2,000 draws/cell, seed 20261130 +
cell index in that nesting order. True SMR 1.2. Combined nominal 90% log-Wald
coverage with the reference term must be >= .86 in every cell. Coverage without
that term is informational. Zero counts/invalid draws count as noncoverage,
never dropped or redrawn. No retuning or changed seeds after the full run.

The Round 24 design supplies five equally populated bands, true rates per
person-year [.0005,.001,.003,.01,.04], independent Gaussian ACS population errors
and census.simulation.make_replicates. Fix period_years=5; populations are scaled
so 5*sum(pop*rate)=E. Draw study counts Poisson(1.2*E). For each reference band,
known person-years=D/true_rate; draw reference deaths Poisson(D) independently of
the study and ACS errors. Observed rate=observed_reference_deaths/person_years.
Both interval versions use those same noisy rates. Combined log variance adds
sum((E_band/E)^2 / observed_reference_deaths); rates stay fixed within ACS refits.
Any zero reference count, invalid full population or invalid replicate fails
that draw for both versions. Wald inference at O=0 is undefined/noncoverage.

Reference person-years are fixed/known; covariance from internal standardization
and spatial dependence are not simulated. Library notes explain that ignoring
positive study/reference covariance makes internal-standardized intervals
conservative. Membership cannot be inferred from numeric rates/counts; that
note is conditional, without an extra manifest flag. Pool reference band
contributions before squaring for a pooled study, since the reference rates are
shared by all study areas. Tests must cover this common-reference covariance.

Freeze and push this criterion and script before the first full run. Smoke runs
<=20 draws/cell write no audit. Record failed criteria, never change them.

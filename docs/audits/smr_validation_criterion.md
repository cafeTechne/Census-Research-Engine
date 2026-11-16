# Indirect SMR validation: criterion fixed before running

Acceptance: combined nominal 90% coverage of true SMR 1.2 >=0.86 in all six
E=10/50/500 x band CV=.05/.20 cells. Exactly 2,000 draws per cell, seed
20261117 + index, ordered (10,.05), (10,.20), (50,.05), (50,.20), (500,.05),
(500,.20). O=0 counts as non-coverage. Also report fixed-E Garwood coverage.

Five reference rates (.0005,.001,.003,.01,.04), with equal band populations
scaled by E/sum(rates). Each draw: Poisson(1.2 E) observed count, independent
Gaussian relative band-population errors, and 80 make_replicates values with
SE=CV*true_populations. Reference rates are fixed and uncertainty-free.
Nonpositive/invalid populations or expected counts count as non-coverage,
without clipping, redrawing or changing the denominator. No spatial dependence
or between-band correlation is simulated.

Smoke runs may use at most 20 draws per cell, without writing audits. Full
runs require the exact script and criterion in a named, pushed commit. No seed,
design, threshold or criterion may change after the full run.

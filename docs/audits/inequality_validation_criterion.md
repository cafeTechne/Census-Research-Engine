# Inequality validation: criterion fixed before running

Acceptance: conservative nominal 90% coverage >=0.86 for SII, log RII and
concentration in all four n=145/1000 x rank CV=0.05/0.15 cells. CV=0.30 is
informational. Exactly 1,000 draws per cell, seeds 20261116 + cell index,
ordered (145,.05), (145,.15), (145,.30), (1000,.05), (1000,.15), (1000,.30).

The full design is PLAN_ROUND_24 section 5 and scripts/inequality_validation.py.
Weights and true x are drawn once per cell; every draw redraws u, binomial
outcomes and rank errors, then the 80 make_replicates values. Truths are .03,
log(.10/.07) and the weighted concentration of .07+.03*true_ridit.

Operational choices fixed here: binomial denominators are w/50 rounded to the
nearest integer (NumPy rint), minimum one; regression weights remain the original
continuous w. Probabilities outside [0,1], undefined refits and invalid draws
count as non-coverage, without clipping, redrawing or reducing the denominator.
Report population coverage, bias and mean SE / empirical SD for all cells.
The rank CV diagnostic uses 100*SE/abs(observed rank), not nominal design CV.

Smoke runs may use at most 20 draws per cell and do not write audit files.
Full runs require the exact script and criterion in a named, pushed commit.
No seed, design, threshold or criterion may change after the full run.

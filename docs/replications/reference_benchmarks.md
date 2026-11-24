# Published Textbook & Closed-Form Reference Benchmarks (Round 115)

Offline automated verification in `tests/test_reference_benchmarks.py` locking Rounds 76–112 statistical modules to published textbook examples and exact mathematical identities:

| # | Benchmark Source | Module Verified | Exact Target |
| :--- | :--- | :--- | :--- |
| 1 | VanderWeele & Ding (2017, *Ann Intern Med* Table 1) | `census.bias_analysis.e_value` | `RR=3.9 -> E=7.26`, `RR=2.0 -> E=3.41`, `RR=1.5 -> E=2.37`, protective symmetry |
| 2 | Rogan & Gladen (1978, *Am J Epidemiol*) | `census.bias_analysis.misclassification` | Exact `RR = 2.0` & `OR` inversion under known `Se=0.85, Sp=0.92` |
| 3 | *Foundations of Epidemiology* (ch. 7–8, Table 8-5) | `census.stratified_core` | OCP/ovarian cancer `MH OR = 4/9`; confounder / effect-modifier / neither labels |
| 4 | Chiang (1984) & Arriaga (1984) | `census.demography_core` | `l_0 = 100,000`, monotone `e_0`, exact `sum(Arriaga) == Δe_0` |
| 5 | Harrer et al. (2021) | `census.evidence.combine_estimates` | Exact inverse-variance fixed-effect mean and SE |
| 6 | Lin (1989, *Biometrics*) | `census.agreement.check_agreement` | Exact CCC under pure location shift (`y = x + 2`) |
| 7 | Kitagawa (1955, *JASA*) | `census.disparity_core.kitagawa` | Exact `rate_effect + composition_effect == crude_difference` |
| 8 | Cunningham (*Causal Inference: The Mixtape*) | `census.rdd_core`, `census.matching` | Exact noiseless local-quadratic sharp RDD (`1.5`) and triple-difference (`-2.25`) |

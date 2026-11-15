# fit_eiv cluster-robust sandwich: simulation validation

Generated 2026-11-15 16:28 UTC by `scripts/eiv_cluster_validation.py` (500 simulated data sets per cell, n = 3000 units, 150 s). PLAN_ROUND_21 B1 (Round 20 friction F6) and Part 2 C5 (jackknife).

Design: G clusters of n/G units; the true covariate and the model error share a cluster component with intra-cluster correlation `icc`; y = 1 + 2x + error. The covariate carries heteroscedastic ACS-type sampling error (reliability 0.8) with synthetic replicates. Outcome `acs`: ACS-type error correlated 0.5 with the covariate's, with replicates. Outcome `external`: a model-based outcome (as CDC PLACES) with independent error that has a shared cluster draw, no replicates, held fixed (`fixed_variables`). Clustered = `cluster="GEOID.str[:5]"` (CR1: G/(G-1) x (n-1)/(n-k)); jackknife = `cluster_se="jackknife"` (delete-one-cluster, CR3); independent = the independence sandwich of the same fit. Coefficient of x, true value 2.

| G | icc | outcome | naive bias | fit_eiv bias | SD | mean SE clustered | mean SE independent | mean SE jackknife | coverage clustered (CR1) | coverage jackknife | coverage independent |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 0.0 | acs | -0.2728 | -0.0007 | 0.0242 | 0.0237 | 0.0242 | 0.0238 | 0.894 | 0.894 | 0.896 |
| 30 | 0.0 | external | -0.4001 | +0.0007 | 0.0296 | 0.0278 | 0.0286 | 0.0279 | 0.860 | 0.862 | 0.878 |
| 30 | 0.2 | acs | -0.2728 | +0.0014 | 0.0329 | 0.0332 | 0.0243 | 0.0341 | 0.890 | 0.894 | 0.774 |
| 30 | 0.2 | external | -0.4023 | +0.0004 | 0.0466 | 0.0445 | 0.0287 | 0.0460 | 0.862 | 0.878 | 0.682 |
| 30 | 0.5 | acs | -0.2777 | +0.0020 | 0.0646 | 0.0618 | 0.0246 | 0.0655 | 0.880 | 0.902 | 0.462 |
| 30 | 0.5 | external | -0.4081 | +0.0015 | 0.0732 | 0.0749 | 0.0290 | 0.0794 | 0.892 | 0.914 | 0.464 |
| 60 | 0.0 | acs | -0.2724 | +0.0001 | 0.0252 | 0.0241 | 0.0242 | 0.0241 | 0.872 | 0.872 | 0.886 |
| 60 | 0.0 | external | -0.4000 | +0.0004 | 0.0299 | 0.0283 | 0.0286 | 0.0284 | 0.896 | 0.898 | 0.896 |
| 60 | 0.2 | acs | -0.2732 | +0.0002 | 0.0284 | 0.0291 | 0.0242 | 0.0294 | 0.904 | 0.908 | 0.828 |
| 60 | 0.2 | external | -0.3984 | +0.0032 | 0.0374 | 0.0374 | 0.0286 | 0.0380 | 0.894 | 0.902 | 0.772 |
| 60 | 0.5 | acs | -0.2782 | -0.0037 | 0.0485 | 0.0468 | 0.0243 | 0.0481 | 0.870 | 0.880 | 0.594 |
| 60 | 0.5 | external | -0.4044 | +0.0034 | 0.0619 | 0.0580 | 0.0289 | 0.0597 | 0.870 | 0.878 | 0.582 |
| 150 | 0.0 | acs | -0.2728 | -0.0004 | 0.0240 | 0.0241 | 0.0242 | 0.0241 | 0.904 | 0.906 | 0.904 |
| 150 | 0.0 | external | -0.3993 | +0.0016 | 0.0290 | 0.0284 | 0.0285 | 0.0285 | 0.892 | 0.894 | 0.888 |
| 150 | 0.2 | acs | -0.2720 | +0.0012 | 0.0260 | 0.0264 | 0.0243 | 0.0265 | 0.914 | 0.916 | 0.882 |
| 150 | 0.2 | external | -0.4007 | +0.0003 | 0.0338 | 0.0324 | 0.0286 | 0.0326 | 0.884 | 0.884 | 0.834 |
| 150 | 0.5 | acs | -0.2747 | -0.0012 | 0.0376 | 0.0357 | 0.0243 | 0.0361 | 0.874 | 0.876 | 0.730 |
| 150 | 0.5 | external | -0.4035 | -0.0007 | 0.0410 | 0.0428 | 0.0287 | 0.0432 | 0.898 | 0.898 | 0.762 |

Monte Carlo 90% band for a true coverage of 0.90 with 500 simulations: +/- 0.022.

**Acceptance** (G >= 60: CR1 and jackknife coverage 0.87-0.93 in every cell; G = 30: jackknife mean coverage 0.891 >= CR1's 0.880; bias < 10% of the naive bias or |bias| < 0.01 everywhere): **PASSED**.

Reading: with no clustering (icc 0) both sandwiches cover. When the covariate and the errors share cluster components, the independence sandwich understates the SE and under-covers, increasingly with icc and cluster size; the clustered sandwich restores coverage. With few clusters (G = 30) CR1 tends to be slightly liberal, the known small-G behaviour (Cameron & Miller 2015); prefer G >= 50. The delete-one-cluster jackknife (CR3) is the conservative alternative (MacKinnon, Nielsen & Webb 2023).

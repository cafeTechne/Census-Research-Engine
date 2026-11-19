# Round 35 post hoc: R21b with corrected slopes under spatial dependence

**Post hoc; author self-review, not independent. Registered manifests and results are unchanged.**

Round 21b (MI/NY county premature mortality; County Health Rankings outcome; ACS covariates with
measurement-error-corrected EIV slopes) had no spatial check: Round 30's corrected cluster
procedure failed. Round 35 validated two corrected procedures (`docs/audits/spatial_eiv_validation.md`):
G1 (eight fixed clusters, pooled within-cluster correction) and G2 (spatial-error whitening, k = 6
neighbours). Inputs: the cached R21b analysed frame and replicates, checksums verified against the
registered manifest and bundle (Round 30's loader), HTTP blocked. The outcome is held fixed (external).
Reproduce: `scripts/r35_posthoc_spatial_eiv.py STUDIES_ROOT OUT_DIR`.

| Hypothesis | Registered Holm p | G1 estimate (90% CI) | G1 Holm p | G2 estimate (90% CI) | G2 Holm p | Still holds? |
| :--- | ---: | :--- | ---: | :--- | ---: | :--- |
| H1 poverty rate (m1) | 2.6e-18 | 13.3 (9.7 to 16.9) | 0.0003 | 13.0 (10.8 to 15.2) | 2.7e-17 | **yes, both** |
| H2 no vehicle (m2) | 0.947 | 3.1 (−1.9 to 8.0) | 0.279 | −0.8 (−1.8 to 0.2) | 0.905 | not supported as registered; still not |
| H3 cost burden (m2) | 0.475 | 4.6 (−4.0 to 13.3) | 0.279 | 1.4 (−1.1 to 4.0) | 0.356 | not supported as registered; still not |
| H4 age-standardized death proportion (m3) | 7.2e-27 | 26.7 (19.9 to 33.6) | 0.0003 | 25.7 (21.7 to 29.8) | 6.5e-19 | **yes, both** |

- One-sided (registered direction "greater") p-values, Holm over H1–H4 as registered.
- G1's intervals are wider (eight cluster estimates, t(7)); G2 estimates λ̂ ≈ 0.43–0.46, i.e.
  substantial residual spatial dependence, which the registered (independent-areas) EIV ignored.
- **m2 (H2, H3) is outside the validated design:** it has four error-prone covariates; validation
  covered at most two. Its rows are exploratory; G1 and G2 disagree in sign for H2.
- Estimand: the error-free slope (corrected for ACS sampling error), as registered.

The registered findings that were supported (H1, H4) are robust to spatial dependence with a
validated corrected procedure. Outputs: `r35_posthoc_outputs.tar.gz` (summary JSON; key-scanned).

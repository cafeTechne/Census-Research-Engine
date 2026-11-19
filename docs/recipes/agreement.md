# Agreement between two sources of the same quantity

1. Put both sources in one frame, one row per area (e.g. ACS disability vs PLACES disability; ACS
   population vs Census population estimates). Comparing an external source with its ACS equivalent
   is the one use of that pair the circularity rule allows.
2. `check_agreement(input_path, a, b, replicates_path=...)` (difference = b - a).
3. Report the **bias** with its interval and **kappa** (agreement of quintile classes): both
   validated (Round 37) for independent areas.
4. Limits of agreement (Bland-Altman, observed and error-free) have validated intervals since Round 48
   (moment-based SEs for heavy-tailed differences, .884-.936). Lin's concordance correlation is reported
   as an estimate; its interval failed validation, so do not use it for claims. With SEs, error-free versions show how much disagreement is
   sampling error versus real difference (descriptive).
5. Validation: `docs/audits/agreement_validation.md`.

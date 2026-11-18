# Round 29 compatibility and acceptance

Author self-review, not independent. Checks run locally on the Round 29 branch;
no GitHub CI, WONDER access, merge into defaultBranch, tag or release.

The resumed branch first merged defaultBranch (`b8da241`). Reviewed manual-file
work was retained (`1a485da`); the obsolete API client, fetch script, API tests
and XML fixture were removed in a separate commit (`46058b4`), preserving history.
The private export checkout stayed clean. Only its ignored INVENTORY.md was
written; all 62 manual files passed the inventory with zero flags.

## Offline compatibility

- Baseline: 1,840 passed, 37 skipped, 4 warnings and 50 subtests.
- Schema golden before registration: all 516 snapshots of 12 old manifests
  byte-identical. Final schema corpus: 640 snapshots of 14 manifests; all 12
  legacy manifest entries remain identical, with only the two new registrations
  added. No harness or normalization changes.
- Execution golden: 29 scenarios. All 28 non-WONDER scenarios remain identical.
  The WONDER scenario deliberately changes: three matching IDs including one
  suppressed outcome now report three matches, one suppressed and two analyzable
  counties, missing share zero, and no false vintage mismatch. The censored row
  has literal `suppressed` output values, an explicitly named nonblocking
  `wonder_suppressed` deviation and complete-case exclusion metadata. Model
  coefficients are unchanged. Status/notes, serialized masks and their dependent
  file hashes change as intended. There are now 20 deviation kinds (was 19).
- No version-induced or unrelated scientific changes in either golden.

## New checks

Twenty synthetic tests cover wrapped/older export formats, cause-code equivalence,
missing population, death-only exports, youngest-band person-year aggregation,
Not Stated handling, file hashes, national/state suppression, numeric 1–9
reference cells, template cell coverage/order, expected-count points and all 80
replicates, period mismatch, exclusive reference alternatives, a complete offline
manifest run, the actual geographic join guard, suppression versus observed zero
and unsuppressed missingness, unchanged other-source behavior, snapshots/refits,
renamed display columns, complementary totals, disclosure scanning, geography-only
replication and the registered H2 sensitivity/Holm family. No tests contact live
Census or WONDER endpoints.

## Real-data execution and disclosure

Both owner-approved manifests were committed and pushed together at
`150e1727ed37dab422f46ffbc919726e3c92f9d2` before any real outcome association.
MI/NY: 145 counties, H2 complete-case 132; OH/PA: 155, H2 complete-case 152.
Both runs are confirmatory with no blocking deviations. All three poverty
coefficients are positive and Holm-supported in each geography; H2 support is
stable in both registered endpoint-assignment refits. These assignments remain
internal and never produce county imputed outputs.

Reference-aware county SMRs, six descriptive EB maps and exploratory SII/RII
are included. Neither replication nor SMR intervals correct the regression's
fixed-offset uncertainty omission or unresolved spatial dependence. Reports
state these limits, ACS approximation to period-average populations, and the
whole-file B17001 published-MOE rounding warning without changing the sources.

The independent packaging check verified all protected snapshot fields and
EB/map fields for 13 MI/NY and 3 OH/PA censored counties, study-state restrictions,
and every bundle SHA-256. The structured scanner passed 15 county frames per
study. The 130-member local archive excludes raw exports, symlinks, national
reference death-count vectors and complementary totals; its uncompressed files
and archived member bytes passed the owner-key scan. No archive was published.

Local artifact: `/tmp/r29_study_outputs.tar.gz`, SHA-256
`a9bebd585fb6d7037a353b3b7955901432b50336cef8d0d836f9bb54883f25aa`.
Detailed audit: `/tmp/r29-package-audit.json`. The two study reports and immutable
manifests are committed; generated data and the archive remain outside Git.

Final full-suite acceptance is recorded in PLAN_ROUND_29.md section 8 and STATUS.md.

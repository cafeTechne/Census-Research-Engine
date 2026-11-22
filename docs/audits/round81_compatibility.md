# Round 81 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round81`, branch `phase81/scan`; defaultBranch (Rounds
76–80) merged in so the criterion commit `b6b69d0` (tag `criterion-r81`) stays an ancestor. Version 0.77.0.

## Behaviour changes

- New full-profile tool `spatial_scan` (75 tools); CLI `python -m census tool spatial_scan`.
- New library modules `census/scan.py` and `census/scan_core.py`; design file `docs/audits/scan_geometry.csv`
  (2022 county populations and representative points, force-added past the `*.csv` ignore rule). No manifest
  change; goldens expected byte-identical.

## Exceptions

1. **Noisy-denominator gate (new, from the reported sensitivity cells):** a `<denominator>_se` column with a median
   CV above .01 makes the p-value exploratory, with a note. This rule was not pre-set; it only makes the engine
   stricter.
2. **Power cells used 250 draws** and the 10% and 25% maximum windows were not simulated (both stated in the
   criterion); windows other than 50% are exploratory.
3. **No manifest method**, as the plan specified.
4. **Tag correction:** a failed first commit attempt pushed `criterion-r81` at the base commit for about a minute;
   it was moved to the real criterion commit `b6b69d0` before any run.
5. **Example map omitted** (summary only).

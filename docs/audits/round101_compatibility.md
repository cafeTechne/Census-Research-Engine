# Round 101 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round101`, branch `phase101/demography`. The criterion
commit (tag `criterion-r101`) is an ancestor of the branch. Version 0.97.0.

## Behaviour changes

- **New library modules** `census/demography.py` and `census/demography_core.py`.
- **No tool and no manifest changes,** so goldens are expected byte-identical.

## Exceptions

1. **The plan's new `demography` recipe became a section of `external_health_outcome`.** A 27th recipe name would
   push the core `get_recipe` description past its 700-character budget.
2. **Arriaga by cause uses the nine mutually exclusive underlying-cause exports on file.** Overdose, firearm and
   alcohol-induced deaths overlap other categories, and COVID-19 falls in "other". Suppressed national cause cells
   count as 0, with a note.
3. **Census-survival migration is a library function only, with an identity test.** The example does not run it,
   because two decennial single-year-age extractions by county would add network-heavy steps outside the plan's core.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 100.
- Full suite: 2390 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

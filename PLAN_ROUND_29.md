# Round 29 plan: real-data mortality from CDC WONDER

**Status: implemented on `phase29/wonder-mortality`; final acceptance in section 8.** All WONDER data are the owner's manual exports (owner decision, 2026-11-18: the API
is not used; Part A0). All 62 files in the guide (`docs/data/wonder_exports.md`, Parts A–F) are in
`external_data/wonder/` and passed a structure check on 2026-11-18. Round 29 uses six of them:
`ucd/2018-2022/county/{premature_all_causes,drug_overdose,heart_disease}.tsv` and
`ucd/2018-2022/national_age_sex/{all_causes,drug_overdose,heart_disease}.tsv`. The rest (more causes,
the 2013–2017 window, MCD drug involvement) are inventoried only, for later rounds.
**Pre-Part C review: done (2026-11-18).** Methods are validated: Poisson GLM with HC3 SEs, SMR with
period scaling and reference counts (Round 28), EB for descriptive maps (Round 27). No spatial method
works with ACS replicates or Poisson yet (Round 30 is queued), so spatial dependence is a stated
limitation. The owner confirmed H1–H3 and the replication rule as written (with the H2 suppression
sensitivity below).

**Goal.** (A0) Remove the WONDER API client. (A) Inventory and check the exports. (B) Turn WONDER age × sex exports into reference rates with
their counts, build matching ACS age × sex populations, and enforce the WONDER data-use rule in outputs.
(C) Run one pre-registered MI/NY mortality study, replicated unchanged in held-out OH/PA. Version 0.26.0.

## 0. Ground rules

1. **Resume** the existing branch `phase29/wonder-mortality` (worktree `/tmp/census-round29`): it has
   commits 6295958 (API client) and d6c2411 (inventory), plus uncommitted work from a session that ran
   out of tokens. First `git merge defaultBranch` (never rebase or force-push) to get this plan, then
   review the uncommitted changes: keep and commit what fits this plan, drop what does not. Do not
   merge into `defaultBranch`, tag or release.
2. **No AI attribution** in commits or the PR body. Never print, log or commit `.env`, keys or tokens.
3. **WONDER access: none.** All WONDER data, county and national, are the owner's manual exports
   (`docs/data/wonder_exports.md`). Never contact WONDER, automate the web form or get past a bot
   check. Never copy raw exports into the repository or a release. `external_data/wonder/` is itself a
   git checkout of the owner's **private** backup repository: never commit, push or edit anything
   there (only `INVENTORY.md`, which that checkout ignores, may be written).
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. No GitHub CI.
5. **Pre-registration:** before the manifest is hashed and committed, no association between any outcome
   and any covariate may be computed or viewed. Parts A and B check structure only.
6. Record impossibilities in section 8 and choose the option that changes least.

## 1a. Part A0: remove the WONDER API client (owner decision, 2026-11-18)

The owner decided the API is too narrow (national data only) and exports the national files by hand,
with the same settings as the guide's "national setup" (Ten-Year Age Groups × Sex, all US, Step 6 as in
its cause list), into `external_data/wonder/ucd/<years>/national_age_sex/<cause>.tsv`.

- **Remove** `census/wonder_api.py`, `scripts/wonder_fetch_national.py`, their tests and the XML fixture
  in a new commit (no rebase, no history rewrite; commit 6295958 stays in history). Keep anything the
  manual-file path reuses (parsers, `.tsv` fixtures). (The local `.wonder-api-last-request` file is
  already deleted.)
- **Rule update** (with rule 6's): CLAUDE.md, STATUS.md and the guide already say that all WONDER data
  are manual exports; keep them consistent if you touch them.

## 1b. Part A: inventory (`scripts/wonder_inventory.py`)

- Walk `external_data/wonder/` (`*.tsv`/`*.txt` only; skip `.git`, `README.md`, `.gitignore`). Parse each export's footer with `census.vital_records.parse_footer`, and
  each national export the same way.
  Write `external_data/wonder/INVENTORY.md` (gitignored), with one row per file:
  - path, database, years, group-by and cause selection;
  - SHA-256;
  - row count, suppressed rows and zero rows.
- **Flag mismatches:**
  - folder years ≠ footer years;
  - folder kind ≠ group-by (`county` / `national_age_sex` / `state_age_sex`);
  - an all-US county file with fewer than 3,100 rows ("Show Zero Values" off);
  - a missing `County Code` or `Deaths` column (other measure columns are optional: record which exist);
  - a cause selection whose ICD-10 code ranges differ from the guide's (compare codes, not the tab:
    `C00-C97` on the ICD-10 Codes tab equals `#Malignant neoplasms (C00-C97)`);
  - for `premature_all_causes`, an age filter other than the nine groups under 75;
  - a database that does not match the folder: `ucd/2018-2022` = "Underlying Cause of Death, 2018-2024,
    Single Race"; `ucd/2013-2017` = "Underlying Cause of Death, 1999-2020"; `mcd/2018-2022` = "Multiple
    Cause of Death, 2018-2024, Single Race";
  - a national file without 22–24 age × sex rows (11 ten-year groups plus "Not Stated", by sex);
  - an `mcd` file whose `MCD - ICD-10 Codes` parameter is missing or differs from the guide's Part F
    codes, or whose `UCD - Drug/Alcohol Induced Causes` is not the four overdose items.
- **Expected selections** (from the guide's cause list; real footer keys): 113-list causes under
  `ICD-10 113 Cause List`; `cancer` may be `ICD-10 Codes: C00-C97`; `drug_overdose` under
  `Drug/Alcohol Induced Causes` (four items); `alcohol_induced` is `Drug/Alcohol Induced Causes:
  Alcohol-induced causes` (the group heading); `firearm` is `Injury Mechanism & All Other Leading
  Causes: Firearm` (intent All is not echoed); `all_causes` and `premature_all_causes` have no cause
  parameter.
- **Not flags (record only):** suppressed cells in national files. They occur only in child age groups
  and "Not Stated" for alcohol-induced, liver, diabetes, kidney, CLRD, stroke, suicide, firearm and the
  MCD drugs; Round 29's three national files have none. 2013–2017 county files have 3,147 rows.
- Exit non-zero on any flag. Test it on fixtures in `tests/fixtures/wonder/`: small synthetic files in
  real WONDER format, built by hand, with no real data.
- **Real export format (owner's files, 2026-11-18; fix `vital_records` and fixtures to match):**
  - files end `.tsv` (older exports `.txt`); accept both;
  - footer parameter lines wrap at about 128 characters (`Ten-Year Age Groups`, `Drug/Alcohol Induced
    Causes`): join continuation lines before parsing, or later parameters are lost;
  - `Population` may be `Not Available` (Connecticut's legacy counties have no 2022 estimates): treat as
    missing with a note, not an error;
  - an age-filtered export may have only `Deaths` (no Population or rate columns): accept it;
  - `Show Totals: Disabled` may appear, with no Total row.
  - The 2018–2022 county exports have no Total row even with `Show Totals: True`; the 2013–2017 ones
    have one. Accept both.
  - The scratch check of all 62 files passed with these rules; repeat it with the real script, which
    must flag nothing on them.

## 2. Part B: engine

1. **`vital_records.read_wonder_reference(path)`** parses the national age × sex manual exports
   (`.tsv`/`.txt`, Ten-Year Age Groups × Sex), with this output:
   - Columns: band, sex, deaths, population, rate per person-year (deaths / summed annual population),
     and suppressed.
   - Bands map WONDER ten-year groups to ACS B01001: `0-4` (= "< 1 year" + "1–4 years"), `5-14`, …,
     `75-84`, `85+`.
   - "Not Stated" age rows (population `Not Applicable`) are dropped, and their deaths are recorded in
     a note.
   - A suppressed reference cell (after dropping "Not Stated") is refused for national files. Round 29's
     three causes have none; later causes with suppressed child-age cells need a pre-registered rule
     (record this in STATUS backlog item 3; do not invent one now). For state files it is allowed only if
     the manifest pre-registers that state rates are used, and the cell is then refused at run time.
2. **ACS bands.** Add a derivation template `acs_age_sex_bands` that sums B01001 cells into the same
   10 bands × 2 sexes, so 20 manifest variables keep their replicates.
3. **`smr` arguments** (Round 28 added `period_years` and `reference_counts`). Add `reference_export:
   {file, sha256}`, an alternative to literal `reference_rates`:
   - rates and counts come from the file;
   - `period_years` must equal the number of footer years;
   - the band order is fixed by the template.
4. **Expected-count derivation** `expected_count` (for Poisson offsets): `E_i = period_years × Σ pop_ib ·
   rate_b`, computed per replicate as well, so it has replicate values. The fitted model holds the offset
   fixed (stated in the methods text). The SMR's combined interval is the sensitivity check.
5. **Suppressed observed counts.**
   - **Fix the suppression/join bug recorded in Round 25 before running the study.** In
     `health_sources.join_external` and the manifest join guard, distinguish an unmatched GEOID
     from a matched WONDER row whose outcome is suppressed. Retain suppression flags before
     filtering outcomes; suppression alone must not trigger `external_join_failed` or a
     geography-vintage mismatch warning. Keep genuine missing-ID checks effective, report
     unsuppressed missing outcomes separately, and preserve other sources' existing behavior.
   - Record matched, unmatched, suppressed and analyzable county counts separately. Suppressed
     values remain unavailable, never zero or an inferred exact count; this fix does not relax
     the complete-case or output-suppression rules below.
   - A county whose count is suppressed (1–9) has no per-county SMR (a deviation that names it).
   - Pooled statistics and regressions exclude suppressed counties as complete-case. The excluded
     counties are listed, and the count of excluded deaths is bounded at [n, 9n].
   - The Round 27 EB smoothing may model them, but only for descriptive maps, and see rule 6.
6. **Data-use rule, enforced in the bundle writer.**
   - Any per-county output column derived from a WONDER count (count, rate, SMR, EB estimate) is replaced
     by `"suppressed"` where the underlying count is 1–9.
   - No output may let a suppressed count be back-calculated: for example, a state total alongside all
     but one county, or a national total from a reference file alongside every other US county (the
     owner's 2018–2022 all-cause county and national files together reveal one county's count). Study
     outputs cover only the study states and never include national reference death counts by band
     next to county counts.
   - Note: WONDER's rule for these databases covers *any* statistic representing 1–9 deaths, not only
     sub-national ones; national reference cells of 1–9 are suppressed by WONDER and must stay so.
   - Add a standing rule to `STATUS.md` and `CLAUDE.md` (hard rules): "WONDER outputs: no sub-national
     counts 1–9 or values derived from them; no raw exports in the repo or releases."
7. Tests for each of items 1–6, using the fixtures. For the join regression, use three matching
   county IDs with one suppressed outcome: report all three as matched, one suppressed and two
   analyzable, without a vintage-mismatch failure caused by suppression. A companion fixture
   with genuinely unmatched IDs must still trigger the existing join guard. Also distinguish
   observed zero counts and unsuppressed missing outcomes from suppression.

## 3. Part C: pre-registered study (confirmatory; author self-review, not independent)

The analysis uses only validated methods: a Poisson GLM with `scale: "robust"` (HC3), offset `log E`,
and replicates. Round 26's IM-8 refuses ACS replicates and Poisson, so spatial dependence is a stated
limitation (Round 30 may later supply a post hoc check).

| ID | Outcome (observed deaths, 2018–2022, county) | Expected | Tested term | Direction |
| :--- | :--- | :--- | :--- | :--- |
| H1 | `premature_all_causes` | national age × sex `all_causes` rates, ages under 75 only | poverty % (B17001) | positive |
| H2 | `drug_overdose` | national age × sex `drug_overdose` rates | poverty % | positive |
| H3 | `heart_disease` | national age × sex `heart_disease` rates | poverty % | positive |

- **Model:** every model includes a state fixed effect. Holm correction over H1–H3. MI/NY counties.
- **Suppression sensitivity (H2, pre-registered).** In the 2018–2022 files, `drug_overdose` is
  suppressed (1–9 deaths) in 13 MI/NY counties and 3 OH/PA counties; the H1 and H3 outcomes have none.
  Complete-case exclusion drops the counties with the fewest deaths, which can bias the slope. Refit H2
  (and its replication) twice more, with every suppressed count set to 1 and then to 9 (a simple
  sensitivity, not a strict bound). Report the coefficient and Holm p of all three fits. H2 is called
  robust only if its conclusion is the same in all three. These fits output coefficients only, never
  county values (rule 6). If an outcome has no suppressed study counties, skip the refits and say so.
- **Circularity:** outcomes are direct vital records, not modelled estimates, so R1 is satisfied.
- **Replication:** the same manifest with geography swapped to OH/PA is a separate registered manifest,
  hashed at the same commit. A replication "holds" when the coefficient has the same sign and its Holm p
  is below 0.10.
- **Descriptive, not tested:** EB-smoothed SMR maps (if Round 27's EB passed), and the SII/RII of the
  SMR across poverty ridits (exploratory).
- **Reports:** `docs/studies/r29_mi_ny_mortality_smr.md` and `docs/studies/r29_oh_pa_replication.md`.
  Outputs go in `r29_study_outputs.tar.gz`, after a key scan and the rule-6 check.

**Owner checkpoint: passed (2026-11-18).** H1–H3, the replication rule and the H2 sensitivity are fixed;
commit the manifests without asking again.

## 4. Acceptance

- Inventory is clean (no flags) on all 62 owner files.
- The API client is removed (Part A0), and no code path contacts WONDER.
- Every Part B rule is tested.
- The two manifests are committed before any outcome analysis, and the commit order shows it.
- Rule 6 is verified on the study bundle: a test scans the output for counts 1–9 in per-county WONDER
  columns.
- Full suite: baseline plus the new tests, 0 failures.
- Version 0.26.0 and a CHANGELOG entry. STATUS: the study row, the standing rule, and backlog item 3
  updated.

## 5. Commits

(0) Remove the API client (Part A0); (1) the
inventory script and fixtures; (2) the Part B engine and tests; (3) the two manifests
(registration); (4) the runs and reports; (5) docs, STATUS, version and the status table. Push. If you
cannot open a PR, leave a body at `/tmp/round29-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| API client removed; national files in place | Done | `46058b4`; all inputs manual. |
| Inventory result | Passed | 62 files, 0 flags; private checkout clean (only ignored INVENTORY.md written). |
| Part B engine, tests | Passed | 20 synthetic tests; details in docs/audits/round29_compatibility.md. |
| Registration commit | Done | Both manifests committed/pushed at `150e172` before outcomes. |
| H1–H3 MI/NY; OH/PA replication | Done | All three positive, Holm-supported and replicated; H2 stable in both sensitivities. |
| Rule-6 check | Passed | 15 frames/study; independent mask/hash checks; 130-member local archive key-scanned. Hash in compatibility audit. |
| Final suite | Passed | 1860 passed, 37 skipped, 4 warnings, 50 subtests; 0 failures (baseline 1840/37). |
| Exceptions | Recorded | WIP retained at `1a485da` before API removal, as directed; initial merge `b8da241`. VRE warning documented. No protocol deviation, WONDER access, defaultBranch merge, tag, release or CI. |

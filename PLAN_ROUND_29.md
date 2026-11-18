# Round 29 plan (draft, blocked on owner county exports): real-data mortality from CDC WONDER

**Status: draft.** This round starts when the owner's county exports are in `external_data/wonder/`
(three files are required; see `docs/data/wonder_exports.md`). National reference data come from the
official WONDER API instead of manual exports (Part A0). The API serves national data only, so county
counts remain manual. Parts A0 and A may be pulled forward on request.
Before Part C, the maintainer reviews this plan against what Rounds 25–28 actually shipped, especially
which methods passed validation, and the owner confirms the hypotheses.

**Goal.** (A0) Fetch the national age × sex reference data through the WONDER API. (A) Inventory and
check the exports and API files. (B) Turn WONDER age × sex exports into reference rates with
their counts, build matching ACS age × sex populations, and enforce the WONDER data-use rule in outputs.
(C) Run one pre-registered MI/NY mortality study, replicated unchanged in held-out OH/PA. Version 0.26.0.

## 0. Ground rules

1. Branch `phase29/wonder-mortality` from `defaultBranch`. Do not merge, tag or release. Never rebase or
   force-push. Work in your own clone or worktree.
2. **No AI attribution** in commits or the PR body. Never print, log or commit `.env`, keys or tokens.
3. **WONDER access: the official API only, national data only, through Part A0's client.** The API
   cannot group or filter vital statistics by any location, so county data still come only from the
   owner's manual exports. Never automate the web form or get past a bot check. Before the first live
   query, confirm with the owner that they accept WONDER's data-use restrictions. Never copy raw exports
   or API responses into the repository or a release.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. No GitHub CI.
5. **Pre-registration:** before the manifest is hashed and committed, no association between any outcome
   and any covariate may be computed or viewed. Parts A and B check structure only.
6. Record impossibilities in section 8 and choose the option that changes least.

## 1a. Part A0: WONDER API client (`census/wonder_api.py`, `scripts/wonder_fetch_national.py`)

Reference: <https://wonder.cdc.gov/wonder/help/wonder-api.html>. Requests are a POST of one parameter,
`request_xml`, to `https://wonder.cdc.gov/controller/datarequest/<database ID>`. The XML must include
`accept_datause_restrictions=true`.

- **Probe first.** Make one national query to confirm that the 2018-and-later single-race Underlying
  Cause database (D158 in WONDER's URLs; check the ID) answers API requests, and that its
  ten-year-age × sex grouping matches the manual export. Take the parameter codes from the help page's
  examples or from the form's own request XML; never guess them silently. If the API refuses this
  database, record it in section 8: the national files then become manual exports (the guide's
  fallback), and the rest of the round is unchanged.
- **Client rules (enforced in code):**
  - national queries only: refuse any location group-by or filter before sending;
  - `accept_data_use_restrictions` must be passed explicitly as `True` (the fetch script's flag is
    `--accept-data-use-restrictions`); there is no default and no environment variable;
  - one request at a time, at least 120 seconds apart (WONDER asks for this), with no parallel runs
    (a lock file); at most one retry, after the same wait;
  - a generic User-Agent; no email or other personal data in requests;
  - network use only in the fetch script, never during manifest runs or tests.
- **Cache and provenance.** Write each response to
  `external_data/wonder/ucd/<years>/national_age_sex/<cause>.xml` (gitignored), with the request XML
  beside it and a SHA-256 in the inventory. Never overwrite: a re-fetch gets a `_v2` name. Check that
  the response echoes the requested database, years, grouping and cause selection; otherwise refuse.
- **Causes:** the Tier 1 selections in `docs/data/wonder_exports.md`, for 2018–2022. Round 29 needs
  `all_causes`, `heart_disease` and `drug_overdose`; fetch all eight Tier 1 causes in one throttled run.
- **Tests (offline):** synthetic response fixtures written by hand in WONDER's XML format; mocked HTTP;
  refusals for a missing acceptance, a location grouping, a second concurrent run, an echo mismatch and
  an existing cache file; the throttle checked with a fake clock. No test touches the network.
- **Rule update** (with rule 6's): replace the CLAUDE.md "Data access" line's WONDER clause with
  "CDC WONDER: the official API for national data only, through `census.wonder_api`, with the owner's
  acceptance of the data-use restrictions; county data are manual exports; no web-form automation or
  bot-check circumvention". Mirror it in STATUS.md and `docs/data/wonder_exports.md`.

## 1b. Part A: inventory (`scripts/wonder_inventory.py`)

- Walk `external_data/wonder/`. Parse each export's footer with `census.vital_records.parse_footer`, and
  each API file's echoed request (Part A0).
  Write `external_data/wonder/INVENTORY.md` (gitignored), with one row per file:
  - path, database, years, group-by and cause selection;
  - SHA-256;
  - row count, suppressed rows and zero rows.
- **Flag mismatches:**
  - folder years ≠ footer years;
  - folder kind ≠ group-by (`county` / `national_age_sex` / `state_age_sex`);
  - an all-US county file with fewer than 3,100 rows ("Show Zero Values" off);
  - missing CI/SE columns;
  - a `drug_overdose` selection that differs from the guide.
- Exit non-zero on any flag. Test it on fixtures in `tests/fixtures/wonder/`: small synthetic files in
  real WONDER format, built by hand, with no real data.

## 2. Part B: engine

1. **`vital_records.read_wonder_reference(path)`** parses age × sex API files and (as the fallback)
   manual exports, with the same output:
   - Columns: band, sex, deaths, population, rate per person-year (deaths / summed annual population),
     and suppressed.
   - Bands map WONDER ten-year groups to ACS B01001: `0-4` (= "< 1 year" + "1–4 years"), `5-14`, …,
     `75-84`, `85+`.
   - "Not Stated" age rows are dropped, and the count is recorded in a note.
   - A suppressed reference cell is refused for national files. For state files it is allowed only if
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
     but one county.
   - Add a standing rule to `STATUS.md` and `CLAUDE.md` (hard rules): "WONDER outputs: no sub-national
     counts 1–9 or values derived from them; no raw exports in the repo or releases."
7. Tests for each of items 1–6, using the fixtures. For the join regression, use three matching
   county IDs with one suppressed outcome: report all three as matched, one suppressed and two
   analyzable, without a vintage-mismatch failure caused by suppression. A companion fixture
   with genuinely unmatched IDs must still trigger the existing join guard. Also distinguish
   observed zero counts and unsuppressed missing outcomes from suppression.

## 3. Part C: pre-registered study (confirmatory; author self-review, not independent)

The analysis uses only validated methods: a Poisson GLM with `scale: "robust"` (HC3), offset `log E`,
and replicates. If Round 26 shipped a validated spatial-cluster method, it is used as well; otherwise
spatial dependence is a stated limitation.

| ID | Outcome (observed deaths, 2018–2022, county) | Expected | Tested term | Direction |
| :--- | :--- | :--- | :--- | :--- |
| H1 | `premature_all_causes` | national age × sex `all_causes` rates, ages under 75 only | poverty % (B17001) | positive |
| H2 | `drug_overdose` | national age × sex `drug_overdose` rates | poverty % | positive |
| H3 | `heart_disease` | national age × sex `heart_disease` rates | poverty % | positive |

- **Model:** every model includes a state fixed effect. Holm correction over H1–H3. MI/NY counties.
- **Circularity:** outcomes are direct vital records, not modelled estimates, so R1 is satisfied.
- **Replication:** the same manifest with geography swapped to OH/PA is a separate registered manifest,
  hashed at the same commit. A replication "holds" when the coefficient has the same sign and its Holm p
  is below 0.10.
- **Descriptive, not tested:** EB-smoothed SMR maps (if Round 27's EB passed), and the SII/RII of the
  SMR across poverty ridits (exploratory).
- **Reports:** `docs/studies/r29_mi_ny_mortality_smr.md` and `docs/studies/r29_oh_pa_replication.md`.
  Outputs go in `r29_study_outputs.tar.gz`, after a key scan and the rule-6 check.

**Owner checkpoint:** H1–H3 and the replication rule are a proposal. The owner confirms or edits them
before the manifest is committed.

## 4. Acceptance

- Inventory is clean (no flags) on the owner's files.
- The Part A0 tests pass offline, and the national fetch ran once, throttled, after the owner's
  acceptance.
- Every Part B rule is tested.
- The two manifests are committed before any outcome analysis, and the commit order shows it.
- Rule 6 is verified on the study bundle: a test scans the output for counts 1–9 in per-county WONDER
  columns.
- Full suite: baseline plus the new tests, 0 failures.
- Version 0.26.0 and a CHANGELOG entry. STATUS: the study row, the standing rule, and backlog item 3
  updated.

## 5. Commits

(0) The API client, fetch script, fixtures and tests (the fetched files stay uncommitted); (1) the
inventory script and fixtures; (2) the Part B engine and tests; (3) the two manifests
(registration); (4) the runs and reports; (5) docs, STATUS, version and the status table. Push. If you
cannot open a PR, leave a body at `/tmp/round29-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| API probe (database ID) / national fetch | | |
| Inventory result | | |
| Part B engine, tests | | |
| Registration commit | | |
| H1–H3 MI/NY; OH/PA replication | | |
| Rule-6 check | | |
| Final suite | | |
| Exceptions | | |

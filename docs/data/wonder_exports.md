# CDC WONDER exports: a step-by-step checklist

**For the owner, done by hand.** Every WONDER file the engine uses is a manual export from the WONDER
web form: the county death counts *and* the national age × sex reference rates. The engine never
contacts WONDER. (Owner decision, 2026-11-18: the WONDER API is not used. It serves national data only,
which is too narrow.)

## What to download, in order

Work top to bottom. You can stop after any part and come back later; WONDER does not need to stay open.

| Part | Database | Years | What | Files | Needed by |
| :--- | :--- | :--- | :--- | ---: | :--- |
| ✓ | Underlying Cause, 2018–2024 | 2018–2022 | county, first 8 causes | 8 | done 2026-11-18 |
| **A** | Underlying Cause, 2018–2024 | 2018–2022 | **national** age × sex, 3 causes | **3** | **Round 29: do these first** |
| B | Underlying Cause, 2018–2024 | 2018–2022 | national age × sex, other causes | 10 | later studies |
| C | Underlying Cause, 2018–2024 | 2018–2022 | county, 6 more causes | 6 | later studies |
| D | Underlying Cause, 1999–2020 | 2013–2017 | county, all 14 causes | 14 | change analyses |
| E | Underlying Cause, 1999–2020 | 2013–2017 | national age × sex, 13 causes | 13 | change analyses |
| F | Multiple Cause, 2018–2024 | 2018–2022 | drug involvement, county + national | 8 | optional, last |

Each export takes 1–2 minutes (county queries can take longer). Part A alone is about 5 minutes.

**Why 2013–2017 is the second window.** It is the latest ACS 5-year window that does not overlap
2018–2022, and the engine only compares 5-year releases that do not overlap. A window such as 2019–2023
shares four years with 2018–2022, so it is not needed. 2013–2017 comes from a different WONDER database
(the 2018–2024 one starts in 2018), but the form works the same way; Part D lists the small differences.

## Quick answers

- **File format: leave it exactly as WONDER gives it.** WONDER has one export format: a tab-delimited
  text file, which now downloads as `.tsv` (older exports were `.txt`; the engine reads both). There is
  no Excel or CSV option, and you need none. **Do not open the file in Excel and save it.** Doing so
  strips WONDER's notes at the bottom (the engine reads them), can drop leading zeros from county codes,
  and changes the file's fingerprint (SHA-256), which the study pins. Rename the file; never edit it.
- **Do not study the numbers.** The study must be registered before anyone looks at county results.
  Scrolling past the results table WONDER shows after each export is fine. If you do look closely at
  something, tell me, and the study report will say so.
- **If anything on the form looks different from this page** (a label, a missing option), stop and send
  me a screenshot or the label text. Do not guess.
- **One tab counts in Step 6.** Step 6 has several tabs (ICD-10 113 Cause List, Drug/Alcohol Induced
  Causes, and so on). WONDER uses the selection on the tab that is **open when you click Send**, so
  always finish on the tab the cause table names.

## Step 0: make the folders (once)

On the machine that runs the engine (the desktop), from the project folder:

```bash
mkdir -p external_data/wonder/ucd/2018-2022/county external_data/wonder/ucd/2018-2022/national_age_sex \
         external_data/wonder/ucd/2013-2017/county external_data/wonder/ucd/2013-2017/national_age_sex \
         external_data/wonder/mcd/2018-2022/county external_data/wonder/mcd/2018-2022/national_age_sex
```

`external_data/` is gitignored, so nothing here is ever committed.

## The cause list (used by every part)

Each part says which rows to export. "113 list" means the **ICD-10 113 Cause List** tab of Step 6.
Labels may be worded slightly differently on your screen; match on the ICD-10 codes in brackets. If the
codes differ, stop and ask.

| Name (save as `<name>.tsv`) | Step 6 tab | Select exactly this |
| :--- | :--- | :--- |
| `all_causes` | 113 list | `*All* (All Causes of Death)` |
| `heart_disease` | 113 list | `#Diseases of heart (I00-I09,I11,I13,I20-I51)` |
| `drug_overdose` | Drug/Alcohol Induced Causes | Ctrl-click these four and nothing else: `Drug poisonings (overdose) Unintentional (X40-X44)`, `Drug poisonings (overdose) Suicide (X60-X64)`, `Drug poisonings (overdose) Homicide (X85)`, `Drug poisonings (overdose) Undetermined (Y10-Y14)` |
| `cancer` | 113 list | `#Malignant neoplasms (C00-C97)` |
| `unintentional_injury` | 113 list | `#Accidents (unintentional injuries) (V01-X59,Y85-Y86)` |
| `suicide` | 113 list | `#Intentional self-harm (suicide) (*U03,X60-X84,Y87.0)` |
| `diabetes` | 113 list | `#Diabetes mellitus (E10-E14)` |
| `stroke` | 113 list | `#Cerebrovascular diseases (I60-I69)` |
| `clrd` | 113 list | `#Chronic lower respiratory diseases (J40-J47)` |
| `liver_disease` | 113 list | `#Chronic liver disease and cirrhosis (K70,K73-K74)` |
| `kidney_disease` | 113 list | `#Nephritis, nephrotic syndrome and nephrosis (N00-N07,N17-N19,N25-N27)` |
| `alcohol_induced` | Drug/Alcohol Induced Causes | Ctrl-click the two alcohol items and nothing else: `Alcohol poisonings (overdose) (X45, X65, Y15)` and `All other alcohol-induced causes` |
| `firearm` | Injury Intent and Mechanism | Left box (**Injury Intent**): `*All*`. Right box (**Injury Mechanism & All Other Leading Causes**): `Firearm` only |
| `premature_all_causes` | 113 list | `*All* (All Causes of Death)`, **and** Step 3 limited to ages under 75 (below). **County files only.** |

**Ages under 75 (only for `premature_all_causes`):** in Step 3, open the **Ten-Year Age Groups** tab and
select `< 1 year` through `65-74 years` (click the first, Shift-click the last: nine groups). **Right
after** that export, set Step 3 back to `*All*` on the same tab, or every later file will be wrong.

## The two setups

Every export uses one of two setups. Set one up once; after that, WONDER keeps your settings, and you
change only Step 6 between exports. Anything not mentioned: leave at its default.

### County setup

| Step | What to set |
| :--- | :--- |
| **1. Organize table layout** | **Group Results By:** `County`. **And By:** `None` (all the other boxes at None). **Measures:** Deaths, Population and Crude Rate are ticked by default; also tick Crude Rate's **95% Confidence Interval** and **Standard Error**. Leave **Age Adjusted Rate** and its interval and SE **unticked** (WONDER refuses them with county grouping, and the study does not use them). Rates per **100,000**. |
| **2. Select location** | Leave `*All* (The United States)`. County means the decedent's county of **residence**. |
| **3. Select demographics** | Leave every box at **All** (ages, sex, race, Hispanic origin). Only `premature_all_causes` changes ages. |
| **4. Select year and month** | The part's years (2018–2022 or 2013–2017): click the first year, Shift-click the last. Exactly five years. |
| **5. Select weekday, autopsy, and place of death** | Leave all at **All**. |
| **6. Select underlying cause of death** | Per the cause list. |
| **7. Other options** | Tick **Export Results**, **Show Totals**, **Show Zero Values** and **Show Suppressed Values**. Leave precision at its default. If a query times out, raise **Data Access Timeout** to its largest value and send again. |

### National setup (age × sex)

The same as the county setup, with two changes:

| Step | What to set |
| :--- | :--- |
| **1. Organize table layout** | **Group Results By:** `Ten-Year Age Groups`. **And By:** `Sex` (some pages say `Gender`). The other boxes: None. **Measures:** Deaths, Population, Crude Rate; tick its interval and SE too. (Age-adjusted rates are not offered with age grouping; that is expected.) |
| **3. Select demographics** | **All** ages (`*All*` on the Ten-Year Age Groups tab), both sexes, all races. If you just did `premature_all_causes`, check this. |

Steps 2, 4, 5 and 7 are as in the county setup. The result has about 24 rows (11 age groups plus "Not
Stated", for each sex); a file with only 1 or 2 rows means Step 1's grouping did not take.

## After each export

1. Find the downloaded file. It is named after the database, for example
   `Underlying Cause of Death, 2018-2024, Single Race.tsv` (your browser may add `(1)`, `(2)`).
2. **Rename** it to the cause name (lowercase, underscores, keep `.tsv`), and **move** it into the
   part's folder.
3. **Tick it off** in the checklist at the end. Then go back to the **Request Form** tab and change only
   what the next export needs.

Tip: rename each file immediately. Downloads all start with the same name, and they are easy to mix up.

## Part A: national, 2018–2022, for Round 29 (3 files; do first)

1. Open <https://wonder.cdc.gov/ucd-icd10-expanded.html> ("Underlying Cause of Death, 2018–2024, Single
   Race"). Read the data use restrictions and click **I Agree** (once per browser session).
2. Apply the **national setup**, with Step 4 = **2018, 2019, 2020, 2021, 2022**.
3. Export these causes, in order, into `external_data/wonder/ucd/2018-2022/national_age_sex/`:
   1. `all_causes.tsv`
   2. `heart_disease.tsv`
   3. `drug_overdose.tsv`

Then tell me: these three unblock Round 29.

## Part B: national, 2018–2022, the other causes (10 files)

Same database and national setup as Part A. Same folder (`ucd/2018-2022/national_age_sex/`):

4. `cancer.tsv`
5. `unintentional_injury.tsv`
6. `suicide.tsv`
7. `diabetes.tsv`
8. `stroke.tsv`
9. `clrd.tsv`
10. `liver_disease.tsv`
11. `kidney_disease.tsv`
12. `alcohol_induced.tsv`
13. `firearm.tsv`

No national `premature_all_causes`: the engine uses the national `all_causes` rates for the age groups
under 75.

## Part C: county, 2018–2022, six more causes (6 files)

Same database. Switch to the **county setup**: Step 1 **Group Results By** `County`, **And By** `None`,
and re-tick the crude rate's interval and SE if they were cleared. Years stay 2018–2022. Folder:
`ucd/2018-2022/county/` (next to your first eight files, which stay as they are):

1. `stroke.tsv`
2. `clrd.tsv`
3. `liver_disease.tsv`
4. `kidney_disease.tsv`
5. `alcohol_induced.tsv`
6. `firearm.tsv`

Each county file has about 3,142 rows. Far fewer means **Show Zero Values** was off.

## Part D: county, 2013–2017, all causes (14 files)

**A different database:** open <https://wonder.cdc.gov/ucd-icd10.html> ("Underlying Cause of Death,
1999–2020"). Click **I Agree** again. This database does **not** keep your settings from the other one,
so set the **county setup** from scratch, with these differences:

- **Step 3:** race uses the older (bridged-race) categories; leave it at **All**, as before. Sex may be
  labelled `Gender`; leave it at **All**.
- **Step 4:** select **2013, 2014, 2015, 2016, 2017** (click 2013, Shift-click 2017). Not 2018–2020.
- The file downloads as `Underlying Cause of Death, 1999-2020.tsv`.
- Everything else, including the Step 6 tabs and labels, is the same. If a cause label or its codes
  differ, stop and ask.

Folder: `ucd/2013-2017/county/`. Export in this order (`premature_all_causes` last, then reset Step 3):

1. `all_causes.tsv`
2. `heart_disease.tsv`
3. `drug_overdose.tsv`
4. `cancer.tsv`
5. `unintentional_injury.tsv`
6. `suicide.tsv`
7. `diabetes.tsv`
8. `stroke.tsv`
9. `clrd.tsv`
10. `liver_disease.tsv`
11. `kidney_disease.tsv`
12. `alcohol_induced.tsv`
13. `firearm.tsv`
14. `premature_all_causes.tsv` (ages under 75; **then set Step 3 back to `*All*`**)

The county count can differ slightly from 2018–2022 (a few counties were renamed or merged around
2015); anything above 3,100 rows is fine.

## Part E: national, 2013–2017 (13 files)

Same database as Part D (1999–2020). Switch to the **national setup**: Step 1 **Group Results By**
`Ten-Year Age Groups`, **And By** `Sex`/`Gender`; check that Step 3 ages are back to `*All*`. Years
stay 2013–2017. Folder: `ucd/2013-2017/national_age_sex/`. The same 13 causes as Parts A and B, in this
order: `all_causes`, `heart_disease`, `drug_overdose`, `cancer`, `unintentional_injury`, `suicide`,
`diabetes`, `stroke`, `clrd`, `liver_disease`, `kidney_disease`, `alcohol_induced`, `firearm`.

## Part F (optional, last): drug involvement, 2018–2022 (8 files)

This one counts overdose deaths by the drug **involved**, which needs the Multiple Cause database. Skip
it until everything above is done; expect heavy suppression in county files.

1. Open <https://wonder.cdc.gov/mcd-icd10-expanded.html> ("Multiple Cause of Death, 2018–2024, Single
   Race"), click **I Agree**, and set the **county setup** with years **2018–2022**.
2. **Step 6 has two parts here.** In the **underlying cause** part, open the **Drug/Alcohol Induced
   Causes** tab and select the same four overdose items as `drug_overdose`. In the **multiple cause**
   part, open the **ICD-10 Codes** tab and select the codes below. (In the code tree they are under
   T36-T50, Poisoning by drugs; expand with the `+` signs and Ctrl-click. If a code shows sub-codes,
   select the code itself, which includes them.)

| Save as | Multiple-cause codes |
| :--- | :--- |
| `any_opioid.tsv` | T40.0, T40.1, T40.2, T40.3, T40.4, T40.6 (Ctrl-click all six) |
| `synthetic_opioid.tsv` | T40.4 |
| `cocaine.tsv` | T40.5 |
| `psychostimulant.tsv` | T43.6 |

3. Export the four into `mcd/2018-2022/county/`.
4. Switch to the **national setup** and export the same four again into `mcd/2018-2022/national_age_sex/`.

If the multiple-cause part looks different from this description, stop and send a screenshot.

## Checklist

```text
2018-2022 county (ucd/2018-2022/county/)         done 2026-11-18, structure-checked
[x] all_causes  [x] heart_disease  [x] drug_overdose  [x] premature_all_causes
[x] cancer  [x] unintentional_injury  [x] suicide  [x] diabetes

Part A  2018-2022 national (ucd/2018-2022/national_age_sex/)   ROUND 29 NEEDS THESE
[ ] 1 all_causes   [ ] 2 heart_disease   [ ] 3 drug_overdose

Part B  2018-2022 national (same folder)
[ ] 4 cancer  [ ] 5 unintentional_injury  [ ] 6 suicide  [ ] 7 diabetes  [ ] 8 stroke
[ ] 9 clrd  [ ] 10 liver_disease  [ ] 11 kidney_disease  [ ] 12 alcohol_induced  [ ] 13 firearm

Part C  2018-2022 county (ucd/2018-2022/county/)
[ ] 1 stroke  [ ] 2 clrd  [ ] 3 liver_disease  [ ] 4 kidney_disease  [ ] 5 alcohol_induced  [ ] 6 firearm

Part D  2013-2017 county (ucd/2013-2017/county/)   1999-2020 database
[ ] 1 all_causes  [ ] 2 heart_disease  [ ] 3 drug_overdose  [ ] 4 cancer  [ ] 5 unintentional_injury
[ ] 6 suicide  [ ] 7 diabetes  [ ] 8 stroke  [ ] 9 clrd  [ ] 10 liver_disease  [ ] 11 kidney_disease
[ ] 12 alcohol_induced  [ ] 13 firearm  [ ] 14 premature_all_causes (then reset Step 3)

Part E  2013-2017 national (ucd/2013-2017/national_age_sex/)
[ ] all_causes  [ ] heart_disease  [ ] drug_overdose  [ ] cancer  [ ] unintentional_injury
[ ] suicide  [ ] diabetes  [ ] stroke  [ ] clrd  [ ] liver_disease  [ ] kidney_disease
[ ] alcohol_induced  [ ] firearm

Part F  optional: drug involvement (mcd/2018-2022/county/ and mcd/2018-2022/national_age_sex/)
[ ] county: any_opioid  synthetic_opioid  cocaine  psychostimulant
[ ] national: any_opioid  synthetic_opioid  cocaine  psychostimulant
```

When a part is done, tell me. I check each file's notes and structure only (database, years, grouping,
cause codes, age filter, row count, suppressed and zero rows) and compute no associations. If a file
fails, I will tell you which step to change, and you re-export just that one.

## Mistakes and re-exports

- **Before a study registers the file:** re-export and overwrite the file with the same name. Only the
  2018–2022 files are being registered (Round 29); the others are free to redo until a round uses them.
- **After it is registered:** never overwrite. Save the new file as `<name>_v2.tsv` and tell me; the
  manifest pins each file's SHA-256.
- **Wrong database, years, ages or grouping:** the check catches these from the file's notes; re-export.

## Final layout

```text
external_data/wonder/
  ucd/2018-2022/county/<cause>.tsv             14 files (8 done + Part C)
  ucd/2018-2022/national_age_sex/<cause>.tsv   13 files (Parts A, B)
  ucd/2013-2017/county/<cause>.tsv             14 files (Part D)
  ucd/2013-2017/national_age_sex/<cause>.tsv   13 files (Part E)
  mcd/2018-2022/county/<drug>.tsv               4 files (Part F, optional)
  mcd/2018-2022/national_age_sex/<drug>.tsv     4 files (Part F, optional)
```

## Not planned (do not download)

- **Natality** (WONDER names only counties of 100,000+ people) and **infant deaths** (state only): they
  need a parser that does not exist yet. A round will ask if they are needed.
- **Skip entirely:** environmental data (county series stop around 2011), provisional mortality (not
  final, not citable), population estimates (the engine uses ACS), and VAERS/TB/AIDS/STD.

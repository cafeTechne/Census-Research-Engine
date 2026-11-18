# CDC WONDER exports: a step-by-step checklist

**For the owner, done by hand.** You download **county** death counts from the WONDER web form. The
national reference rates come from WONDER's official API, which the engine fetches itself in Round 29;
the API cannot return state or county death data, so county files are the only manual part.

**What Round 29 needs: 3 files** (exports 1–3 below, about 10 minutes in total). Exports 4–8 are
optional extras for later studies; do them now only if you have time. Everything else ("Later" at the
end) waits until a round asks for it.

## Quick answers

- **File format: leave it exactly as WONDER gives it.** WONDER has one export format: a tab-delimited
  text file (`.txt`; in effect a TSV). There is no Excel or CSV option, and you need none. **Do not open
  the file in Excel and save it**: that strips WONDER's notes at the bottom (the engine reads them), can
  drop leading zeros from county codes, and changes the file's fingerprint (SHA-256), which the study
  pins. Only rename the file; never edit it.
- **Do not study the numbers.** The study must be registered before anyone looks at county results. The
  results table WONDER shows on screen after each export is fine to scroll past; if you do look closely
  at something, tell me, and the study report will say so.
- **If anything on the form looks different from this page** (a label, a missing option), stop and send
  me a screenshot or the label text. Do not guess.

## Part 1: one-time setup (5 minutes)

1. **Make the folder** on the machine that runs the engine (the desktop), from the project folder:

   ```bash
   mkdir -p external_data/wonder/ucd/2018-2022/county
   ```

   `external_data/` is gitignored, so nothing here is ever committed.
2. **Open the database:** <https://wonder.cdc.gov/ucd-icd10-expanded.html> ("Underlying Cause of Death,
   2018–2024, Single Race"). Use this one database for every export on this page.
3. **Data use restrictions page:** read it and click **I Agree**. You agree again in each new browser
   session. It forbids publishing counts of 1–9 (or rates based on them) for areas below national level,
   and any attempt to identify people; the engine enforces this in its outputs.
4. You are now on the **Request Form** tab, with Steps 1–7 down the page. Part 2 sets them once; for
   later exports you change only one or two steps.

## Part 2: base settings (set once, for export 1)

Go down the form in order. Anything not mentioned: leave at its default.

| Step | What to set |
| :--- | :--- |
| **1. Organize table layout** | **Group Results By:** `County`. **And By:** `None` (leave the other boxes at None). **Measures:** Deaths, Population and Crude Rate are ticked by default; also tick Crude Rate's **95% Confidence Interval** and **Standard Error**. Leave **Age Adjusted Rate** and its interval and SE **unticked**: WONDER refuses them with county grouping, and the study does not use them (it builds expected deaths from national rates). Leave rates per **100,000**. |
| **2. Select location** | Leave **`*All* (The United States)`**. All-US files also cover the OH/PA replication. County is the decedent's county of **residence**; there is nothing to choose. |
| **3. Select demographics** | Leave every box at **All** (all ages, both sexes, all races, all Hispanic origins). Export 3 changes ages; it says how. |
| **4. Select year and month** | Select exactly **2018, 2019, 2020, 2021, 2022**: click 2018, then Shift-click 2022 (or Ctrl-click each). Not 2023 or 2024: the years must match ACS 2018–2022. |
| **5. Select weekday, autopsy, and place of death** | Leave all at **All**. |
| **6. Select underlying cause of death** | Set per export below. |
| **7. Other options** | Tick **Export Results**, **Show Totals**, **Show Zero Values** and **Show Suppressed Values**. Leave precision at its default. If a query times out, raise **Data Access Timeout** to its largest value and send again. |

## Part 3: the exports, in this order

For **each** export: set the steps it names, click **Send** (at the bottom; the button at the top works
too), wait for the download, then do the **after each export** steps.

**After each export:**

1. Find the downloaded file. It is named after the database, for example
   `Underlying Cause of Death, 2018-2024, Single Race.txt` (your browser may add `(1)`, `(2)`).
2. **Rename** it to the exact name in the table (lowercase, underscores, ending `.txt`) and **move** it
   into `external_data/wonder/ucd/2018-2022/county/`.
3. **Tick it off** in the checklist. Then go back to the **Request Form** tab: WONDER keeps your
   settings, so you only change what the next export says.

### Required for Round 29

| # | Save as | Change from the previous export |
| :--- | :--- | :--- |
| 1 | `heart_disease.txt` | Base settings (Part 2). **Step 6:** open the **ICD-10 113 Cause List** tab and select `#Diseases of heart (I00-I09,I11,I13,I20-I51)`. |
| 2 | `drug_overdose.txt` | **Step 6:** open the **Drug/Alcohol Induced Causes** tab. Ctrl-click to select exactly these four, and nothing else: `Drug poisonings (overdose) Unintentional (X40-X44)`, `Drug poisonings (overdose) Suicide (X60-X64)`, `Drug poisonings (overdose) Homicide (X85)`, `Drug poisonings (overdose) Undetermined (Y10-Y14)`. |
| 3 | `premature_all_causes.txt` | **Step 6:** go back to the **ICD-10 113 Cause List** tab and select `*All* (All Causes of Death)`. **Step 3:** on the **Ten-Year Age Groups** tab, select `< 1 year` through `65-74 years` (click the first, Shift-click the last: nine groups, every age under 75). |

Labels may be worded slightly differently on your screen; match on the ICD-10 codes in brackets. If the
codes do not match, stop and ask.

### Optional now (useful for later studies)

First **reset Step 3** to **All Ages** (select `*All*` on the Ten-Year Age Groups tab). Then, for each
row, change only **Step 6** (all on the **ICD-10 113 Cause List** tab unless noted):

| # | Save as | Step 6 selection |
| :--- | :--- | :--- |
| 4 | `all_causes.txt` | `*All* (All Causes of Death)` |
| 5 | `cancer.txt` | `#Malignant neoplasms (C00-C97)` |
| 6 | `unintentional_injury.txt` | `#Accidents (unintentional injuries) (V01-X59,Y85-Y86)` |
| 7 | `suicide.txt` | `#Intentional self-harm (suicide) (*U03,X60-X84,Y87.0)` |
| 8 | `diabetes.txt` | `#Diabetes mellitus (E10-E14)` |

### Checklist

```text
[ ] 1 heart_disease.txt          (required)
[ ] 2 drug_overdose.txt          (required)
[ ] 3 premature_all_causes.txt   (required; ages under 75)
[ ] 4 all_causes.txt             (optional; Step 3 reset to All Ages first)
[ ] 5 cancer.txt                 (optional)
[ ] 6 unintentional_injury.txt   (optional)
[ ] 7 suicide.txt                (optional)
[ ] 8 diabetes.txt               (optional)
```

When you are done, the folder should look like this (exports 4–8 only if you did them):

```text
external_data/wonder/ucd/2018-2022/county/
  heart_disease.txt
  drug_overdose.txt
  premature_all_causes.txt
```

Then tell me. Round 29's first step (`scripts/wonder_inventory.py`) reads each file's notes and checks
the database, years, grouping, cause selection, row count (about 3,140 counties; far fewer means "Show
Zero Values" was off) and suppressed rows. It checks structure only and computes no associations. If a
file fails a check, I will tell you exactly which step to change and you re-export just that one.

## Mistakes and re-exports

- **Before the study is registered:** just re-export and overwrite the file with the same name.
- **After it is registered:** never overwrite. Save the new file as `<name>_v2.txt` and tell me; the
  manifest pins each file's SHA-256.
- **Wrong database, years or ages:** the inventory catches these from the file's notes; re-export.

## Fallback: national files by hand (only if Round 29 asks)

If the API turns out not to serve this database, Round 29 will ask for three national files instead.
Use Part 2's settings with two changes: **Step 1 Group Results By:** `Ten-Year Age Groups`, **And By:**
`Sex`, with no age-adjusted measures; **Step 3:** All Ages. Export the Step 6 selections of exports 1,
2 and 4 above as `heart_disease.txt`, `drug_overdose.txt` and `all_causes.txt` into
`external_data/wonder/ucd/2018-2022/national_age_sex/`. Do not do this unless asked.

## Later (do not do yet; a round will ask)

- **More causes, 2018–2022** (county; same steps): `stroke` (#Cerebrovascular diseases, I60-I69),
  `clrd` (#Chronic lower respiratory diseases, J40-J47), `liver_disease` (#Chronic liver disease and
  cirrhosis, K70,K73-K74), `kidney_disease` (#Nephritis, nephrotic syndrome and nephrosis), and, from
  other tabs, `alcohol_induced` (Drug/Alcohol Induced Causes: all alcohol-induced categories) and
  `firearm` (Injury Intent and Mechanism: Firearm, all intents).
- **The 2013–2017 window**, from the 1999–2020 bridged-race database, into `ucd/2013-2017/county/`,
  for change analyses matched to ACS 2013–2017.
- **Drug involvement, 2018–2022**, from the Multiple Cause of Death single-race database, into
  `mcd/2018-2022/county/`: the drug-overdose underlying causes plus a multiple cause of
  `any_opioid` (T40.0–T40.4, T40.6), `synthetic_opioid` (T40.4), `cocaine` (T40.5) or
  `psychostimulant` (T43.6). Expect heavy suppression; Round 27's smoothing handles it.
- **Natality** (2016 onward; WONDER names only counties of 100,000+ people) and **infant deaths**
  (state only): needs a parser that does not exist yet.
- **Skip entirely:** environmental data (county series stop around 2011), provisional mortality (not
  final, not citable), population estimates (the engine uses ACS), and VAERS/TB/AIDS/STD.

Full layout once everything exists (the engine writes the `national_age_sex` API files itself):

```text
external_data/wonder/
  ucd/2018-2022/county/<cause>.txt            you, by hand (this page)
  ucd/2018-2022/national_age_sex/<cause>.xml  the engine, via the API (Round 29)
  ucd/2013-2017/county/<cause>.txt            later
  mcd/2018-2022/county/<drug>.txt             later
```

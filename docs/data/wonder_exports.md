# CDC WONDER exports: what to download and where to put it

**For the owner, done by hand.** The engine never automates WONDER: county data comes only through the
web form, and the data-use agreement and bot checks rule out scripting. This page lists the exports
Rounds 29 and later will use, the exact form settings the parser needs, and the folder layout. Work
through the tiers in order; Tier 1 alone unblocks Round 29.

## Before you start

- **Data-use agreement.** You accept it at the start of each WONDER session. For sub-national data it
  forbids presenting counts of 9 or fewer, or rates based on them, and any attempt to identify
  individuals. The engine will enforce this in its outputs (Round 29), and raw exports never go into the
  repository or a release.
- **Pre-registration.** Exporting is fine. Try not to study the county numbers on screen before Round
  29's study is registered. If you do look closely at something, say so, and the study report will
  disclose it.
- **Where files live.** In the repository on the machine that runs the engine:
  `external_data/wonder/` (gitignored). Never edit an exported file. The parser requires WONDER's
  footer, and manifests pin each file's SHA-256. If you need to re-export after a study is registered,
  save the new file under a new name ending in `_v2`; never overwrite the original.

## Form settings for every mortality export

Use **"Underlying Cause of Death"** (UCD). For 2018 onward, use the single-race database. For years
before 2018 (Tier 2), use the 1999–2020 bridged-race database. Race is not grouped, so totals are
comparable across the two.

| Form section | Setting |
| :--- | :--- |
| 1. Group results by | As given in the table for that export (County; or Ten-Year Age Groups + Sex; or State + Ten-Year Age Groups + Sex). "Sex" may be labelled "Gender" in older databases. |
| 1. Measures | Deaths, Population and Crude Rate are default. Also tick: Crude Rate 95% CI and Standard Error. For County exports only, also tick Age Adjusted Rate, its 95% CI and its Standard Error. |
| 2. Location | All states (the whole US), unless the table says otherwise. All-US county files also give us held-out states (OH/PA) for replication. |
| 3. Demographics | Leave age, sex, race and Hispanic origin at "All", except the premature-death export (ages under 75; see the cause table). |
| 4. Year | The data years of the window, ticking each year (2018–2022 for Tier 1). |
| 6. Cause of death | As given in the cause table below. |
| 7. Other options | **Export Results: ticked. Show Totals: ticked. Show Zero Values: ticked. Show Suppressed Values: ticked.** Leave precision and the age-adjustment standard (2000 US) at their defaults. |

Then **Send**. The browser downloads a `.txt` file named after the database. Rename it as the tables
below say, and move it into its folder. The **Request Form** tab keeps your settings, so for the next
export change only the cause.

## Folder layout

```text
external_data/wonder/
  ucd/2018-2022/county/<cause>.txt              Group by: County
  ucd/2018-2022/national_age_sex/<cause>.txt    Group by: Ten-Year Age Groups, Sex
  ucd/2018-2022/state_age_sex/<cause>.txt       Group by: State, Ten-Year Age Groups, Sex
  ucd/2013-2017/...                             same three folders (Tier 2)
  mcd/2018-2022/county/<drug>.txt               Multiple Cause of Death (Tier 2)
  mcd/2018-2022/national_age_sex/<drug>.txt
  natality/2018-2022/{state,county}/<measure>.txt   (Tier 3)
  infant_deaths/2018-2022/state/all_causes.txt      (Tier 3)
```

Names are lowercase with underscores, exactly as in the tables. The data years in the folder name must
match the years ticked in the form; the inventory check (below) compares them with the file's footer.

## Tier 1: unblocks Round 29 (2018–2022, the same years as the ACS 2018–2022 release)

Make three exports per cause (county, national by age and sex, state by age and sex), except
`premature_all_causes`, which is county only: its age-specific reference rates come from
`all_causes`. That is 22 files.

| `<cause>` | Section 6 selection (ICD-10 113 Cause List unless noted) |
| :--- | :--- |
| `all_causes` | No cause filter |
| `premature_all_causes` | No cause filter; section 3 ages: every ten-year group from "< 1 year" to "65–74 years" (county export only) |
| `heart_disease` | #Diseases of heart (I00–I09, I11, I13, I20–I51) |
| `cancer` | #Malignant neoplasms (C00–C97) |
| `unintentional_injury` | #Accidents (unintentional injuries) (V01–X59, Y85–Y86) |
| `drug_overdose` | ICD-10 Codes: X40–X44, X60–X64, X85, Y10–Y14 (all intents). Or use the "Drug/Alcohol Induced Causes" drug-poisoning categories, which select the same codes. |
| `suicide` | #Intentional self-harm (suicide) (*U03, X60–X84, Y87.0) |
| `diabetes` | #Diabetes mellitus (E10–E14) |

## Tier 2: worth having (do after Tier 1)

**a. More causes, 2018–2022.** Same three exports per cause (18 files):

| `<cause>` | Selection |
| :--- | :--- |
| `stroke` | #Cerebrovascular diseases (I60–I69) |
| `clrd` | #Chronic lower respiratory diseases (J40–J47) |
| `liver_disease` | #Chronic liver disease and cirrhosis (K70, K73–K74) |
| `kidney_disease` | #Nephritis, nephrotic syndrome and nephrosis (N00–N07, N17–N19, N25–N27) |
| `alcohol_induced` | "Drug/Alcohol Induced Causes": all alcohol-induced categories |
| `firearm` | "Injury Mechanism & All Other Leading Causes": Firearm (all intents) |

**b. The 2013–2017 window** (bridged-race database, 1999–2020), for change analyses matched to ACS
2013–2017: Tier 1's 22 files again under `ucd/2013-2017/`.

**c. Drug involvement, 2018–2022** (Multiple Cause of Death, single race). Underlying cause = the
`drug_overdose` codes above, **and** a multiple cause containing:

| `<drug>` | Multiple-cause codes |
| :--- | :--- |
| `any_opioid` | T40.0, T40.1, T40.2, T40.3, T40.4, T40.6 |
| `synthetic_opioid` | T40.4 (mostly fentanyl) |
| `cocaine` | T40.5 |
| `psychostimulant` | T43.6 (mostly methamphetamine) |

Export County and national by age and sex for each (8 files). Expect heavy county suppression;
Round 27's smoothing handles it.

## Tier 3: optional, later

- **Natality** (expanded, 2016 onward). WONDER identifies only counties of 100,000+ people; smaller ones
  pool into "Unidentified Counties". Export State and County, measure Births, one file per indicator:
  - `all_births` (no filter);
  - `low_birthweight` (birthweight under 2,500 g);
  - `preterm` (OE gestational age under 37 weeks);
  - `teen_births` (mother's age under 20);
  - `late_prenatal_care` (care not begun in the first trimester).

  County Health Rankings already gives county low birth weight, so this is lower priority. The parser
  for natality comes in a later round.
- **Infant deaths** (Linked Birth/Infant Death), State only, 2018–2022: `all_causes`.

**Skip:**

- environmental data (WONDER's county PM2.5 and temperature series stop around 2011);
- provisional mortality (counts change after release, so it is not citable);
- population estimates (the engine uses ACS);
- VAERS, TB, AIDS and STD (not our questions).

## Checking your exports

Round 29 starts with `scripts/wonder_inventory.py`, which can be pulled forward on request. It reads
every file's footer and writes `external_data/wonder/INVENTORY.md`, which lists for each file:

- the database, years, group-by, cause selection and SHA-256;
- the row count, and the number of suppressed and zero rows;
- any mismatch with the folder or file name. For example, an all-US county file has about 3,140 rows;
  far fewer means "Show Zero Values" was off.

It checks structure only and computes no associations.

## Rough effort

Tier 1 is 22 exports at a couple of minutes each, once the form is set up. Tier 2 is about 48 more.
Tier 3 is about 11.

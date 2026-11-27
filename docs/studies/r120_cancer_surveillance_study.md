# Pre-Registered Study: County Cancer Mortality Surveillance, Spatial Disease Mapping, and Poverty Designation (2018–2022)

**Date:** 2026-11-26  
**Engine version:** `v0.115.0` (with 3 manifest-integration bugfixes uncovered during execution; see Section 5)  
**Review status:** Author self-review, not independent.  
**Data sources:** U.S. Census Bureau ACS 5-Year 2018–2022 (`B01001`, `B17001`, plus Census VRE replicates) and owner manual CDC WONDER UCD 2018–2022 county and national age × sex cancer mortality exports (`external_data/wonder/ucd/2018-2022/`). Zero suppressed counts (1–9) exist in the study counties and no raw WONDER exports are included in this report.

---

## 1. Pre-Registration and Provenance

Both manifests were validated and hashed prior to examining any outcome associations:

| Role | Geography | Manifest | SHA-256 | Analysis status | Deviations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Primary | MI (`26`), NY (`36`); $N = 145$ counties | `examples/manifests/r120_mi_ny_cancer_surveillance.json` | `7b49685d01bac98bbb5fe919f71ec2d0e373157c030ef378b2429f6014108708` | `confirmatory` | None (`[]`) |
| Held-out replication | OH (`39`), PA (`42`); $N = 155$ counties | `examples/manifests/r120_oh_pa_cancer_replication.json` | `622823ab064b60ed24485b6b89430ecc048f706928648850e80cfbe281bf78cd` | `confirmatory` | None (`[]`) |

All five pre-registered analyses ran offline against cached local data (`studies_output/r120_mi_ny_confirmatory/` and `studies_output/r120_oh_pa_confirmatory/`):

1. **`dm_cancer` (`disease_map`, BYM2 `method="B3"`, threshold `1.2`):** Observed 5-year cancer deaths vs. age-sex indirectly standardized expected deaths (`E_cancer`), using Queen contiguity with nearest-component bridges where states/peninsulas are disconnected.
2. **`scan_cancer` (`spatial_scan`, Kulldorff Poisson, `max_share=0.5`, 999 Monte Carlo replicates):** High-rate cluster detection on `cancer_numerator` vs. `E_cancer`.
3. **`des_poverty` (`designation`, arcsine Fay–Herriot `rule="prob80"`, 200 parametric bootstrap draws):** Accuracy of designating counties with true ACS poverty rate $\ge 15\%$.
4. **`ag_counts` (`agreement`, `first="cancer_numerator"`, `second="E_cancer"`):** Mean difference (`E_cancer - cancer_numerator`), observed Lin's CCC (Fisher-$z$ jackknife), and quintile weighted $\kappa$.
5. **`reg_cancer` (`fit_replicate`, Poisson HC3 + 80 Census VRE refits, `exposure="E_cancer"`, `target="conservative"`):** `cancer_numerator ~ poverty + C(GEOID.str[:2])`.

Multiple comparisons across `H1–H5` were adjusted with Holm's procedure separately in MI/NY and OH/PA at nominal $\alpha = 0.10$ (90% intervals).

---

## 2. Confirmatory Hypothesis Results

### 2.1 Primary Region: Michigan & New York ($N = 145$ counties)

| ID | Analysis | Statistic | Estimate | SE | 90% CI | Holm $p$ | Verdict ($\alpha = 0.10$) |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | :--- |
| **H1** | `dm_cancer` | `relative_risk` (Wayne County, MI `26163`) | `1.140` | `0.0075` | `1.126` to `1.154` | `4.95e-68` | **Supported** |
| **H2** | `scan_cancer` | `primary_rr` (Sanilac-centered, 112 counties) | `1.286` | — | — | `0.0015` | **Supported** |
| **H3** | `des_poverty` | `ppv` (`prob80`, poverty $\ge 15\%$, null `0.70`) | `0.960` | `0.0320` | `0.893` to `0.998` | `8.17e-16` | **Supported** |
| **H4** | `ag_counts` | `bias` (`E_cancer - observed`, null `0`) | `+95.3` | `71.57` | `-22.5` to `+213.0` | `0.366` | **Not supported** |
| **H5** | `reg_cancer` | `coefficient` (`poverty`, per 1 pp, conditional on state) | `+0.0030` | `0.0044` | `-0.0042` to `+0.0102` | `0.366` | **Not supported** |

### 2.2 Held-Out Replication: Ohio & Pennsylvania ($N = 155$ counties)

| ID | Analysis | Statistic | Estimate | SE | 90% CI | Holm $p$ | Verdict ($\alpha = 0.10$) |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | :--- |
| **H1** | `dm_cancer` | `relative_risk` (Cuyahoga County, OH `39035`) | `1.111` | `0.0084` | `1.096` to `1.126` | `1.86e-35` | **Replicated** |
| **H2** | `scan_cancer` | `primary_rr` (Scioto-centered, 15 counties) | `1.284` | — | — | `0.0005` | **Replicated** |
| **H3** | `des_poverty` | `ppv` (`prob80`, poverty $\ge 15\%$, null `0.70`) | `0.959` | `0.0289` | `0.905` to `1.000` | `6.30e-19` | **Replicated** |
| **H4** | `ag_counts` | `bias` (`E_cancer - observed`, null `0`) | `-125.2` | `20.35` | `-158.7` to `-91.8` | `2.26e-09` | **Supported (diverges from MI/NY)** |
| **H5** | `reg_cancer` | `coefficient` (`poverty`, per 1 pp, conditional on state) | `+0.0121` | `0.0030` | `+0.0071` to `+0.0171` | `6.36e-05` | **Supported (diverges from MI/NY)** |

---

## 3. Secondary & Descriptive Diagnostics

- **BYM2 `B3` spatial smoothing (`dm_cancer`, validated in both regions):**
  - **MI/NY:** Smoothed county RR spans `0.717–1.297`; $\sigma = 0.171$, $\phi = 0.95$ (strongly spatially structured); `7` counties have $P(\text{RR} > 1.2) \ge 0.80$. Three bridge edges joined Michigan's Upper/Lower Peninsulas and Michigan/New York (`['26097','26047']`, `['36013','26147']`, `['36085','26147']`).
  - **OH/PA:** Smoothed county RR spans `0.847–1.631`; $\sigma = 0.111$, $\phi = 0.65$; `21` counties have $P(\text{RR} > 1.2) \ge 0.80$ (single connected Queen graph, zero bridges needed).
- **Kulldorff spatial scan (`scan_cancer`, validated `confirmatory=True`, `validated_p=True`):**
  - **MI/NY:** Primary cluster centered at Sanilac County, MI (`26151`, 112 counties across Michigan and upstate/western New York, `RR = 1.286`, $p = 0.001$), reflecting the sharp contrast between lower-SMR downstate NY/NYC and higher-SMR Michigan/upstate NY.
  - **OH/PA:** Compact primary cluster centered at Scioto County, OH (`39145`, 15 southern/Appalachian Ohio counties, `RR = 1.284`, $p = 0.001$).
- **Poverty $\ge 15\%$ screening accuracy (`des_poverty`, `prob80`):**
  - **MI/NY:** 27 counties designated; PPV `0.960` (90% CI `0.893–0.998`), sensitivity `0.683`, specificity `0.990`, NPV `0.898`.
  - **OH/PA:** 21 counties designated; PPV `0.959` (90% CI `0.905–1.000`), sensitivity `0.591`, specificity `0.993`, NPV `0.896`.
- **Observed vs. expected count agreement (`ag_counts`):**
  - **MI/NY:** Lin's CCC `0.971` (90% CI `0.950–0.983`), quintile $\kappa = 0.862$ (`0.809–0.916`).
  - **OH/PA:** Lin's CCC `0.993` (90% CI `0.989–0.995`), quintile $\kappa = 0.903$ (`0.859–0.947`); observed cancer deaths exceed national age-sex-expected counts by `+125.2` deaths/county on average (90% CI `+91.8` to `+158.7`).
- **Regional divergence on poverty (`H5`):**
  - Unlike Round 29's premature all-cause and heart-disease mortality (which showed positive poverty gradients in both regions), age-standardized cancer mortality shows a strong positive poverty gradient in OH/PA ($\beta = +0.0121$/pp, $p = 6.36 \times 10^{-5}$) but no statistically significant gradient in MI/NY ($\beta = +0.0030$/pp, $p = 0.366$), where New York has substantially lower cancer mortality than Michigan overall (`C(GEOID.str[:2])[T.36] = -0.208`, $p = 4.9 \times 10^{-6}$). Ecologic cross-sectional design and unadjusted spatial residual correlation in `reg_cancer` remain standing limitations.

---

## 4. Author Self-Review (Not Independent)

- **Strengths:** Both regions achieved `confirmatory` status with zero deviations; pre-registered hashes are immutable; zero suppressed counts occurred; all 5 methods used validated inferential procedures with explicit uncertainty intervals and Holm adjustment.
- **Limitations:**
  - `reg_cancer` uses independent-area HC3 + VRE SEs (`dm_cancer` found high spatial structure $\phi = 0.65\text{–}0.95$, so spatial residual dependence is not accounted for in `H5`).
  - `ag_counts` compares raw counts (`cancer_numerator` vs. `E_cancer`), so CCC and quintile $\kappa$ are dominated by county population scale; `bias` (`E_cancer - observed`) is the interpretable regional offset.
  - All findings are ecologic and cross-sectional (2018–2022) and do not support individual-level or causal inference.

---

## 5. Engine & Platform Friction Log (Empirical Findings from v0.115.0)

Running a real end-to-end study surfaced **three concrete manifest-runner bugs** in `census/manifest/methods.py` that synthetic unit tests had missed (all three fixed and regression-tested in `tests/test_round120_study_fixes.py`), plus two minor UX observations:

1. **Bug fixed — `disease_map` auto-edges in `run_manifest`:** `_run_disease_map` raised `ValueError` whenever `args.edges` was omitted because `run_manifest` never populated `ctx["edges"]`. Fixed to auto-derive connected Queen contiguity edges (with nearest-component bridges) from cartographic boundaries, matching `workflows_geo.py`.
2. **Bug fixed — external/WONDER variable validation in `spatial_scan`, `disease_map`, and `agreement`:** All three methods declared `external_outcome=True`, but their `before_spatial` validators checked `names` only and rejected external `<name>_numerator` columns. Fixed to match `_check_smr`.
3. **Bug fixed — `_stat_spatial_scan` confirmatory key mismatch:** `_stat_spatial_scan` checked `res.get("validated", False)`, whereas `census.scan.spatial_scan()` returns `confirmatory` / `validated_p`. Every `spatial_scan` manifest hypothesis was silently failing closed as `not_tested`. Fixed to read `confirmatory` / `validated_p`.
4. **Patched — `methods.md` target labels & registry citations (`census/manifest/methods_text.py`):** Previously `methods.md` printed `(`None`)` for formula-less methods and omitted method-registry citations (`riebler2016`, `moraga2023`, `kulldorff1997`, `fay_herriot1979`, `lin1989`) from `### References`. Both are now patched while keeping both legacy manifest goldens byte-identical.
5. **Layer B / Literature-tooling verdict:** During this end-to-end study, **zero need for a heavy RAG/OpenScholar stack arose**. The actual literature need was narrow and concrete: (a) ensuring every manifest method's built-in BibTeX/method citations flow cleanly into `methods.md`/`references.bib`, and (b) optionally looking up 2–3 domain-specific epidemiology papers (e.g., Appalachian vs. NYC cancer mortality disparities) via lightweight metadata lookup + BibTeX export.

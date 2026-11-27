# Round 156 Study Report: End-to-End Live Layer B → Layer A Study — County Stroke Mortality (2018–2022) BYM2 (`B3`) & E-Value QBA

**Layer A Pre-registration Protocol SHA-256:** `d49d4448713f807ebababdaea6946ea058f596dfc89c0e6e812d49e093609ca3`  
**Upstream Layer B Provenance (strictly isolated, human-reviewed before Layer A registration):**
- **SSD Index:** `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/index.sqlite` (`130` deduplicated OpenAlex + Europe PMC papers)
- **Layer B Dossier SHA-256:** `ba2b16843bde00f51dfbd5961a2fccdcee6b7b5ab551b5d37cea30d6d634fd19`
- **Layer B Seed SHA-256:** `89e7ab85b6216ee9eff1c2f61395064a0ecf6ed668707c8c33a9105e1fb2ad52` (8 DOIs from 2021–2026)

**Script:** [r156_layer_b_to_layer_a_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r156_layer_b_to_layer_a_study.py)

## Empirical Results (WONDER 2018–2022 Stroke Mortality + ACS 2020–2024 `B17001`)

| Region | Counties | BYM2 $\sigma$ / $\phi$ | Validated | Raw SMR IQR → Smoothed RR IQR | High-Exceedance Counties ($P(\text{RR} > 1.20) \ge 0.80$) | Q4 vs. Q1 Poverty Crude RR (90% CI) | E-Value (Point / CI Limit) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MI + OH (`26`, `39`) | 171 | `0.264` / `0.80` | Yes | `0.321` → `0.309` | 33 | `1.081` (`1.063`, `1.101`) | `1.38` / `1.32` |
| NY + PA (`36`, `42`) | 129 | `0.171` / `0.65` | Yes | `0.391` → `0.308` | 39 | `0.784` (`0.772`, `0.796`) | `1.87` / `1.82` |

## Publication Bundle Verification
- `verify_bundle("studies_output/r156_layer_a_stroke/bundle")` returned **`ok: true`**, `checked_files: 4`, `errors: []` (all SHA-256 digests, `methods.md`, and `references.bib` verified).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** Expected counts use regional crude rates; NY+PA crude Q4/Q1 poverty RR (`0.784`) reflects age-structure confounding from younger NYC boroughs relative to older rural counties. Zero automated WONDER access; zero raw sub-national 1–9 counts emitted.

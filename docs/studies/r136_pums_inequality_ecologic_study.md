# Round 136 Study Report: PUMS Earnings Inequality & PUMA Ecologic Fallacy Decomposition (MI & OH, 2019–2023)

**Pre-registration Protocol SHA-256:** `dd0636b298ba9db8def368168ce3af8ada51a9ca569f572864e631e5b48bf4af`  
**Script:** [r136_pums_inequality_ecologic_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r136_pums_inequality_ecologic_study.py)  
**Data:** ACS 5-Year 2019–2023 person PUMS for working-age adults (ages 25–64) with 80 successive-difference replicate weights (`PWGTP1..80`) in Michigan (`26`, primary; $N = 244{,}125$, `190,107` positive earners, 68 PUMAs) and Ohio (`39`, replication; $N = 280{,}493$, `226,425` positive earners, 90 PUMAs).

## 1. Validated Earnings Inequality (`PERNP > 0`, 90% SDR CIs)

| Metric | Michigan (`26`) | Ohio (`39`) | Validation Status |
| :--- | :---: | :---: | :---: |
| Gini | `0.4495` (`0.4476`, `0.4514`) | `0.4398` (`0.4381`, `0.4414`) | Validated |
| Atkinson ($\epsilon = 0.5$) | `0.1775` (`0.1760`, `0.1790`) | `0.1714` (`0.1700`, `0.1727`) | Validated |
| Disabled − Non-Disabled Gini Difference | `+0.0533` (`+0.0453`, `+0.0612`) | `+0.0421` (`+0.0357`, `+0.0486`) | Validated |
| Theil $T$ | `0.3760` (`0.3723`, `0.3796`) | `0.3669` (`0.3634`, `0.3704`) | Exploratory only (failed R56/R60/R62 coverage) |

## 2. PUMA Ecologic Fallacy Decomposition (Poverty `POVPIP < 100` on Disability `DIS == 1`)

| Component | Michigan (`26`, 68 PUMAs) | Ohio (`39`, 90 PUMAs) |
| :--- | :---: | :---: |
| Within-PUMA Logit Log-OR | `1.183` (`1.147`, `1.219`) | `1.260` (`1.225`, `1.294`) |
| Between-PUMA Logit Log-OR | `11.827` (`10.926`, `12.728`) | `12.564` (`11.660`, `13.469`) |
| Contextual Difference (Between − Within) | `+10.644` (`+9.746`, `+11.541`) | `+11.305` (`+10.401`, `+12.209`) |
| Fuller Measurement-Error-Corrected Ecologic Slope | `1.248` (`1.065`, `1.430`), reliability `0.982` | `1.236` (`1.104`, `1.367`), reliability `0.977` |

## Key Findings
1. **Higher Earnings Dispersion Among Disabled Workers:** In both MI and OH, earnings inequality among positive earners with a disability is significantly higher than among non-disabled earners (`+0.0533` Gini points in MI, `+0.0421` in OH).
2. **Severe Ecologic Fallacy at the PUMA Level:** The between-PUMA logit association between area disability prevalence and area poverty (`11.83` MI, `12.56` OH) is roughly **10× larger** than the individual-level within-PUMA log-odds ratio (`1.18` MI, `1.26` OH), confirming strong geographic sorting/contextual confounding that replicates tightly across both states.

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** Restricted to positive earners (`PERNP > 0`) for inequality indices; Theil $T$ is reported strictly as exploratory per engine validation rules.

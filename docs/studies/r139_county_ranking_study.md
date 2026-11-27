# Round 139 Study Report: County Poverty Ranking (KWW Individual & Joint Intervals) and Holm State-Reference Comparisons (2020–2024)

**Pre-registration Protocol SHA-256:** `61ce674ea164609bdeca767bf36a0534e9bba6fe1d429731d138ee2787806254`  
**Script:** [r139_county_ranking_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r139_county_ranking_study.py)  
**Data:** ACS 5-Year 2020–2024 county VRE table `B17001` (`B17001_002 / B17001_001`) across 300 counties in Michigan (`26`), New York (`36`), Ohio (`39`), and Pennsylvania (`42`), with 80 successive-difference replicate SEs at the 90% confidence level.

## Empirical Results

| State | Counties | Population-Weighted State Poverty (%) | Median Individual Rank-Interval Width | Median Joint (KWW) Rank-Interval Width | Surely Top-Decile Counties (`rank_upper <= ceil(0.10*N)`) | Counties Differing from State Mean (Holm, $\alpha = 0.10$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Michigan (`26`) | 83 | 13.21 | 55.0 | 64.0 | 0 | 33 |
| New York (`36`) | 62 | 14.01 | 39.0 | 45.0 | 1 | 27 |
| Ohio (`39`) | 88 | 13.29 | 53.5 | 63.5 | 0 | 43 |
| Pennsylvania (`42`) | 67 | 11.71 | 44.0 | 52.0 | 1 | 26 |

## Key Findings
1. **Substantial Rank Uncertainty:** Even at the 90% level with 5-year ACS precision, individual rank intervals span roughly 60–66% of each state's county count (median widths 39–55 ranks), and simultaneous Klein–Wright–Wieczorek (KWW) joint rank intervals widen further to 45–64 ranks.
2. **Almost No Counties Are Certifiably Top-Decile:** Across all 300 counties in 4 states, only 2 counties (1 in NY, 1 in PA; 0 in MI and OH) have an upper 90% rank bound strictly inside the top decile. Naive league-table rankings of county poverty rates are therefore highly unstable.
3. **State-Reference Comparisons Are Much Better Powered:** Using Holm-adjusted comparisons to each state's population-weighted mean (`census.ranking.compare_to_reference`), 129 of 300 counties (43.0%) differ significantly from their state reference rate (`33/83` MI, `27/62` NY, `43/88` OH, `26/67` PA).

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** Reference comparisons use independent county SEs combined with population-weighted reference covariance (`reference_covariance`), and do not model cross-county spatial correlation.

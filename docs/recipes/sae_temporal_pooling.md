# Recipe: Multi-Release County Small-Area Estimation (Arcsine & Rao–Yu Temporal Fay–Herriot)

Use this workflow when county ACS 5-year estimates have high sampling variance and you have 3+ non-overlapping or panel releases available for temporal borrowing of strength.

## Steps

1. **Assemble a balanced county-by-year panel with VRE replicate SEs:**
   - Extract county rates and 80-replicate SEs for each release (e.g., 2019, 2022, 2024 `B17001` poverty + `B15002` BA+ covariate).
2. **Compare cross-sectional arcsine Fay–Herriot vs. temporal Rao–Yu Fay–Herriot:**
   - Cross-sectional bounded proportion SAE: `census.sae_extensions.arcsine_small_area(...)` (guaranteed inside `[0, 1]`).
   - Temporal panel SAE: `census.sae_extensions.temporal_small_area(...)` (borrows strength across years via AR(1) random effects).
3. **Verify variance reduction and replicate across regions:**
   - Compare median direct variance (`se**2`) against median SAE `mse` for both cross-sectional and temporal models.
   - Replicate the full specification in a second independent multi-state region (e.g., MI/NY primary, OH/PA replication).

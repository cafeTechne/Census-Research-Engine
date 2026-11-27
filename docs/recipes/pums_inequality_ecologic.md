# Recipe: PUMS Earnings Inequality & PUMA Ecologic Fallacy Decomposition

Use this workflow when analyzing individual-level ACS PUMS earnings dispersion alongside area-level (PUMA) vs. individual-level associations to diagnose ecologic fallacy.

## Steps

1. **Fetch person PUMS with 80 successive-difference replicate weights (`PWGTP1..80`):**
   - `df = fetch_pums(state_fips, 2023, product="5-year", record="person", columns=["AGEP", "DIS", "PERNP", "POVPIP", "PUMA"], replicates=True)`
   - Filter to working-age adults (`AGEP` 25–64) and coerce numeric columns (`pd.to_numeric`).
2. **Compute validated earnings inequality (`PERNP > 0`):**
   - Overall: `pums_inequality(earn, "PERNP", weight="person")` (Gini, Atkinson $\epsilon=0.5, 1.0$, $\log(P_{90}/P_{10})$, $\log(P_{80}/P_{20})$, top-10% share are validated; Theil $T$ is exploratory only).
   - Subgroup Gini difference: `pums_inequality(earn, "PERNP", weight="person", by="DIS == 1")` (`gini_difference["validated"] == True`).
3. **Run PUMA within / between / contextual ecologic decomposition:**
   - Stack weights `W = df[["PWGTP"] + [f"PWGTP{i}" for i in range(1, 81)]].to_numpy(float)`.
   - Call `ecologic_check(y, x, area, W, binary=True, level=0.90)`.
   - Compare `logit["within"]` (individual association within PUMAs) against `logit["between"]` (aggregate PUMA association) and report `logit["contextual"]` plus the measurement-error-corrected `ecologic_fuller` slope and reliability.

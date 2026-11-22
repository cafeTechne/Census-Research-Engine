# Dollars: inflation and place price levels

Goal: compare dollar estimates (income, rent, home value) across years or across places fairly.

1. **Across years:** `adjust_inflation(value, from_year, to_year)`.
   - It uses R-CPI-U-RS, the Census standard for ACS dollars.
   - A five-year release's dollars are in its end year.
   - A provisional year, one with fewer than 12 published months, needs `allow_provisional=True` and carries an
     advisory.
2. **Across places:** BEA Regional Price Parities express dollars in national-average purchasing power. They are
   never applied automatically.
   - For one value: `adjust_for_place(value, geography, year)`, where `geography` is a state FIPS, a CBSA code or
     "US". Add `base_year` to also convert years.
   - For a whole analysis frame: `place_adjust_frame(input_path, variables=[...], year, areas="county_metro")`.
     It uses the metro RPP for counties in a metro CBSA, else the state's nonmetro RPP. SEs and replicates scale by
     the same factor.
3. **In pre-registered manifests:** use an `"adjustments": [{"type": "rpp", ...}]` block (recipe `preregistered`).
4. Report which index and which RPP year were used. RPPs carry their own estimation error, which is not in ACS
   MOEs, so say so.

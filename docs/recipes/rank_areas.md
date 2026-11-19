# Rank areas, and compare each area with the state

1. Build an analysis frame with the estimate and its replicates (preferred) or its MOE.
2. Ranks: `rank_areas(input_path, variable, replicates_path=...)` returns, for each area, its
   point rank and a **rank interval** (Klein, Wright and Wieczorek 2020; rank 1 = highest).
   `joint=True` makes the intervals hold for all areas at once (use it for league tables).
3. Report the interval, never the point rank alone: two areas whose intervals overlap cannot be
   ordered. The summary says how many areas are surely in the top 10%.
4. Versus the state: `rank_areas(..., kind="versus_reference", weights="population")` compares each
   area with the population-weighted mean of the areas. The state value contains each area's own
   error; with replicates the engine uses their joint covariance. Give `reference=<number>` for a
   fixed benchmark instead. `method="holm"` (default) or `"simultaneous"` (also gives
   simultaneous intervals).
5. Both are validated (Round 34, `docs/audits/ranking_validation.md`) and conservative. Bootstrap
   percentile ranks, common in county rankings, under-covered badly and are not offered.
6. Suppressed or missing values (e.g. WONDER counts of 1-9) are excluded and listed, never ranked.

# Composite (deprivation) index from ACS estimates

1. Choose three or more indicators that measure one concept (e.g. poverty, no vehicle, housing
   cost burden, no bachelor's degree). List in `reverse` any where higher means less deprived.
2. Never include the outcome you will relate the index to (circularity; `outcome=` enforces it).
3. `build_index(input_path, indicators, replicates_path=...)`: first-principal-component weights
   (`method="pca"`) or equal weights. Standardisation and weights come from the full sample and stay
   fixed in every replicate, so each area's score has a replicate SE and a 90% interval (validated).
4. Report scores with intervals and `quintile_stability` (the share of replicates keeping the area in
   its quintile): low stability means the quintile label is fragile.
5. Cronbach's alpha (Feldt interval) describes internal consistency; its interval is validated for
   independent areas and too narrow when areas are spatially correlated.
6. `typology_k` adds k-means groups with their median replicate adjusted Rand index (descriptive).
7. Validation: `docs/audits/index_validation.md` (Round 36).
8. Before using an index, read the loadings and alpha. In MI/NY counties (Round 36 example) "no
   vehicle" and housing cost burden made New York City's boroughs the most "deprived" (alpha 0.40):
   they measure urban form there, not hardship. Sampling-error intervals cannot fix construct validity.

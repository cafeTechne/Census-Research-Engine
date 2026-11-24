# Release Summary — Rounds 103–118 (`v0.99.0` → `v0.114.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted, ready for owner review and commit)

## Highlights
1. **Agent Access & Routing Parity (Rounds 103, 107, 110, 116):**
   - Added full-profile MCP/CLI umbrella tool `demography_analysis` (**81 MCP tools** total; `core` unchanged at 16).
   - Extended `disparity_measures` (`double_disaggregation`, `priority_quadrants`), `spatial_model` (`diversity`, `disease_map` `method="B3"`), and `difference_in_differences(design="msm", method="gformula")`.
   - Expanded `docs/agent_routing.md` and `tests/test_agent_routing.py` from 15 to **40 offline-tested rows (`R1–R40`)**.
   - Refreshed `README.md`, `docs/agent_protocol.md` (synced to `mcp_server.py`), and `docs/recipes/`.
2. **22 Validated Exploratory-Measure Repairs & Extensions (Rounds 104–110, 112–113):**
   - Meta-analysis (`k ≥ 10`): Nagashima–Noma–Furukawa prediction interval (`P2`), truncated Knapp–Hartung meta-regression (`R2`), Thompson–Sharp RE Egger (`E2`).
   - Causal & policy: nearest-neighbour matching ATT (`M1b-ATT`), continuous RDD with CCT CER bandwidth (`R1b`), RDD manipulation/density test (`R2_dens`, `n ≥ 1,000`), and single- & multi-confounder parametric g-formula MSM (`M5`, `M5b`, `p ≥ 1`).
   - Spatial & epidemiology: BYM2 PC-prior disease mapping (`B3`, `median E ≥ 30`), probabilistic misclassification (`M1b`), observed Lin's CCC (`C2`), designation PPV intervals (`prob80`, `point`, `lower`), PUMS Hotelling `F` homogeneity (`H2d`, `min_n ≥ 500`), SDR bias-corrected Shannon entropy (`S2b`, `n ≥ 150`), Fuller $\alpha=4$ ecologic slope (`E3d`, `areas ≥ 50, median_n ≥ 80`), Joinpoint AAPC bootstrap-$t$ (`J3c`), and count-scale disparity indices (`idisp`, `bgv`, `theil`, `mld`, `min_events ≥ 100`).
   - Failed candidates (`M3`/`M4` IPW MSM, `MD2`/`W2` WHO `mdm`/`mdb`, `S3` synthetic-control conformal, `M3b`/`M3c` 3-level variance shares, `Q2e-prob50`, `W3_rr` Woolf RR homogeneity) stayed strictly exploratory with published audits.
3. **Confirmed-Method Correctness, Stress Audit & Reference Benchmarks (Rounds 111, 115):**
   - Fixed 2 edge-case bugs (constant-`x` `ZeroDivisionError` in Fuller ecologic slope; identical-series crash in `agreement.py`).
   - **10/10 out-of-DGP adversarial stress tests held** (`docs/audits/confirmed_stress_audit.md`).
   - Added 8 published textbook & closed-form reference benchmarks (`tests/test_reference_benchmarks.py`).
4. **100% Pre-Registered Manifest Coverage (Rounds 104, 108–110, 114):**
   - Expanded `census/manifest/methods.py` from 15 to **28 manifest methods** (+13: `estimate_effect`, `spatial_scan`, `stratified`, `designation`, `agreement`, `rdd`, `disease_map`, `joinpoint`, `demography`, `difference_in_differences`, `interrupted_series`, `combine_estimates`, `bias_analysis`), plus opt-in `fit_replicate` `args.marginal`/`args.impute` and `disparity` `args.who_measures`/`args.compare_years`.
5. **Release & Data-Refresh Tooling (Rounds 117–118):**
   - Added offline N39 ACS 2021–2025 preflight script (`scripts/acs_release_preflight.py`) and pre-commit release-hygiene verifier (`scripts/release_hygiene_check.py`).
   - Manifest execution golden (`scripts/run_golden.py`) remains **byte-identical** to pre-Round-103 baseline.

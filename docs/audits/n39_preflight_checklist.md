# Backlog N39 Runbook — ACS 2021–2025 Release Refresh Preflight (Round 117)

When the Census Bureau publishes the ACS 2021–2025 5-year release (~December 2026) and BLS finalizes the 2025 annual average price index, execute this sequence:

1. **Run offline preflight:**
   ```bash
   python scripts/acs_release_preflight.py --target-year 2025
   ```
   Confirms current metadata vintages, bundled CSV SHA-256 integrity, and crosswalk health, and prints exact missing items.
2. **Fetch 2025 variable metadata archive:**
   ```bash
   python scripts/fetch_metadata_archive.py --years 2025
   ```
3. **Refresh price indexes & BEA RPPs (once final 2025 averages publish):**
   ```bash
   python scripts/update_price_indexes.py
   python scripts/update_price_parities.py
   ```
4. **Run concordance audit & validation suite:**
   ```bash
   python scripts/validate_against_census.py
   python scripts/acs_release_preflight.py --target-year 2025
   OPENBLAS_NUM_THREADS=1 pytest -q
   ```
   Confirm `ready: true`, `crosswalk_error_count: 0`, and zero test failures before closing N39.

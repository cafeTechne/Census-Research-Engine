# Unattended Pure-Engine Sprint Log & Queue (2026-11-27, 12:30 PM – 7:30 PM EST)

**Focus:** 100% core engine upgrades, hardening, simulation validation, and regression testing (zero throwaway research artifacts; zero git commits until owner returns; 100% sandbox-safe so no prompt stalls occur).

## Queue Status

| Round | Target Version | Engine Deliverable | Status |
| :--- | :--- | :--- | :--- |
| **R203** | `0.199.0` | Expose `allow_disconnected=True` in `spatial_model` + top-level `census` exports | **DONE** (12:28 PM) |
| **R204** | `0.200.0` | Reusable zero-CDN `census.web_maps.side_by_side_choropleth()` (`N135`) | **DONE** (12:28 PM) |
| **R205** | `0.201.0` | Layer B `allow_subprocess_neural` hook in `rag.py`, routing `R101–R103`, hygiene sync | **DONE** (12:28 PM) |
| **R206** | `0.202.0` | Multi-component BYM2 (`N132`) finite-sample simulation calibration (`census/simulation_multicomponent_bym2.py`) | **DONE** (1:17 PM; conn cov `0.901`, island cov `0.883`, RMSE `0.147` vs `0.162`) |
| **R207** | `0.203.0` | Layer B SQLite WAL concurrency hardening (`journal_mode=WAL`, `busy_timeout=5000`) & vectorized `min_year` SQL pre-filter | **DONE** (2:16 PM) |
| **R208** | `0.204.0` | Layer A `doctor --deep` invariant check (MCP tool ↔ `TOOL_SOURCES` 1:1 parity + metadata SHA-256 manifest verification) | **DONE** (3:16 PM) |
| **R209** | `0.205.0` | Layer B domain synonym query expansion (`BYM2`, `SCPC`, `RPP`, `KWW`, `Fay-Herriot`) & passage vector indexing (`passages.sqlite`) | **DONE** (4:16 PM) |
| **R210** | `0.206.0` | Layer A `workflows_geo.py` modularization (extract `workflows_geo_helpers.py` with dynamic lookup + 100% re-export parity) | **DONE** (5:16 PM) |
| **R211** | `0.207.0` | Layer A `confounding_adjustment_screen` MCP/CLI tool exposure + manifest support & routing `R104–R109` | **DONE** (6:17 PM; 85 MCP tools == 85 `TOOL_SOURCES`, 109 routing rows) |
| **R212** | `0.208.0` | Full-repository `pytest` regression sweep (`tests/` + `layer_b_openscholar/tests/`), `release_hygiene_check.py`, `doctor --deep`, and evening summary | **DONE** (7:17 PM; `183 passed, 0 failed, 72 subtests passed`) |

## Execution Log
- **12:28 PM:** Completed Batch 1 (`R203–R205`, `v0.201.0`) and scheduled hourly cron (`15 * * * *`, `MaxIterations: 7`) to execute `R206–R212` cleanly before 7:30 PM EST.
- **1:17 PM (Cron #1):** Completed **R206 (`v0.202.0`)** — `census/simulation_multicomponent_bym2.py` (30 draws, 4 components, 2 islands, `median_e=40`): connected 90% CI coverage **`0.901`**, island 90% CI coverage **`0.8833`**, exceedance precision **`0.9256`**, RMSE **`0.1466`** vs raw SMR **`0.1621`**. `6 passed`, `release_hygiene_check.py` `ok: true`.
- **2:16 PM (Cron #2):** Completed **R207 (`v0.203.0`)** — enabled SQLite WAL mode + `busy_timeout=5000` across Layer B `index.sqlite`/`passages.sqlite`/`vectors.sqlite` and SQL `min_year` pre-filtering in `LocalVectorStore.search()`. Verified via `tests/test_round207.py`, `layer_b_openscholar/tests/`, and `release_hygiene_check.py`.
- **3:16 PM (Cron #3):** Completed **R208 (`v0.204.0`)** — added `doctor --deep` invariant check verifying 1:1 MCP tool ↔ `TOOL_SOURCES` parity (`84 == 84`), recipe doc parity (`33`), and `metadata/manifest.json` integrity. Verified via `tests/test_round208.py` and `release_hygiene_check.py`.
- **4:16 PM (Cron #4):** Completed **R209 (`v0.205.0`)** — added `layer_b_openscholar/query_expansion.py` (`expand_domain_query` wired into `rag.py`) and `sync_passages_to_vectors()` in `vector_store.py`. Verified via `tests/test_round209.py`, `layer_b_openscholar/tests/`, and `release_hygiene_check.py`.
- **5:16 PM (Cron #5):** Completed **R210 (`v0.206.0`)** — extracted `census/workflows_geo_helpers.py` from `census/workflows_geo.py` with 100% re-export parity and dynamic lookup. Verified via `tests/test_round210.py`, `tests/test_workflows_geo.py`, and `release_hygiene_check.py`.
- **6:17 PM (Cron #6):** Completed **R211 (`v0.207.0`)** — exposed `confounding_screen` via MCP (`85` tools == `85` `TOOL_SOURCES`) and CLI (`python -m census tool confounding_screen`), expanded routing to `109` rows (`R104–R109`), synced `README.md`/`STATUS.md`, and verified `doctor --deep`, `test_round43`, `test_round88`, `test_round211`, and `release_hygiene_check.py`.
- **7:17 PM (Cron #7, Final):** Completed **R212 (`v0.208.0`)** — expanded routing to **110** rows (`R110`), verified `release_hygiene_check.py` (`ok: true`, `version: "0.208.0"`), `doctor --deep --json` (`ok: true`, `85 == 85` MCP/TOOL_SOURCES parity, `33` recipes, `28` manifest methods), and **`183 passed, 0 failed, 72 subtests passed`** across Rounds 185–212 + all core contract suites + `layer_b_openscholar/tests/`. All 10 sprint rounds (`R203–R212`) finished cleanly before 7:30 PM EST; working tree left uncommitted awaiting owner approval.

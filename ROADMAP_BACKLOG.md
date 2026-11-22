# Backlog roadmap (open items only)

**Status: rewritten 2026-11-21, after v0.65.0 (DOI 10.5281/zenodo.24411452).** Finished work (Rounds 43–69,
issues N1–N46, the replication shortlist) was removed from this file. It stays in git at tag `backlog-r43-69`,
in `CHANGELOG.md` and in the plan tags `plan-r<n>`. This file is the owner's backlog, from which
`PLAN_ROUND_<n>.md` files are drafted; it is not itself a plan. **Implementing agents: do not read this file
unless the owner asks; implement only the lowest-numbered `PLAN_ROUND_<n>.md`.**

**Ground rules (unchanged):**
- Validation first: the criterion is committed before the full run, and failed methods stay exploratory.
- MI/NY are the test states and OH/PA the replication states; later geometries are added where a round needs
  them.
- Goldens stay byte-identical unless a round says otherwise.
- No automated WONDER access, and no sub-national counts 1–9 in any output.
- Releases need the owner's yes each time.

## 1. Open issues

| # | Issue | Found in | Kind | Round |
| :--- | :--- | :--- | :--- | :--- |
| N39 | The ACS 2021–2025 five-year release (due about December 2026) needs its metadata archive, a concordance audit and a price-index refresh; BLS's 2025 annual average is still provisional | owner, 2026-11-20 | data refresh | about 2026-12-20 |
| N47 | `load_dotenv()` searches from the engine's own file location, not the working directory. Installed from a wheel, the engine misses the user's project `.env` (Census API key). Seen in every worktree run of Rounds 66–69 | R66–R69 | bug | 70 |
| N48 | Long workflows give no progress and save results only at the end; a killed run loses everything (Round 69's first run) | R69 | usability | 70 |
| N49 | No tract-level spatial interval is validated: on NC tracts SCPC under-covers at 100 km (.75/.81) and HC3 covers .12–.26. Fits give no warning when residuals are clearly spatially dependent | R67 | validation gap | 71 |
| N50 | Data sources the replications needed are not in the engine: County Business Patterns, ERS county typology and rural–urban codes, CHR additional measures. All-state tract pulls need a hand loop (no one-request-per-state path) | R66, R69 | missing capability | 72 |
| N51 | Methods the replications needed are missing: three-level multilevel models (was N46), indices from published loadings, indirect standardization for a county frame from a national age × sex file | R68, R69 | missing method | 73 |
| N52 | The replications are one-off scripts: an agent cannot rerun them through MCP or manifests, and nothing checks that the engine still reproduces them | R66–R69 | reproducibility | 74 |

## 2. Recorded limits (not scheduled; reopen only with a new idea)

- Interrupted series below 17 annual points (every method failed at 15).
- G2 with eight error-prone covariates (.856); spatial EIV beyond the gated caps (G1 8, G2 7).
- Theil T from PUMS (fails up to 8,000 households).
- Bias-corrected segregation D above noise .75 (failed on Texas), and any index at infinite noise.
- Clipped six-group segregation only as validated in Round 62; naive isolation and H are exploratory.
- IM-8 correlation and α intervals; CCC intervals; PUMS GEE (deferred: SDR replicates carry the design).
- Round 27 splines and joint tests (exploratory until a pre-specified finite-sample validation).
- WONDER causes with suppressed national child-age reference cells need a pre-registered rule before analysis.

## 3. Rounds

| Round | Theme | Covers | Status |
| :--- | :--- | :--- | :--- |
| 70 | Housekeeping: `.env` discovery and long-job progress/checkpoints (no new statistics) | N47, N48 | merged (v0.66.0) |
| 71 | Tract-level spatial inference: validation, plus a residual-dependence warning | N49 | merged (v0.68.0; SCPC .20/.30 pass for tract OLS; SEM fails) |
| 72 | Data sources: CBP, ERS typology and rural–urban codes, CHR additional measures, state-wide tract pulls | N50 | merged (v0.67.0; state-wide tract pulls already existed) |
| 73 | Methods: three-level multilevel models, loading-weighted indices, indirect standardization helper | N51 | merged (v0.69.0; three-level fixed effects and loadings indices validated; share intervals exploratory) |
| 74 | Replication suite: the five replications as registered manifests and engine regression checks | N52 | planned |
| — | ACS 2021–2025 refresh | N39 | about 2026-12-20 |

Order rationale:
- **Round 70** fixes a user-facing bug first.
- **Round 71** closes the largest validation gap; tract studies are common in public health.
- **Rounds 72–73** turn the replications' hand-built steps into engine features.
- **Round 74** depends on 72–73, so that the replications can run through manifests.

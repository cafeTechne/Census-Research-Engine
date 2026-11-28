# Plan — Round 199 (N134): Reproducible Container (`Dockerfile`), External Reviewer Checklist, Routing `R95–R97` & `v0.195.0` Sync

## 1. Strategic Objective
Prepare the repository for independent external replication and JOSS / epidemiology journal review by shipping a clean, minimal `Dockerfile`, a structured `docs/external_review_checklist.md`, expanding `docs/agent_routing.md` (`R95–R97`, **97** rows), extending `scripts/release_hygiene_check.py` through Round 199, and syncing version `0.195.0`.

## 2. Exact File Contracts
1. `Dockerfile`: Pinned `python:3.12-slim` image installing `requirements.txt` and editable package, running `python -m census doctor --verbose --json` as smoke check (zero secrets baked in).
2. `docs/external_review_checklist.md`: Step-by-step independent reviewer verification protocol covering installation, `doctor --verbose`, offline test suite, `verify_bundle`, `lint-latex`, and Layer B isolation.
3. `docs/agent_routing.md`: Append `R95–R97` (97 rows total).
4. `scripts/release_hygiene_check.py`: Extend audit check through Round 199 (`range(126, 200)`).
5. Version sync `0.195.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`, `ROADMAP_BACKLOG.md` (close `N128`, `N130`, `N133`, `N134`).
6. `tests/test_round199.py` & `docs/audits/round199_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted from roadmap item `N134`.
- *2026-11-27:* Added `Dockerfile`, `docs/external_review_checklist.md`, routing `R95–R97` (97 rows), closed `N128`/`N130`/`N133`/`N134`, and synced version `0.195.0`. Verified via `tests/test_round199.py` and `release_hygiene_check.py`.

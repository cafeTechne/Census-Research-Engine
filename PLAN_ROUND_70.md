# Round 70 plan: `.env` discovery and long-job progress (no new statistics)

**Goal.** Backlog N47 and N48. Version 0.66.0. Branch `phase70/env-progress`. Goldens byte-identical; registered
manifests unchanged.

## 1. `.env` discovery (N47)

**Problem.** `census/api.py` and `mcp_server.py` call `load_dotenv()` with no path. python-dotenv then searches
upward from the *calling file's* directory, not the working directory. Installed from a wheel, the engine never
sees the user's project `.env`, so it runs without a Census API key: rate-limited, or "Invalid Key" pages. Every
worktree run in Rounds 66–69 hit this.

**Fix.** New `census/env.py` with `load_environment()`, called once by `census/api.py` and `mcp_server.py`:
1. If `CENSUS_DOTENV` names a file, load it.
2. Otherwise load `.env` found upward from the **current working directory**
   (`find_dotenv(usecwd=True)`).
3. Otherwise load `.env` found upward from the package location (today's behaviour, so editable clones still
   work).
4. Existing environment variables are never overridden (`override=False`), and nothing is printed.
5. `load_environment()` returns which source was used (path or `None`) for diagnostics. It never returns values.

**Docs.** The README configuration table gains `CENSUS_DOTENV` and one sentence on the search order.
`docs/claude_setup.md` gets the same sentence.

**Tests** (`tests/test_round70.py`), using subprocesses with a temporary directory and a dummy key:
- a `.env` in the working directory is found when the package lives elsewhere;
- `CENSUS_DOTENV` wins over both other locations;
- an existing environment variable is not overridden;
- the dummy key never appears in stdout or stderr;
- the repository `.env` is not read when a working-directory `.env` exists.

## 2. Long-job progress and checkpoints (N48)

**Problem.** `run_manifest` and other long workflows report nothing until they finish and save nothing on
failure. A killed run loses all of its work.

**Fix (opt-in; defaults unchanged, so goldens stay identical):**
- `run_manifest(..., checkpoint=True)`:
  - writes each completed analysis's result to `<output_dir>/.checkpoint/<analysis_id>.json`, together with the
    manifest hash and the input-data hash it used;
  - on a rerun with the same manifest and inputs, skips analyses whose checkpoint matches and reports which were
    reused;
  - deletes `.checkpoint/` after a successful bundle is written;
  - a checkpoint from a different manifest hash or input hash is ignored with a note, never reused.
- **Progress lines** go to stderr (never stdout, which stays clean JSON for the CLI and MCP):
  - `run_manifest`: one line per analysis;
  - `batch_download`: one line per 25 requests (its existing `progress` callback);
  - replicate refits in `fit_model(method="replicate")` and `regression_calibration`: one line per 20 refits.
  - Silence them with `CENSUS_PROGRESS=0`.
- **MCP:** where the client supports it, `run_manifest` and `batch_download` send progress notifications through
  the MCP context. Clients without progress support see no change.
- **CLI:** `python -m census tool run_manifest --arg checkpoint=true` passes through; the README notes it.

**Tests:**
- a manifest whose second analysis raises leaves the first analysis's checkpoint;
- a rerun reuses it and finishes;
- a changed manifest hash ignores the stale checkpoint;
- stdout stays valid JSON with progress on;
- `CENSUS_PROGRESS=0` silences stderr.

## 3. Docs and acceptance

- STATUS round entry; CHANGELOG 0.66.0; version; compatibility audit; rule text (`agent_protocol.md`, generated
  into `mcp_server.py`): long registered runs should use `checkpoint=True`.
- Goldens byte-identical; full suite; no example (no new statistics).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| `.env` discovery | | |
| Checkpoints | | |
| Progress lines / MCP notifications | | |
| Goldens, final suite | | |
| Exceptions | | |

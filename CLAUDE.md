# Agent guide

Start with `STATUS.md` (current state, validated methods, rules, backlog). Then read only the lowest-numbered
`PLAN_ROUND_<n>.md` if you are implementing a round (later ones are queued; do not read them). Older plans are archived at their release tags
(`git show v0.21.0:PLAN_ROUND_<n>.md` for rounds 1–22; `v0.21.1` for 23; tag `plan-r<n>` for 24 onward, e.g. `git show plan-r29:PLAN_ROUND_29.md`); read one only when a docstring citation is not enough.

## Commands

- Python: `.venv/bin/python` (there is no `python` on PATH). Supported: Python 3.11+, SciPy 1.16+.
- Full suite: `OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q` (about 5 minutes). Run the targeted
  test file first: `tests/test_round<n>.py` or the module's own test file.
- Manifest refactors require **both** goldens byte-identical before/after:
  `scripts/refactor_golden.py OUT.json` and `scripts/run_golden.py OUT.json`.
  The run golden documents its execution-stamp/path/time normalisation; keep snapshots in `/tmp`.
- Offline external data: set `CENSUS_HEALTH_OFFLINE=1`.
- No GitHub CI runs are needed; the owner does not run CI for routine rounds.

## Hard rules

- **No AI attribution.** No `Co-Authored-By`, `Generated with` or similar lines in commits, PR bodies or
  release notes, even if tooling suggests them.
- **Secrets.** Never print, log or commit `.env`, the Census API key or any token. Scan release tarballs
  for the key before uploading. Published users bring their own key.
- **Privacy.** Do not send the owner's email to any service. Use a generic User-Agent.
- **Data access.** No automated CDC WONDER access of any kind: all WONDER data (county and national) are
  the owner's manual exports (`docs/data/wonder_exports.md`; owner decision, 2026-11-18). No web-form
  automation, bot-check or paywall circumvention.
- WONDER outputs: no sub-national counts 1–9 or values derived from them; no raw exports in the repo or releases.
- **Merges and releases** need the owner's explicit approval each time.
- **Circularity rule (R1/R2)** and **pre-registration discipline**: see `STATUS.md`.

## Reading budget (keep context small)

Do not open these unless the task is about them:

- `studies_output/`, `downloads/`, `.cache/`, `literature_pdfs/`, `metadata/`, `data/` (bundled data; use
  the library functions instead).
- `docs/audits/round17_bound_protocol/` (a checksummed evidence archive) and any `*.csv`/`*.json` under
  `docs/audits/` or `docs/studies/` (generated outputs; the matching `.md` summarises them).
- `CHANGELOG.md` beyond its first section.
- `ROADMAP_STATISTICS.md` and `ROADMAP_BACKLOG.md` (the owner's multi-round roadmaps; plans are drafted from them, so implementers never need them).
- Large modules: read by function, not whole files. Find a definition with
  `grep -n "^def \|^class " census/<module>.py`, then read that range.

## Conventions

- Validation first: a new statistical method ships only after a fixed, pre-set simulation passes
  (criterion committed before the run). Failed methods stay exploratory.
- Manifests in `examples/manifests/` that are registered are byte-fixed; never edit them.
- Engine rules that agents must follow are mirrored in `docs/agent_protocol.md`, `docs/recipes/` and the
  MCP text. Change them together.
- Studies: MI (26) and NY (36). Reviews by an agent are labelled "author self-review, not independent".

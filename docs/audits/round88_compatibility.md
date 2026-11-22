# Round 88 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round88`, branch `phase88/attribution`. Version 0.84.0.
No statistics changed and no validation run (the plan has no simulation criterion).

## Behaviour changes

- **MCP and CLI `tool` results.** Successful results of the 49 method tools gain `method_sources`. Failures, the 29
  discovery and extraction tools, and module-level Python calls are unchanged. The result is a shallow copy, so cached
  dicts are never mutated.
- **`make_results_bundle`.**
  - `methods.md` ends with a **Sources** section.
  - Two new files, `references.md` and `references.bib`, appear in `files` in `bundle.json`.
  - `results_bundle(references=...)` accepts only those two names. Without the argument nothing changes, so manifest
    bundles and goldens are byte-identical.
- **New CLI command** `cite`. Still 78 MCP tools; the `get_recipe` budget is unchanged.
- **Protocol rule** (mirrored into `mcp_server.py` by `scripts/sync_rule_text.py`).

## Exceptions

1. **Manifest bundles do not get `references.bib`.** The plan allowed this only if goldens stayed unchanged. Manifest
   methods text already lists references, so this is left for a documented later change.
2. **Discovery and extraction tools carry no `method_sources`.** Their only sources are data products, already cited
   in provenance. Omitting them keeps frequent results small for local models (sources add 0.3–2.4 KB per result).
3. **One entry is unverified:** Hadam, Würz and Kreutzmann 2020, which Round 80 cites by author and year only. Its
   title and outlet were recorded from memory, so it is marked "[details to verify]". A Casas-Cordero et al. entry
   was dropped because the engine does not rely on it.
4. **Validation audits are cited by path.** They are evidence about the engine, not publications.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 87.
- Full suite: 2291 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.

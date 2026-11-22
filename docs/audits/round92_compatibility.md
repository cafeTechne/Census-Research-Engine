# Round 92 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round92`, branch `phase92/sources`. Version 0.88.0. No
statistics changed and no simulation was run.

## Behaviour changes

- **New module** `census/demographic_sources.py`.
- **Three new `context` sources** (`pep`, `lodes`, `acs_flows`). They are validated in manifests and frames;
  existing context entries are unchanged.
- **Downloads** are cached under the context cache with SHA-256 sidecars and use a generic User-Agent. Flows use the
  user's API key through the engine's client.
- **No new MCP tool.** Registered manifests have no new sources, so goldens are expected byte-identical.

## Exceptions

1. **PEP comes from the published dataset files, not the Census API.** The API's PEP endpoints stop at vintage 2019
   for characteristics; the files cover both vintages with one format.
2. **Flows after the 2016–2020 release are refused for county-to-county use.** Those releases publish state-level
   partners only (checked against the live API).
3. **Population pyramids** (Walker chapter 4) are left to `pep_age_sex` plus the existing figure tools; no new
   figure type was added.

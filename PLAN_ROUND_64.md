# Round 64 plan: agent access (no new statistics)

**Goal.** Backlog issues N40–N43 (`ROADMAP_BACKLOG.md` section 8). Agents are the engine's primary operators, but
some validated methods are out of their reach and the text that guides them has drifted. Version 0.61.0. Baseline:
the v0.60.0 suite (2137 passed, 37 skipped). Branch `phase64/agent-access`. No simulation: no statistical result
changes, and both goldens must stay byte-identical.

## 1. CLI allowlist (N40)

Add the nine shared workflows the CLI `tool` command cannot run: `compare_groups`, `test_association`,
`estimate_effect`, `check_agreement`, `combine_estimates`, `rank_areas`, `build_index`, `list_health_sources`,
`run_variant`. The remaining MCP-only tools have dedicated CLI subcommands or are server-local (listing, metadata,
review); a test records that split so a new workflow cannot be left out silently.

## 2. MCP routes for Python-only methods (N41)

- **New tool `interrupted_series`** (full profile; tool count 70 → 71): an annual series as `values` (or
  `input_path` + `column`, sorted by a `year` column), `interruption_index` or `interruption_year`, `method` (default
  `"bootstrap_t_cons"`). It wraps `census.missing_censored_its.interrupted_series` and returns its validated flag,
  notes and audit. Results carry `summary` and `next_step`. ACS five-year windows are refused as annual points
  (overlapping releases), as `trend_test` already does.
- **`fit_model(model="negbin", censored="<column>")`** routes to `fit_censored_negbin` (Round 45; counts hidden as
  1–9 used as interval information, never estimated). It needs `exposure`, refuses any other model, and its output
  never contains a value for a hidden count.

## 3. One source for rule text (N42)

- `docs/agent_protocol.md` gets one marked block, the validated-method rules (`<!-- rules:start -->` …
  `<!-- rules:end -->`), holding every round passage now copied into `mcp_server.py`.
- Where the copies drifted, keep the more complete and newer statement, checked against the code and `STATUS.md`.
- `scripts/sync_rule_text.py` writes that block into `mcp_server.py` between `# BEGIN GENERATED RULES` and
  `# END GENERATED RULES`, with `INSTRUCTIONS` built from the generated text plus the hand-written parts.
- `--check` exits non-zero when the two differ, and a test runs it.
- Existing rule-text tests keep passing (they check both files).
- `CORE_INSTRUCTIONS` and the recipes stay hand-written summaries; they are not copies.

## 4. Core-profile text names only reachable tools (N43, part 1)

`CORE_INSTRUCTIONS` and the core descriptions may mention a tool outside the profile only with the words "full
profile" in the same item. A test parses tool names in that text against `PROFILES["core"]`. The profile itself
stays at 16 tools: small local models do better with few tools (`docs/local_models.md`).

## 5. Routing contract (N43, part 2)

- `docs/agent_routing.md` holds about 15 research questions. Each has the tool, the key arguments and the expected
  flag, using offline fixtures. Examples:
  - a binomial share with spatial dependence → `fit_model(spatial="scpc")`, validated;
  - a 15-point annual series → `interrupted_series`, not validated, the note names 17;
  - six noisy covariates at reliability .7 → EIV, not validated;
  - Theil T → not validated;
  - an overdispersed count → `negbin`;
  - WONDER-censored counts → `censored`.
- `tests/test_agent_routing.py` checks each row:
  - the tool exists in the stated profile;
  - the matching recipe or instructions name the tool;
  - the call returns the expected flag.
- The same questions become tasks in `scripts/local_model_eval.py`, verified by `--offline-check`. Live model runs
  stay paused (owner decision).

## 6. Docs and acceptance

- README: tool count, the interrupted-series row, the CLI note.
- STATUS (tool counts, round entry); CHANGELOG 0.61.0; version; compatibility audit.
- Goldens byte-identical; full suite; no example (no new statistics).

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| CLI allowlist | | |
| MCP routes | | |
| Rule-text source | | |
| Core text check | | |
| Routing contract | | |
| Goldens, final suite | | |
| Exceptions | | |

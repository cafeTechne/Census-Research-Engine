# Round 180 Compatibility Audit (`v0.175.0`)

- **Scope:** Routing expansion (`R77–R80`, 80 rows total in `docs/agent_routing.md`), `scripts/release_hygiene_check.py` extended through Round 180 (`range(126, 181)`), `tests/test_round180.py`, and version consolidation at `0.175.0`.
- **Backward Compatibility:** Additive only; all prior manifest schemas, golden outputs, MCP profiles, crosswalk/spatial APIs, and CLI interfaces remain unchanged.
- **Layer B Isolation:** Enforced automatically by `scripts/release_hygiene_check.py` (zero `census` imports across `layer_b_openscholar/`).
- **Review Note:** Author self-review, not independent.

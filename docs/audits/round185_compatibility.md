# Round 185 Compatibility Audit (`v0.180.0`)

- **Scope:** Routing expansion (`R81–R84`, 84 rows total in `docs/agent_routing.md`), `scripts/release_hygiene_check.py` extended through Round 185 (`range(126, 186)`), `tests/test_round185.py`, and version consolidation at `0.180.0`.
- **Backward Compatibility:** Additive only; all prior manifest schemas, golden outputs, MCP profiles, PUMS/health-source APIs, and CLI interfaces remain unchanged.
- **Layer B Isolation:** Enforced automatically by `scripts/release_hygiene_check.py` (zero `census` imports across `layer_b_openscholar/`).
- **Review Note:** Author self-review, not independent.

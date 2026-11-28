# External Reviewer & Independent Replication Checklist (Round 199 / N134)

This checklist lets an independent reviewer (e.g., JOSS, *Epidemiology*, *AJPH*, or an external methods auditor) verify the Census Research Engine cleanly from a fresh clone or container without needing a Census API key or live internet access.

## 1. Environment & Integrity Verification (< 1 minute)

```bash
python -m census doctor --verbose --json
python scripts/release_hygiene_check.py
```

- Confirm `"ok": true`, `"bundled_data_ok": true`, `"crosswalks_valid": true`, and `"errors": []`.
- Confirm `CENSUS_API_KEY` is never echoed in stdout/stderr even when set in the environment.

## 2. Offline Statistical & Contract Verification

```bash
pytest -q tests/test_reference_benchmarks.py \
  tests/test_track_a_manifest_parity.py \
  tests/test_track_b_bibtex_bundle.py \
  tests/test_proposition_verification.py \
  tests/test_agent_routing.py \
  tests/test_mcp_profiles.py \
  tests/test_packaging.py \
  layer_b_openscholar/tests/
```

- Confirm **0 failures** across published textbook reference benchmarks, manifest parity goldens, proposition verification contracts, 97 routing rows, MCP profiles, wheel packaging, and isolated Layer B tests.

## 3. Strict Two-Layer Isolation Audit

- Confirm `layer_b_openscholar/` contains **zero imports** from `census/` (automatically enforced by `scripts/release_hygiene_check.py`).
- Confirm `pyproject.toml` and `requirements.txt` contain zero PyTorch/Transformers bloat (Tier 2 neural embeddings run exclusively in an optional isolated `venv-neural`).

## 4. Publication Bundle & LaTeX Verification

```bash
python -m census lint-latex studies_output/r188_flagship_manuscript/manuscript.tex --json
python -m census verify-bundle studies_output/r188_flagship_manuscript/bundle
```

- Confirm `"ok": true`, `"errors": []`, and zero raw sub-national mortality counts of `1–9` in any emitted table, figure, or narrative.

## 5. Containerized Reproduction (Optional)

```bash
docker build -t census-research-engine .
docker run --rm census-research-engine
docker run --rm census-research-engine python scripts/release_hygiene_check.py
```

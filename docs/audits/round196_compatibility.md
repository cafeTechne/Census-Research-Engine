# Round 196 Compatibility Audit — Subprocess Neural Query Bridge (`N130`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Updated `ROADMAP_BACKLOG.md` closing `N127` and adding `N128–N135` based on empirical lessons from Rounds 121–195.
  - Added `SubprocessNeuralEmbedder` in `layer_b_openscholar/neural_bridge.py` enabling zero-torch callers to query neural embeddings stored in `vectors.sqlite` via the isolated SSD `venv-neural`.
- **Isolation:** Strictly zero `census` imports in `layer_b_openscholar/`.

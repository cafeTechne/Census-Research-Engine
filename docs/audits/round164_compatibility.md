# Round 164 Compatibility Audit (`v0.159.0`)

- **Scope:** Added pluggable SQLite + NumPy vector store (`layer_b_openscholar/vector_store.py`, zero-dependency `HashProjectionEmbedder` + `SentenceTransformerEmbedder` hook for N127) and `domain_hybrid_rag` recipe (`docs/recipes/domain_hybrid_rag.md`, 33 recipes total in `census/recipes.py`).
- **Layer B Isolation:** Zero `census` imports; `pyproject.toml` and `requirements.txt` untouched.
- **Review Note:** Author self-review, not independent.

# Layer B Prototype: OpenScholar Literature Discovery & Hypothesis-Seed Workspace

Standalone **upstream** literature retrieval, reranking, and hypothesis-gap handoff tool (Architecture v11, Layer B).

- **Strictly decoupled from Layer A (`census/`):** zero imports from or into `census/`; separate dependencies.
- **Mode 1 (default — no 700 GB datastore required):** Semantic Scholar Graph API (`S2_API_KEY`) + Hugging Face **`OpenScholar/OpenScholar_Reranker`** (0.6B `bge-reranker-large` fine-tune; falls back cleanly to deterministic BM25 when `torch`/`transformers` are not installed).
- **Epistemic boundary:** Outputs are explicitly tagged `exploratory_hypothesis_seed` with immutable Semantic Scholar `paperId`, DOI, and dossier SHA-256. They **never** establish confirmatory status — pre-registered empirical testing happens downstream in `Census-Research-Engine`.

## Quick start

```bash
# Optional: set your Semantic Scholar API key (higher rate limits)
export S2_API_KEY="your-key-here"

# Optional: install OpenScholar_Reranker dependencies (GPU or CPU)
pip install -r layer_b_openscholar/requirements.txt

# Search, rerank, and emit dossier.json + references.bib + hypothesis_seeds.md
.venv/bin/python -m layer_b_openscholar search \
  "county cancer mortality disparities Appalachia poverty spatial smoothing" \
  --limit 25 --top-k 10 --backend auto --out studies_output/dossier_cancer
```

## Mode 2 (future upgrade, only if Mode 1 proves need)
If Mode 1 proves valuable across several real studies and you want fully offline retrieval without hitting Semantic Scholar, index a **domain-scoped subset** (public health, epidemiology, demography, spatial econometrics — ~5–20 GB on SSD) rather than the full 700 GB multi-discipline `OpenScholar-DataStore-V3` on a spinning HDD.

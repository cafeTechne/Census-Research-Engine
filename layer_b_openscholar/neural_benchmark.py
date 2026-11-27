# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 186: Head-to-head Lexical vs. Hash vs. Neural BGE Hybrid RAG benchmark (N127).

Runs 5 domain queries against the Layer B corpus comparing:
1. Lexical ``FTS5 + BM25`` (``vector_model="none"``)
2. 3-way ``FTS5 + BM25 + HashProjection`` (``hash_projection_d256``)
3. 3-way ``FTS5 + BM25 + Neural BGE Dense`` (``BAAI/bge-small-en-v1.5``)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .local_index import LocalLiteratureIndex
from .pdf_indexer import LocalPassageIndex
from .rag import query_hybrid_rag
from .vector_store import DEFAULT_NEURAL_MODEL, HashProjectionEmbedder, LocalVectorStore, SentenceTransformerEmbedder

NEURAL_BENCHMARK_QUERIES = [
    "county mortality spatial autocorrelation small area estimation BYM2",
    "PUMA ecologic fallacy microdata aggregation bias American Community Survey",
    "regional price parity cost of living poverty measurement BEA",
    "race residential segregation dissimilarity isolation index census tract",
    "opioid overdose suicide despair mortality rural urban socioeconomic",
]


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return round(len(sa & sb) / max(len(sa | sb), 1), 4)


def run_neural_benchmark(
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    neural_model: str = DEFAULT_NEURAL_MODEL,
    top_k: int = 8,
    out_md_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Benchmark Lexical vs. Hash vs. Neural BGE RAG across 5 domain queries."""
    lit_stats = LocalLiteratureIndex(db_path).stats()
    pas_stats = LocalPassageIndex(passages_db_path).stats()
    hash_emb = HashProjectionEmbedder(dim=256)
    neural_emb: Optional[Any] = None
    neural_error: Optional[str] = None
    try:
        neural_emb = SentenceTransformerEmbedder(model_name=neural_model)
    except Exception as exc:
        neural_error = f"{type(exc).__name__}: {exc}"

    vstats = LocalVectorStore(db_path=vector_db_path, embedder=neural_emb or hash_emb).stats()

    results: List[Dict[str, Any]] = []
    for q in NEURAL_BENCHMARK_QUERIES:
        row: Dict[str, Any] = {"query": q, "modes": {}}
        mode_specs = [
            ("lexical_bm25", "none", None),
            ("hash_3way", "hash", hash_emb),
        ]
        if neural_emb is not None:
            mode_specs.append(("neural_bge_3way", neural_model, neural_emb))

        for mode_name, vmodel, emb in mode_specs:
            t0 = time.perf_counter()
            rep = query_hybrid_rag(
                q,
                db_path=db_path,
                passages_db_path=passages_db_path,
                vector_db_path=vector_db_path,
                top_k_papers=top_k,
                top_k_passages=3,
                vector_model=vmodel,
                embedder=emb,
            )
            ms = round((time.perf_counter() - t0) * 1000.0, 2)
            lit_hits = [c for c in rep["citations"] if c["kind"] == "literature"]
            row["modes"][mode_name] = {
                "latency_ms": ms,
                "backend": rep["backend"],
                "paper_hits": rep["paper_hits"],
                "passage_hits": rep["passage_hits"],
                "top_ids": [c["paperId"] for c in lit_hits[:top_k]],
                "top_3_titles": [c["title"] for c in lit_hits[:3]],
            }
        lex_ids = row["modes"]["lexical_bm25"]["top_ids"]
        row["jaccard_hash_vs_lexical"] = _jaccard(lex_ids, row["modes"]["hash_3way"]["top_ids"])
        if "neural_bge_3way" in row["modes"]:
            row["jaccard_neural_vs_lexical"] = _jaccard(lex_ids, row["modes"]["neural_bge_3way"]["top_ids"])
            row["jaccard_neural_vs_hash"] = _jaccard(
                row["modes"]["hash_3way"]["top_ids"],
                row["modes"]["neural_bge_3way"]["top_ids"],
            )
        results.append(row)

    summary = {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "corpus": lit_stats,
        "passages": pas_stats,
        "vectors": vstats,
        "neural_model": neural_model,
        "neural_active": neural_emb is not None,
        "neural_error": neural_error,
        "queries": results,
    }

    if out_md_path is not None:
        lines = [
            "# Layer B Tier 2 Neural RAG Benchmark (Round 186 / N127)",
            "",
            f"- **Timestamp (UTC):** `{summary['timestamp_utc']}`",
            "- **Status:** `exploratory_hypothesis_seed` (isolated Layer B; zero `census/` imports)",
            f"- **Corpus (`index.sqlite`):** `{lit_stats['paper_count']}` deduplicated papers",
            f"- **Passages (`passages.sqlite`):** `{pas_stats['passage_count']}` passages across `{pas_stats['doc_count']}` documents",
            f"- **Vectors (`vectors.sqlite`):** `{vstats['models']}`",
            f"- **Neural Embedder:** `{neural_model}` (`active={summary['neural_active']}`)",
            "",
            "## Latency & Ranking Overlap Across 5 Domain Queries",
            "",
            "| Query | Lexical (ms) | Hash 3-way (ms) | Neural BGE 3-way (ms) | Jaccard(Hash, Lex) | Jaccard(Neural, Lex) |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in results:
            m = r["modes"]
            lms = m["lexical_bm25"]["latency_ms"]
            hms = m["hash_3way"]["latency_ms"]
            nms = m["neural_bge_3way"]["latency_ms"] if "neural_bge_3way" in m else "n/a"
            jh = r["jaccard_hash_vs_lexical"]
            jn = r.get("jaccard_neural_vs_lexical", "n/a")
            lines.append(f"| {r['query'][:60]} | {lms} | {hms} | {nms} | {jh} | {jn} |")

        lines.extend(["", "## Top-3 Retrieved Papers per Query (Neural BGE 3-way vs. Lexical)"])
        for r in results:
            lines.append(f"\n### Query: `{r['query']}`")
            lines.append("- **Lexical BM25 top-3:**")
            for t in r["modes"]["lexical_bm25"]["top_3_titles"]:
                lines.append(f"  - {t}")
            if "neural_bge_3way" in r["modes"]:
                lines.append("- **Neural BGE 3-way top-3:**")
                for t in r["modes"]["neural_bge_3way"]["top_3_titles"]:
                    lines.append(f"  - {t}")

        out_p = Path(out_md_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run Layer B Tier 2 Neural RAG Benchmark.")
    ap.add_argument("--db", default=None)
    ap.add_argument("--passages-db", default=None)
    ap.add_argument("--vectors-db", default=None)
    ap.add_argument("--model", default=DEFAULT_NEURAL_MODEL)
    ap.add_argument("--out-md", default="docs/audits/layer_b_neural_rag_benchmark.md")
    args = ap.parse_args()
    rep = run_neural_benchmark(
        db_path=args.db,
        passages_db_path=args.passages_db,
        vector_db_path=args.vectors_db,
        neural_model=args.model,
        out_md_path=args.out_md,
    )
    print(json.dumps({
        "ok": rep["ok"],
        "neural_active": rep["neural_active"],
        "vectors": rep["vectors"],
        "out_md": args.out_md,
    }, indent=2))

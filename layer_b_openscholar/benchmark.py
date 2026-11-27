# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible 5-query benchmark harness comparing BM25 vs OpenScholar_Reranker."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Sequence

from .reranker import OpenScholarReranker

BENCHMARK_QUERIES: List[Dict[str, Any]] = [
    {"id": "Q1", "query": "Appalachia county cancer mortality poverty spatial disparities", "keywords": ["appalachia", "cancer", "poverty"]},
    {"id": "Q2", "query": "Medicare age 65 regression discontinuity uninsurance ACS PUMS", "keywords": ["medicare", "65", "uninsurance"]},
    {"id": "Q3", "query": "rural urban county poverty disparity difference in differences", "keywords": ["rural", "poverty", "county"]},
    {"id": "Q4", "query": "residential racial segregation measurement error ACS tracts", "keywords": ["segregation", "tract", "acs"]},
    {"id": "Q5", "query": "Fay Herriot small area estimation threshold designation PPV", "keywords": ["fay", "herriot", "small"]},
]


def evaluate_backend(
    papers_by_query: Dict[str, Sequence[Dict[str, Any]]],
    backend: str = "bm25",
    top_k: int = 5,
) -> Dict[str, Any]:
    reranker = OpenScholarReranker(backend=backend)
    rows = []
    t0 = time.perf_counter()
    for spec in BENCHMARK_QUERIES:
        qid = spec["id"]
        cand = papers_by_query.get(qid) or []
        ranked = reranker.rerank(spec["query"], cand, top_k=top_k)
        kws = spec["keywords"]
        hits = 0
        first_hit_rank = None
        for idx, p in enumerate(ranked, 1):
            blob = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
            if sum(1 for k in kws if k in blob) >= 2:
                hits += 1
                if first_hit_rank is None:
                    first_hit_rank = idx
        p_at_k = hits / max(len(ranked), 1)
        mrr = (1.0 / first_hit_rank) if first_hit_rank else 0.0
        rows.append({"id": qid, "candidates": len(cand), "precision_at_k": round(p_at_k, 4), "mrr": round(mrr, 4)})
    elapsed = time.perf_counter() - t0
    mean_p = sum(r["precision_at_k"] for r in rows) / max(len(rows), 1)
    mean_mrr = sum(r["mrr"] for r in rows) / max(len(rows), 1)
    return {
        "backend": reranker.active_backend,
        "top_k": top_k,
        "mean_precision_at_k": round(mean_p, 4),
        "mean_mrr": round(mean_mrr, 4),
        "elapsed_sec": round(elapsed, 4),
        "queries": rows,
    }

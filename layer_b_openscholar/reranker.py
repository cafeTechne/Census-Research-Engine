# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reranking layer: Hugging Face OpenScholar/OpenScholar_Reranker with deterministic BM25 fallback."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Sequence

MODEL_ID = "OpenScholar/OpenScholar_Reranker"
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _bm25_scores(query: str, docs: Sequence[str], k1: float = 1.5, b: float = 0.75) -> List[float]:
    if not docs:
        return []
    q_toks = _tokens(query)
    doc_toks = [_tokens(d) for d in docs]
    n = len(doc_toks)
    avgdl = sum(len(d) for d in doc_toks) / max(n, 1)
    df: Counter[str] = Counter()
    for d in doc_toks:
        df.update(set(d))
    scores: List[float] = []
    for d in doc_toks:
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for t in q_toks:
            f = tf.get(t, 0)
            if f == 0:
                continue
            idf = math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * (f * (k1 + 1.0)) / (f + k1 * (1.0 - b + b * dl / max(avgdl, 1.0)))
        scores.append(s)
    return scores


class OpenScholarReranker:
    """Reranks candidate papers against a research query.

    Uses ``OpenScholar/OpenScholar_Reranker`` (fine-tuned bge-reranker-large) when
    ``torch`` and ``transformers`` are available and ``backend in ("auto", "openscholar")``;
    otherwise falls back cleanly to deterministic BM25 lexical scoring.
    """

    def __init__(self, backend: str = "auto", model_id: str = MODEL_ID) -> None:
        if backend not in ("auto", "bm25", "openscholar"):
            raise ValueError(f"unsupported backend {backend!r}")
        self.requested_backend = backend
        self.model_id = model_id
        self.active_backend = "bm25"
        self._tokenizer = None
        self._model = None
        if backend in ("auto", "openscholar"):
            try:
                import torch  # noqa: F401
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(model_id)
                self._model = AutoModelForSequenceClassification.from_pretrained(model_id)
                self._model.eval()
                self.active_backend = "openscholar"
            except Exception:
                if backend == "openscholar":
                    raise
                self.active_backend = "bm25"

    def rerank(self, query: str, papers: Sequence[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        if not papers:
            return []
        texts = [f"{p.get('title', '')}. {p.get('abstract', '')}".strip() for p in papers]
        if self.active_backend == "openscholar" and self._model is not None and self._tokenizer is not None:
            import torch

            pairs = [[query, t] for t in texts]
            with torch.no_grad():
                enc = self._tokenizer(pairs, padding=True, truncation=True, max_length=512, return_tensors="pt")
                logits = self._model(**enc).logits.view(-1).cpu().tolist()
            scores = [float(x) for x in logits]
        else:
            scores = _bm25_scores(query, texts)

        ranked = []
        for paper, sc in zip(papers, scores):
            item = dict(paper)
            item["rerank_score"] = round(float(sc), 6)
            item["rerank_backend"] = self.active_backend
            ranked.append(item)
        ranked.sort(key=lambda r: (-r["rerank_score"], -int(r.get("citationCount") or 0), r.get("paperId", "")))
        return ranked[: max(int(top_k), 1)]

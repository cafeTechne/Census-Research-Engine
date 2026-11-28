# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tier 1 Domain-Specific Hybrid RAG v2 for isolated Layer B (strictly zero census imports).

Fuses literature hits from ``index.sqlite`` (FTS5 + BM25 reranker) and local study/PDF
passages from ``passages.sqlite`` via Reciprocal Rank Fusion (RRF), strips JATS/HTML tags
from Europe PMC abstracts, supports year/domain filters and BibTeX export, and builds
structured Evidence Briefs.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from .local_index import LocalLiteratureIndex, resolve_index_path
from .pdf_indexer import LocalPassageIndex
from .reranker import OpenScholarReranker

_TAG_RE = re.compile(r"<[^>]+>")


def strip_jats_html(text: str) -> str:
    """Remove JATS/XML/HTML tags (e.g. <h4>Introduction</h4>) and normalize whitespace."""
    cleaned = _TAG_RE.sub(" ", html.unescape(text or ""))
    return " ".join(cleaned.split())


def _paper_to_bibtex(p: Dict[str, Any], key: str) -> str:
    title = (p.get("title") or "Untitled").replace("{", "").replace("}", "")
    year = p.get("year") or ""
    doi = (p.get("doi") or "").strip()
    venue = (p.get("venue") or "").strip()
    authors = p.get("authors") or []
    author_str = " and ".join(authors[:6]) if isinstance(authors, list) else str(authors)
    lines = [f"@article{{{key},", f"  title = {{{title}}},"]
    if author_str:
        lines.append(f"  author = {{{author_str}}},")
    if venue:
        lines.append(f"  journal = {{{venue}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    lines.append("}")
    return "\n".join(lines)


def query_hybrid_rag(
    query: str,
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    top_k_papers: int = 8,
    top_k_passages: int = 5,
    rrf_k: int = 60,
    backend: str = "bm25",
    vector_model: Optional[str] = None,
    embedder: Optional[Any] = None,
    allow_subprocess_neural: bool = False,
    expand_synonyms: bool = True,
    min_year: Optional[int] = None,
    domain_filter: Optional[str] = None,
    export_bib_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Retrieve and RRF-fuse literature (FTS5 + BM25 + optional Vector Cosine) + local passages."""
    from .neural_bridge import DEFAULT_SSD_NEURAL_VENV, SubprocessNeuralEmbedder
    from .query_expansion import expand_domain_query
    from .vector_store import LocalVectorStore, SentenceTransformerEmbedder

    lit_idx = LocalLiteratureIndex(db_path)
    pas_idx = LocalPassageIndex(passages_db_path)

    fts_q, added_syns = expand_domain_query(query) if expand_synonyms else (query, [])
    fts_papers = lit_idx.search_fts(fts_q, limit=max(top_k_papers * 6, 40))
    if min_year is not None:
        fts_papers = [p for p in fts_papers if isinstance(p.get("year"), int) and p["year"] >= int(min_year)]
    if domain_filter:
        df_low = domain_filter.strip().lower()
        fts_papers = [
            p for p in fts_papers
            if df_low in str(p.get("source") or "").lower()
            or df_low in str(p.get("title") or "").lower()
            or df_low in str(p.get("abstract") or "").lower()
        ]

    reranker = OpenScholarReranker(backend=backend)
    bm25_papers = reranker.rerank(query, fts_papers, top_k=max(top_k_papers * 2, 15))
    passages = pas_idx.search_passages(query, limit=max(top_k_passages * 2, 10))

    # Optional 3rd RRF signal: cosine similarity from vectors.sqlite if present & non-empty
    vpath = Path(vector_db_path) if vector_db_path is not None else resolve_index_path(db_path).with_name("vectors.sqlite")
    vec_hits: List[Dict[str, Any]] = []
    used_vector = False
    active_vector_model: Optional[str] = None
    if vpath.exists() and vector_model != "none":
        chosen_embedder = embedder
        if chosen_embedder is None and vector_model and vector_model != "hash":
            try:
                chosen_embedder = SentenceTransformerEmbedder(model_name=vector_model)
            except Exception:
                if allow_subprocess_neural and DEFAULT_SSD_NEURAL_VENV.exists():
                    chosen_embedder = SubprocessNeuralEmbedder(model_name=vector_model)
                else:
                    chosen_embedder = None
        vstore = LocalVectorStore(db_path=vpath, embedder=chosen_embedder)
        if chosen_embedder is None and vector_model is None:
            # Auto-upgrade to a stored neural model if sentence_transformers is available in this runtime
            models_avail = vstore.model_counts()
            neural_models = [m for m in models_avail if not m.startswith("hash_projection_")]
            if neural_models:
                try:
                    vstore = LocalVectorStore(db_path=vpath, embedder=SentenceTransformerEmbedder(neural_models[0]))
                except Exception:
                    if allow_subprocess_neural and DEFAULT_SSD_NEURAL_VENV.exists():
                        vstore = LocalVectorStore(db_path=vpath, embedder=SubprocessNeuralEmbedder(neural_models[0]))
        if vstore.stats()["vector_count"] > 0:
            vec_hits = vstore.search(query, top_k=max(top_k_papers * 3, 20), min_year=min_year)
            used_vector = len(vec_hits) > 0
            if used_vector:
                active_vector_model = vstore.embedder.model_name

    fts_rank = {p.get("paperId") or p.get("title"): r for r, p in enumerate(fts_papers, 1)}
    bm25_rank = {p.get("paperId") or p.get("title"): r for r, p in enumerate(bm25_papers, 1)}
    vec_rank = {p.get("paperId") or p.get("title"): r for r, p in enumerate(vec_hits, 1)}
    by_key: Dict[str, Dict[str, Any]] = {}
    for p in bm25_papers:
        k = p.get("paperId") or p.get("title")
        if k not in by_key:
            by_key[k] = dict(p)
    for p in vec_hits:
        k = p.get("paperId") or p.get("title")
        if k not in by_key:
            by_key[k] = dict(p)

    fused_papers: List[Dict[str, Any]] = []
    for k, p in by_key.items():
        score = 0.0
        if k in fts_rank:
            score += 1.0 / (rrf_k + fts_rank[k])
        if k in bm25_rank:
            score += 1.0 / (rrf_k + bm25_rank[k])
        if k in vec_rank:
            score += 1.0 / (rrf_k + vec_rank[k])
        p["rrf_score"] = round(score, 6)
        fused_papers.append(p)
    fused_papers.sort(key=lambda x: x["rrf_score"], reverse=True)
    selected_papers = fused_papers[:top_k_papers]
    selected_passages = passages[:top_k_passages]

    citations: List[Dict[str, Any]] = []
    bib_entries: List[str] = []
    md_lines: List[str] = [
        f"# Exploratory Domain RAG Context: {query}",
        "",
        "- **Status:** `exploratory_hypothesis_seed` (not confirmatory Layer A evidence)",
        f"- **Literature Index:** `{resolve_index_path(db_path)}` ({lit_idx.stats()['paper_count']} papers)",
        f"- **Passage Index:** `{pas_idx.db_path}` ({pas_idx.stats()['passage_count']} passages)",
        "",
        "## Grounded Literature Evidence",
    ]
    for i, p in enumerate(selected_papers, 1):
        cite_tag = f"L{i}"
        doi = (p.get("doi") or "").strip()
        yr = p.get("year") or "n.d."
        abstract = strip_jats_html(p.get("abstract") or "")[:360]
        citations.append({
            "tag": cite_tag,
            "kind": "literature",
            "paperId": p.get("paperId"),
            "title": strip_jats_html(p.get("title") or ""),
            "year": p.get("year"),
            "venue": p.get("venue") or "",
            "doi": doi or None,
            "rrf_score": p["rrf_score"],
        })
        bib_entries.append(_paper_to_bibtex(p, f"layerb_{cite_tag.lower()}_{yr}"))
        md_lines.append(f"- **[{cite_tag}]** {strip_jats_html(p.get('title') or '')} ({yr})" + (f" — DOI:`{doi}`" if doi else ""))
        if abstract:
            md_lines.append(f"  > {abstract}")

    md_lines.extend(["", "## Grounded Local Study / PDF Passages"])
    for j, psg in enumerate(selected_passages, 1):
        cite_tag = f"P{j}"
        src = psg.get("source_path") or psg.get("doc_path") or "local"
        page = psg.get("page_num") or psg.get("page") or 1
        sha = str(psg.get("source_sha256") or "")[:12]
        snippet = strip_jats_html(str(psg.get("text") or ""))[:360]
        citations.append({
            "tag": cite_tag,
            "kind": "passage",
            "source": src,
            "page": page,
            "source_sha256": psg.get("source_sha256"),
        })
        md_lines.append(f"- **[{cite_tag}]** `{Path(str(src)).name}` (p.{page}, sha:`{sha}`)")
        if snippet:
            md_lines.append(f"  > {snippet}")

    bibtex_text = "\n\n".join(bib_entries) + ("\n" if bib_entries else "")
    if export_bib_path is not None:
        bp = Path(export_bib_path)
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(bibtex_text, encoding="utf-8")

    context_md = "\n".join(md_lines) + "\n"
    rag_sha = hashlib.sha256(
        json.dumps({"query": query, "citations": citations}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "query": query,
        "backend": f"rrf(fts5+{reranker.active_backend}{f'+vector({active_vector_model})' if used_vector else ''})+passages",
        "vector_model": active_vector_model,
        "expanded_terms": added_syns,
        "filters": {"min_year": min_year, "domain_filter": domain_filter},
        "paper_hits": len(selected_papers),
        "passage_hits": len(selected_passages),
        "rag_sha256": rag_sha,
        "citations": citations,
        "bibtex": bibtex_text,
        "context_markdown": context_md,
        "next_step": "Review cited [L#]/[P#] evidence, then run `draft-seed` or `run-pipeline` before Layer A pre-registration.",
    }


def build_evidence_brief(
    query: str,
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    top_k_papers: int = 10,
    min_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a structured exploratory Evidence Brief summarizing recency, venues, DOIs, and grounded RAG context."""
    rag = query_hybrid_rag(
        query,
        db_path=db_path,
        passages_db_path=passages_db_path,
        top_k_papers=top_k_papers,
        min_year=min_year,
    )
    lit_cites = [c for c in rag["citations"] if c["kind"] == "literature"]
    years = [c["year"] for c in lit_cites if isinstance(c.get("year"), int)]
    venues = Counter(c.get("venue") for c in lit_cites if c.get("venue"))
    dois = [c["doi"] for c in lit_cites if c.get("doi")]
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "query": query,
        "rag_sha256": rag["rag_sha256"],
        "paper_hits": rag["paper_hits"],
        "passage_hits": rag["passage_hits"],
        "year_range": [min(years), max(years)] if years else None,
        "recent_2022_plus_count": sum(1 for y in years if y >= 2022),
        "top_venues": venues.most_common(5),
        "dois": dois,
        "bibtex": rag["bibtex"],
        "context_markdown": rag["context_markdown"],
        "next_step": rag["next_step"],
    }

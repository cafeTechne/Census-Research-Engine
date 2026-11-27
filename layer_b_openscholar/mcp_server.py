# SPDX-License-Identifier: AGPL-3.0-or-later
"""Standalone Layer B FastMCP server (strictly isolated from census/)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .agenda import build_research_agenda as _build_research_agenda
from .agenda import write_research_agenda as _write_research_agenda
from .citation_expander import expand_seed_citations as _expand_seed_citations
from .corpus_miner import load_miner_status as _load_miner_status
from .daemon_ops import corpus_health_report as _corpus_health_report
from .epmc_client import EuropePMCClient, merge_and_deduplicate
from .fulltext_harvester import harvest_epmc_fulltext as _harvest_epmc_fulltext
from .gap_matrix import build_gap_matrix as _build_gap_matrix
from .handoff import build_dossier, write_dossier
from .handoff_bridge import run_exploratory_pipeline as _run_exploratory_pipeline
from .handoff_bridge import validate_and_bridge_seed as _validate_and_bridge_seed
from .local_index import LocalLiteratureIndex, resolve_index_path
from .maintenance import audit_and_compact_corpus as _audit_and_compact_corpus
from .maintenance import dedupe_title_duplicates as _dedupe_title_duplicates
from .manifest_seeder import draft_manifest_seed as _draft_manifest_seed
from .manifest_seeder import write_manifest_seed as _write_manifest_seed
from .pdf_indexer import LocalPassageIndex
from .rag import build_evidence_brief as _build_evidence_brief
from .rag import query_hybrid_rag as _query_hybrid_rag
from .reranker import OpenScholarReranker
from .s2_client import OpenAlexClient, SemanticScholarClient
from .trends import analyze_domain_trends as _analyze_domain_trends
from .vector_store import sync_from_literature_index as _sync_from_literature_index


def search_literature(
    query: str,
    source: str = "auto",
    limit: int = 20,
    top_k: int = 8,
    backend: str = "auto",
    year: Optional[str] = None,
    cache_dir: str = ".cache/layer_b_s2",
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Search ungated OpenAlex / Europe PMC (or S2 if S2_API_KEY is set), rerank, and return an exploratory dossier."""
    cdir = Path(cache_dir)
    if source == "epmc":
        papers, src = EuropePMCClient(cache_dir=cdir).search_papers(query, limit=limit, year=year), "epmc"
    elif source == "multi":
        oa = OpenAlexClient(cache_dir=cdir).search_papers(query, limit=limit, year=year)
        ep = EuropePMCClient(cache_dir=cdir).search_papers(query, limit=limit, year=year)
        papers, src = merge_and_deduplicate(oa, ep), "multi(openalex+epmc)"
    elif source == "s2":
        papers, src = SemanticScholarClient(cache_dir=cdir).search_papers(query, limit=limit, year=year), "s2"
    else:
        papers, src = OpenAlexClient(cache_dir=cdir).search_papers(query, limit=limit, year=year), "openalex"
    reranker = OpenScholarReranker(backend=backend)
    ranked = reranker.rerank(query, papers, top_k=top_k)
    dossier = build_dossier(query, ranked, backend=reranker.active_backend)
    dossier["retrieval_source"] = src
    paths = write_dossier(dossier, out_dir) if out_dir else None
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "source": src,
        "backend": reranker.active_backend,
        "dossier_sha256": dossier["dossier_sha256"],
        "paper_count": len(ranked),
        "papers": dossier["papers"],
        "paths": paths,
    }


def local_search_literature(
    query: str,
    db_path: Optional[str] = None,
    limit: int = 50,
    top_k: int = 8,
    backend: str = "auto",
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the offline Samsung 850 EVO SSD SQLite FTS5 index and rerank."""
    idx = LocalLiteratureIndex(db_path)
    papers = idx.search_fts(query, limit=limit)
    reranker = OpenScholarReranker(backend=backend)
    ranked = reranker.rerank(query, papers, top_k=top_k)
    dossier = build_dossier(query, ranked, backend=reranker.active_backend)
    dossier["retrieval_source"] = f"local_fts5:{resolve_index_path(db_path)}"
    paths = write_dossier(dossier, out_dir) if out_dir else None
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "source": dossier["retrieval_source"],
        "backend": reranker.active_backend,
        "dossier_sha256": dossier["dossier_sha256"],
        "paper_count": len(ranked),
        "papers": dossier["papers"],
        "paths": paths,
    }


def index_literature(
    papers: list[Dict[str, Any]],
    db_path: Optional[str] = None,
    source: str = "mcp",
) -> Dict[str, Any]:
    """Ingest normalized paper dicts into the offline SQLite FTS5 index."""
    idx = LocalLiteratureIndex(db_path)
    added = idx.ingest_papers(papers, source=source)
    return {"ok": True, "status": "exploratory_hypothesis_seed", "added": added, "stats": idx.stats()}


def index_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Report paper count and path of the offline SQLite FTS5 index."""
    idx = LocalLiteratureIndex(db_path)
    return {"ok": True, "status": "exploratory_hypothesis_seed", **idx.stats()}


def search_passages(query: str, db_path: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Search page-level local document passages with immutable source SHA-256 citations."""
    idx = LocalPassageIndex(db_path)
    hits = idx.search_passages(query, limit=limit)
    return {"ok": True, "status": "exploratory_hypothesis_seed", "passage_count": len(hits),
            "passages": hits, "stats": idx.stats()}


def build_gap_matrix(
    query: str,
    db_path: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Build a (geography x method x recency) evidence & gap matrix from the offline FTS5 index."""
    idx = LocalLiteratureIndex(db_path)
    papers = idx.search_fts(query, limit=limit)
    mat = _build_gap_matrix(papers, query=query)
    return {"ok": True, **mat}


def draft_manifest_seed_tool(
    topic: str,
    geography: str = "county",
    method_family: str = "small_area",
    db_path: Optional[str] = None,
    limit: int = 25,
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Draft an exploratory pre-registration scaffold from the offline FTS5 index (never auto-registered)."""
    idx = LocalLiteratureIndex(db_path)
    papers = idx.search_fts(topic, limit=limit)
    scaffold = _draft_manifest_seed(topic, papers, geography=geography, method_family=method_family)
    paths = _write_manifest_seed(scaffold, out_dir) if out_dir else None
    return {"ok": True, **scaffold, "paths": paths}


def validate_handoff_seed(
    seed_path: str,
    dossier_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate a Layer B manifest_seed.json provenance chain and emit a human-reviewable Layer A template."""
    return _validate_and_bridge_seed(seed_path, dossier_path=dossier_path)


def run_exploratory_pipeline(
    topic: str,
    out_dir: str,
    geography: str = "county",
    method_family: str = "small_area",
    db_path: Optional[str] = None,
    limit: int = 40,
    top_k: int = 10,
    backend: str = "bm25",
) -> Dict[str, Any]:
    """Run offline Layer B pipeline: local-search -> gap-matrix -> draft-seed -> provenance bridge validation."""
    return _run_exploratory_pipeline(
        topic,
        out_dir,
        geography=geography,
        method_family=method_family,
        db_path=db_path,
        limit=limit,
        top_k=top_k,
        backend=backend,
    )


def rag_query(
    query: str,
    db_path: Optional[str] = None,
    passages_db_path: Optional[str] = None,
    top_k_papers: int = 8,
    top_k_passages: int = 5,
) -> Dict[str, Any]:
    """Run Tier 1 Domain Hybrid RAG (FTS5 + BM25 RRF + local study passages) with inline [L#]/[P#] citations."""
    return _query_hybrid_rag(
        query,
        db_path=db_path,
        passages_db_path=passages_db_path,
        top_k_papers=top_k_papers,
        top_k_passages=top_k_passages,
    )


def miner_status(
    db_path: Optional[str] = None,
    state_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Report background corpus miner checkpoint state, 36-domain count, and SSD FTS5 index totals."""
    return _load_miner_status(db_path=db_path, state_path=state_path)


def expand_citations(
    work_id: str,
    db_path: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Expand 1-hop OpenAlex citing works for a seed work ID into the SSD FTS5 index."""
    return _expand_seed_citations(work_id, db_path=db_path, limit=limit)


def evidence_brief(
    query: str,
    db_path: Optional[str] = None,
    passages_db_path: Optional[str] = None,
    top_k_papers: int = 10,
    min_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a structured exploratory Evidence Brief (recency, top venues, DOIs, BibTeX, grounded RAG context)."""
    return _build_evidence_brief(
        query,
        db_path=db_path,
        passages_db_path=passages_db_path,
        top_k_papers=top_k_papers,
        min_year=min_year,
    )


def corpus_health(
    db_path: Optional[str] = None,
    passages_db_path: Optional[str] = None,
    state_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Report comprehensive Layer B SSD corpus health (DOI/abstract/recency coverage, passages, miner state)."""
    return _corpus_health_report(db_path=db_path, passages_db_path=passages_db_path, state_path=state_path)


def sync_vectors(
    db_path: Optional[str] = None,
    vector_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Incrementally embed all papers in index.sqlite into vectors.sqlite for 3-way Hybrid RAG."""
    return _sync_from_literature_index(db_path=db_path, vector_db_path=vector_db_path)


def build_research_agenda(
    db_path: Optional[str] = None,
    top_opportunities: int = 12,
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Synthesize a multi-domain exploratory research agenda ranking under-studied (geography x method) cells."""
    ag = _build_research_agenda(db_path=db_path, top_opportunities=top_opportunities)
    paths = _write_research_agenda(ag, out_dir) if out_dir else None
    return {**ag, "paths": paths}


def domain_trends(
    db_path: Optional[str] = None,
    top_n: int = 15,
) -> Dict[str, Any]:
    """Analyze per-domain publication velocity (pre-2020, 2020-2023, 2024+), median citations, and OA PDF rates."""
    return _analyze_domain_trends(db_path=db_path, top_n=top_n)


def compact_corpus(
    db_path: Optional[str] = None,
    vector_db_path: Optional[str] = None,
    vacuum: bool = True,
) -> Dict[str, Any]:
    """Audit FTS5 integrity, prune orphan vectors, report title duplicates, and VACUUM SQLite databases."""
    return _audit_and_compact_corpus(db_path=db_path, vector_db_path=vector_db_path, vacuum=vacuum)


def dedupe_corpus(
    db_path: Optional[str] = None,
    vector_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Merge cross-source normalized-title duplicates in index.sqlite (keeping richest DOI/abstract row) and prune vectors."""
    return _dedupe_title_duplicates(db_path=db_path, vector_db_path=vector_db_path)


def harvest_fulltext(
    db_path: Optional[str] = None,
    passages_db_path: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Harvest open-access Europe PMC JATS XML full-text sections into passages.sqlite."""
    return _harvest_epmc_fulltext(db_path=db_path, passages_db_path=passages_db_path, limit=limit)


_TOOL_REGISTRY = (
    ("search_literature", search_literature),
    ("local_search_literature", local_search_literature),
    ("index_literature", index_literature),
    ("index_stats", index_stats),
    ("search_passages", search_passages),
    ("build_gap_matrix", build_gap_matrix),
    ("draft_manifest_seed", draft_manifest_seed_tool),
    ("validate_handoff_seed", validate_handoff_seed),
    ("run_exploratory_pipeline", run_exploratory_pipeline),
    ("rag_query", rag_query),
    ("miner_status", miner_status),
    ("expand_citations", expand_citations),
    ("evidence_brief", evidence_brief),
    ("corpus_health", corpus_health),
    ("sync_vectors", sync_vectors),
    ("build_research_agenda", build_research_agenda),
    ("domain_trends", domain_trends),
    ("compact_corpus", compact_corpus),
    ("dedupe_corpus", dedupe_corpus),
    ("harvest_fulltext", harvest_fulltext),
)


def list_tool_names() -> list[str]:
    """Return the registered Layer B MCP tool names."""
    return [name for name, _ in _TOOL_REGISTRY]


def create_server():
    """Build a standalone FastMCP server exposing the 20 Layer B tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("layer-b-openscholar")
    for name, fn in _TOOL_REGISTRY:
        mcp.tool(name=name)(fn)
    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()

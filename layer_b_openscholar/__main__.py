# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI for Layer B OpenScholar (OpenAlex / Europe PMC / S2 + Samsung 850 EVO SSD FTS5 + Reranker)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .agenda import build_research_agenda, write_research_agenda
from .benchmark import BENCHMARK_QUERIES
from .citation_expander import expand_seed_citations
from .claim_grounder import ground_claims, write_grounding_markdown
from .corpus_miner import CorpusMiner, load_topics
from .daemon_ops import corpus_health_report, render_systemd_unit
from .epmc_client import EuropePMCClient, merge_and_deduplicate
from .fulltext_harvester import harvest_epmc_fulltext
from .gap_matrix import build_gap_matrix
from .handoff import build_dossier, write_dossier
from .handoff_bridge import run_exploratory_pipeline
from .local_index import LocalLiteratureIndex, resolve_index_path
from .maintenance import audit_and_compact_corpus, dedupe_title_duplicates
from .manifest_seeder import draft_manifest_seed, write_manifest_seed
from .neural_bridge import neural_runtime_status
from .pdf_indexer import LocalPassageIndex
from .rag import build_evidence_brief, query_hybrid_rag
from .reranker import OpenScholarReranker
from .s2_client import OpenAlexClient, SemanticScholarClient
from .trends import analyze_domain_trends
from .vector_store import sync_from_literature_index


def _fetch_online(query: str, source: str, limit: int, year: str | None, cache_dir: Path, expand_refs: bool):
    if source == "epmc":
        return EuropePMCClient(cache_dir=cache_dir).search_papers(query, limit=limit, year=year), "epmc"
    if source == "openalex":
        return OpenAlexClient(cache_dir=cache_dir).search_papers(query, limit=limit, year=year), "openalex"
    if source == "multi":
        oa = OpenAlexClient(cache_dir=cache_dir).search_papers(query, limit=limit, year=year)
        ep = EuropePMCClient(cache_dir=cache_dir).search_papers(query, limit=limit, year=year)
        return merge_and_deduplicate(oa, ep), "multi(openalex+epmc)"
    use_s2 = source == "s2" or (source == "auto" and bool(os.environ.get("S2_API_KEY")))
    if use_s2:
        client = SemanticScholarClient(cache_dir=cache_dir)
        try:
            papers = client.search_papers(query, limit=limit, year=year)
            if expand_refs and papers and papers[0].get("paperId"):
                seen_ids = {p["paperId"] for p in papers if p.get("paperId")}
                for ref in client.get_references(papers[0]["paperId"], limit=15):
                    if ref.get("paperId") and ref["paperId"] not in seen_ids:
                        papers.append(ref)
                        seen_ids.add(ref["paperId"])
            return papers, "s2"
        except Exception as exc:
            if source == "s2":
                raise
            print(f"Semantic Scholar unavailable ({type(exc).__name__}: {exc}); falling back to OpenAlex.", file=sys.stderr)
    return OpenAlexClient(cache_dir=cache_dir).search_papers(query, limit=limit, year=year), "openalex"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="layer_b_openscholar", description="Layer B upstream literature dossier tool.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Search online APIs, rerank, and emit a literature dossier.")
    p_search.add_argument("query", help="Scientific literature search query.")
    p_search.add_argument("--out", required=True, help="Output directory for dossier.json, references.bib, hypothesis_seeds.md.")
    p_search.add_argument("--limit", type=int, default=25)
    p_search.add_argument("--top-k", type=int, default=10)
    p_search.add_argument("--year", default=None)
    p_search.add_argument("--source", choices=("auto", "openalex", "epmc", "multi", "s2"), default="auto")
    p_search.add_argument("--backend", choices=("auto", "bm25", "openscholar"), default="auto")
    p_search.add_argument("--cache-dir", default=".cache/layer_b_s2")
    p_search.add_argument("--expand-refs", action="store_true")
    p_search.add_argument("--also-index", action="store_true", help="Ingest retrieved papers into the local SSD FTS5 index.")
    p_search.add_argument("--db", default=None, help="Override SQLite FTS5 index path (default: Samsung 850 EVO SSD).")

    p_build = sub.add_parser("build-index", help="Ingest JSONL or live topic query into the local SSD FTS5 index.")
    p_build.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_build.add_argument("--jsonl", default=None, help="Path to normalized papers JSONL file.")
    p_build.add_argument("--query", default=None, help="Optional live query to harvest and ingest.")
    p_build.add_argument("--source", choices=("auto", "openalex", "epmc", "multi", "s2"), default="multi")
    p_build.add_argument("--limit", type=int, default=50)
    p_build.add_argument("--cache-dir", default=".cache/layer_b_s2")

    p_local = sub.add_parser("local-search", help="Search the offline SSD SQLite FTS5 index and rerank.")
    p_local.add_argument("query", help="Offline search query.")
    p_local.add_argument("--out", required=True)
    p_local.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_local.add_argument("--limit", type=int, default=50)
    p_local.add_argument("--top-k", type=int, default=10)
    p_local.add_argument("--backend", choices=("auto", "bm25", "openscholar"), default="auto")

    p_seed = sub.add_parser("seed-domain", help="Harvest the 5 core epidemiology/demography topics into the SSD FTS5 index.")
    p_seed.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_seed.add_argument("--source", choices=("openalex", "epmc", "multi"), default="multi")
    p_seed.add_argument("--limit-per-query", type=int, default=20)
    p_seed.add_argument("--cache-dir", default=".cache/layer_b_s2")

    p_gap = sub.add_parser("gap-matrix", help="Build a geography x method x recency evidence & gap matrix from the local FTS5 index.")
    p_gap.add_argument("query", help="Topic query to retrieve from the local FTS5 index.")
    p_gap.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_gap.add_argument("--limit", type=int, default=50)
    p_gap.add_argument("--out", default=None, help="Optional JSON output path.")

    p_draft = sub.add_parser("draft-seed", help="Draft an exploratory pre-registration seed scaffold from the local FTS5 index.")
    p_draft.add_argument("topic", help="Research topic to retrieve and scaffold.")
    p_draft.add_argument("--geography", default="county")
    p_draft.add_argument("--method", default="small_area")
    p_draft.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_draft.add_argument("--limit", type=int, default=25)
    p_draft.add_argument("--out", default=None, help="Optional output directory for manifest_seed.json and manifest_seed.md.")

    p_pipe = sub.add_parser("run-pipeline", help="Run offline Layer B pipeline: local-search -> gap-matrix -> draft-seed -> bridge.")
    p_pipe.add_argument("topic", help="Research topic query.")
    p_pipe.add_argument("--out", required=True, help="Output directory for all pipeline artifacts.")
    p_pipe.add_argument("--geography", default="county")
    p_pipe.add_argument("--method", default="small_area")
    p_pipe.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_pipe.add_argument("--limit", type=int, default=40)
    p_pipe.add_argument("--top-k", type=int, default=10)
    p_pipe.add_argument("--backend", choices=("auto", "bm25", "openscholar"), default="bm25")

    p_mine = sub.add_parser("mine-corpus", help="Mine 24 domain topics from OpenAlex + Europe PMC into the SSD FTS5 index.")
    p_mine.add_argument("--daemon", action="store_true", help="Run indefinitely in a polite background loop.")
    p_mine.add_argument("--max-cycles", type=int, default=None, help="Optional cap on daemon cycles (None = indefinite).")
    p_mine.add_argument("--limit-per-query", type=int, default=25)
    p_mine.add_argument("--max-pages", type=int, default=10)
    p_mine.add_argument("--delay", type=float, default=1.5, help="Polite delay in seconds between topic requests.")
    p_mine.add_argument("--cycle-sleep", type=float, default=1800.0, help="Seconds to sleep between full 24-topic cycles.")
    p_mine.add_argument("--topics-file", default=None, help="Optional JSON file overriding the 24 default domain topics.")
    p_mine.add_argument("--db", default=None, help="SQLite FTS5 index path (default: Samsung 850 EVO SSD).")
    p_mine.add_argument("--state-file", default=None, help="Miner checkpoint JSON path (default: beside index.sqlite).")
    p_mine.add_argument("--cache-dir", default=".cache/layer_b_miner")

    p_rag = sub.add_parser("rag-query", help="Run Tier 1 Hybrid RAG (FTS5 + BM25 RRF + local passages) with inline citations.")
    p_rag.add_argument("query", help="Domain research question or keyword query.")
    p_rag.add_argument("--top-k", type=int, default=8)
    p_rag.add_argument("--top-passages", type=int, default=5)
    p_rag.add_argument("--db", default=None, help="Literature FTS5 index path (default: Samsung 850 EVO SSD).")
    p_rag.add_argument("--passages-db", default=None, help="Passage FTS5 index path (default: Samsung 850 EVO SSD).")
    p_rag.add_argument("--min-year", type=int, default=None)
    p_rag.add_argument("--domain", default=None)
    p_rag.add_argument("--bib-out", default=None, help="Optional BibTeX output path.")
    p_rag.add_argument("--out", default=None, help="Optional Markdown file path to save context_markdown.")

    p_exp = sub.add_parser("expand-citations", help="Expand 1-hop OpenAlex citing works for a seed work ID into FTS5.")
    p_exp.add_argument("work_id", help="OpenAlex work ID (e.g. W4408165420).")
    p_exp.add_argument("--limit", type=int, default=25)
    p_exp.add_argument("--db", default=None)

    p_hlth = sub.add_parser("corpus-health", help="Report SSD literature/passage coverage and background miner health.")
    p_hlth.add_argument("--db", default=None)
    p_hlth.add_argument("--passages-db", default=None)
    p_hlth.add_argument("--state-file", default=None)

    p_unit = sub.add_parser("systemd-unit", help="Print a reboot-persistent systemd --user service unit for the miner.")
    p_unit.add_argument("--db", default=None)
    p_unit.add_argument("--out", default=None, help="Optional file path to write the .service unit.")

    p_vec = sub.add_parser("sync-vectors", help="Embed all papers in index.sqlite into vectors.sqlite for 3-way Hybrid RAG.")
    p_vec.add_argument("--db", default=None)
    p_vec.add_argument("--vectors-db", default=None)
    p_vec.add_argument("--model", default=None, help="Optional SentenceTransformer model name (e.g. BAAI/bge-small-en-v1.5) or 'hash'.")

    p_ft = sub.add_parser("harvest-fulltext", help="Harvest open-access Europe PMC JATS XML full-text sections into passages.sqlite.")
    p_ft.add_argument("--db", default=None)
    p_ft.add_argument("--passages-db", default=None)
    p_ft.add_argument("--limit", type=int, default=20)
    p_ft.add_argument("--delay", type=float, default=0.5)
    p_ft.add_argument("--cache-dir", default=".cache/layer_b_epmc_xml")

    p_ns = sub.add_parser("neural-status", help="Report Tier 2 neural runtime capabilities and stored vector models.")
    p_ns.add_argument("--vectors-db", default=None)

    p_gc = sub.add_parser("ground-claims", help="Ground draft research claims against Layer B 3-way Hybrid RAG.")
    p_gc.add_argument("claims", nargs="+", help="One or more research claim strings to ground.")
    p_gc.add_argument("--db", default=None)
    p_gc.add_argument("--passages-db", default=None)
    p_gc.add_argument("--vectors-db", default=None)
    p_gc.add_argument("--model", default=None, help="Optional vector model name (e.g. BAAI/bge-small-en-v1.5).")
    p_gc.add_argument("--out-md", default=None, help="Optional Markdown audit output path.")
    p_gc.add_argument("--title", default="Layer B Claim Grounding Audit")

    p_ag = sub.add_parser("build-agenda", help="Synthesize a multi-domain exploratory research agenda from index.sqlite.")
    p_ag.add_argument("--db", default=None)
    p_ag.add_argument("--top", type=int, default=12)
    p_ag.add_argument("--out", default=None, help="Optional output directory for research_agenda.json and .md.")

    p_sp = sub.add_parser("sync-passages", help="Incrementally index local Markdown/TXT/PDF files into passages.sqlite.")
    p_sp.add_argument("directory", help="Directory to scan for .md, .txt, and .pdf files.")
    p_sp.add_argument("--passages-db", default=None)

    p_tr = sub.add_parser("domain-trends", help="Analyze per-domain publication velocity, citations, and OA PDF rates.")
    p_tr.add_argument("--db", default=None)
    p_tr.add_argument("--top", type=int, default=15)

    p_cmp = sub.add_parser("compact-corpus", help="Verify FTS5 integrity, prune orphan vectors, and VACUUM SSD SQLite DBs.")
    p_cmp.add_argument("--db", default=None)
    p_cmp.add_argument("--vectors-db", default=None)
    p_cmp.add_argument("--no-vacuum", action="store_true")

    p_dd = sub.add_parser("dedupe-corpus", help="Merge normalized-title duplicates in index.sqlite and prune orphan vectors.")
    p_dd.add_argument("--db", default=None)
    p_dd.add_argument("--vectors-db", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "search":
        papers, active_source = _fetch_online(
            args.query, args.source, args.limit, args.year, Path(args.cache_dir), args.expand_refs
        )
        if args.also_index and papers:
            LocalLiteratureIndex(args.db).ingest_papers(papers, source=active_source)
        reranker = OpenScholarReranker(backend=args.backend)
        ranked = reranker.rerank(args.query, papers, top_k=args.top_k)
        dossier = build_dossier(args.query, ranked, backend=reranker.active_backend)
        dossier["retrieval_source"] = active_source
        paths = write_dossier(dossier, args.out)
        print(json.dumps({"ok": True, "source": active_source, "paper_count": len(ranked),
                          "backend": reranker.active_backend, "dossier_sha256": dossier["dossier_sha256"],
                          "paths": paths}, indent=2))
        return 0

    if args.cmd == "build-index":
        idx = LocalLiteratureIndex(args.db)
        added = 0
        if args.jsonl:
            added += idx.ingest_jsonl(args.jsonl)
        if args.query:
            papers, src = _fetch_online(args.query, args.source, args.limit, None, Path(args.cache_dir), False)
            added += idx.ingest_papers(papers, source=src)
        print(json.dumps({"ok": True, "added": added, "stats": idx.stats()}, indent=2))
        return 0

    if args.cmd == "local-search":
        idx = LocalLiteratureIndex(args.db)
        papers = idx.search_fts(args.query, limit=args.limit)
        reranker = OpenScholarReranker(backend=args.backend)
        ranked = reranker.rerank(args.query, papers, top_k=args.top_k)
        dossier = build_dossier(args.query, ranked, backend=reranker.active_backend)
        dossier["retrieval_source"] = f"local_fts5:{resolve_index_path(args.db)}"
        paths = write_dossier(dossier, args.out)
        print(json.dumps({"ok": True, "source": dossier["retrieval_source"], "paper_count": len(ranked),
                          "backend": reranker.active_backend, "dossier_sha256": dossier["dossier_sha256"],
                          "paths": paths}, indent=2))
        return 0

    if args.cmd == "seed-domain":
        idx = LocalLiteratureIndex(args.db)
        total_added = 0
        for spec in BENCHMARK_QUERIES:
            papers, src = _fetch_online(spec["query"], args.source, args.limit_per_query, None, Path(args.cache_dir), False)
            total_added += idx.ingest_papers(papers, source=src)
        print(json.dumps({"ok": True, "queries": len(BENCHMARK_QUERIES), "added": total_added, "stats": idx.stats()}, indent=2))
        return 0

    if args.cmd == "gap-matrix":
        idx = LocalLiteratureIndex(args.db)
        papers = idx.search_fts(args.query, limit=args.limit)
        report = build_gap_matrix(papers, query=args.query)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if args.cmd == "draft-seed":
        idx = LocalLiteratureIndex(args.db)
        papers = idx.search_fts(args.topic, limit=args.limit)
        scaffold = draft_manifest_seed(args.topic, papers, geography=args.geography, method_family=args.method)
        paths = write_manifest_seed(scaffold, args.out) if args.out else None
        print(json.dumps({"ok": True, "seed_id": scaffold["seed_id"], "seed_sha256": scaffold["seed_sha256"],
                          "status": scaffold["status"], "paths": paths}, indent=2))
        return 0

    if args.cmd == "run-pipeline":
        rep = run_exploratory_pipeline(
            args.topic,
            args.out,
            geography=args.geography,
            method_family=args.method,
            db_path=args.db,
            limit=args.limit,
            top_k=args.top_k,
            backend=args.backend,
        )
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1

    if args.cmd == "mine-corpus":
        miner = CorpusMiner(
            db_path=args.db,
            state_path=args.state_file,
            cache_dir=args.cache_dir,
            topics=load_topics(args.topics_file),
            limit_per_query=args.limit_per_query,
            max_pages_per_topic=args.max_pages,
            delay_seconds=args.delay,
            cycle_sleep_seconds=args.cycle_sleep,
        )
        if args.daemon:
            return miner.run_forever(max_cycles=args.max_cycles)
        rep = miner.run_once(log_stream=sys.stderr)
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "rag-query":
        rep = query_hybrid_rag(
            args.query,
            db_path=args.db,
            passages_db_path=args.passages_db,
            top_k_papers=args.top_k,
            top_k_passages=args.top_passages,
            min_year=args.min_year,
            domain_filter=args.domain,
            export_bib_path=args.bib_out,
        )
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(rep["context_markdown"], encoding="utf-8")
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "expand-citations":
        rep = expand_seed_citations(args.work_id, db_path=args.db, limit=args.limit)
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "corpus-health":
        rep = corpus_health_report(db_path=args.db, passages_db_path=args.passages_db, state_path=args.state_file)
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "systemd-unit":
        unit = render_systemd_unit(workdir=Path.cwd(), db_path=args.db)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(unit, encoding="utf-8")
        print(unit)
        return 0

    if args.cmd == "sync-vectors":
        rep = sync_from_literature_index(db_path=args.db, vector_db_path=args.vectors_db, model_name=args.model)
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "harvest-fulltext":
        rep = harvest_epmc_fulltext(
            db_path=args.db,
            passages_db_path=args.passages_db,
            cache_dir=args.cache_dir,
            limit=args.limit,
            delay_seconds=args.delay,
        )
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "neural-status":
        print(json.dumps(neural_runtime_status(vector_db_path=args.vectors_db), indent=2))
        return 0

    if args.cmd == "ground-claims":
        rep = ground_claims(
            args.claims,
            db_path=args.db,
            passages_db_path=args.passages_db,
            vector_db_path=args.vectors_db,
            vector_model=args.model,
        )
        if args.out_md:
            write_grounding_markdown(rep, args.out_md, title=args.title)
        print(json.dumps({
            "ok": rep["ok"],
            "backend": rep["backend"],
            "vector_model": rep["vector_model"],
            "grounded_count": rep["grounded_count"],
            "claim_count": rep["claim_count"],
            "unique_doi_count": rep["unique_doi_count"],
            "out_md": args.out_md,
        }, indent=2))
        return 0

    if args.cmd == "build-agenda":
        ag = build_research_agenda(db_path=args.db, top_opportunities=args.top)
        paths = write_research_agenda(ag, args.out) if args.out else None
        print(json.dumps({"ok": True, "domains_scanned": ag["domains_scanned"], "agenda_sha256": ag["agenda_sha256"],
                          "top_count": len(ag["top_opportunities"]), "paths": paths}, indent=2))
        return 0

    if args.cmd == "sync-passages":
        pidx = LocalPassageIndex(args.passages_db)
        root = Path(args.directory)
        files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".txt", ".pdf"))
        added = sum(pidx.index_file(f) for f in files)
        print(json.dumps({"ok": True, "files_scanned": len(files), "passages_added": added, "stats": pidx.stats()}, indent=2))
        return 0

    if args.cmd == "domain-trends":
        rep = analyze_domain_trends(db_path=args.db, top_n=args.top)
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "compact-corpus":
        rep = audit_and_compact_corpus(db_path=args.db, vector_db_path=args.vectors_db, vacuum=not args.no_vacuum)
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1

    if args.cmd == "dedupe-corpus":
        rep = dedupe_title_duplicates(db_path=args.db, vector_db_path=args.vectors_db)
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())

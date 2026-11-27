# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI for Layer B OpenScholar (Semantic Scholar + OpenScholar_Reranker) prototype."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .handoff import build_dossier, write_dossier
from .reranker import OpenScholarReranker
from .s2_client import OpenAlexClient, SemanticScholarClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="layer_b_openscholar", description="Layer B upstream literature dossier tool.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_search = sub.add_parser("search", help="Search Semantic Scholar (or OpenAlex fallback), rerank, and emit a dossier.")
    p_search.add_argument("query", help="Scientific literature search query.")
    p_search.add_argument("--out", required=True, help="Output directory for dossier.json, references.bib, hypothesis_seeds.md.")
    p_search.add_argument("--limit", type=int, default=25, help="Number of papers to retrieve.")
    p_search.add_argument("--top-k", type=int, default=10, help="Number of reranked papers to retain.")
    p_search.add_argument("--year", default=None, help="Optional year filter (e.g. 2015-2026).")
    p_search.add_argument("--source", choices=("auto", "s2", "openalex"), default="auto",
                          help="Retrieval API: auto tries Semantic Scholar then falls back to OpenAlex on 429.")
    p_search.add_argument("--backend", choices=("auto", "bm25", "openscholar"), default="auto")
    p_search.add_argument("--cache-dir", default=".cache/layer_b_s2", help="Disk cache directory for API responses.")
    p_search.add_argument("--expand-refs", action="store_true", help="Also pull references of the top retrieved paper (S2).")

    args = parser.parse_args(argv)
    if args.cmd == "search":
        cache_dir = Path(args.cache_dir)
        active_source = args.source
        papers = []
        use_s2 = args.source == "s2" or (args.source == "auto" and bool(os.environ.get("S2_API_KEY")))
        if use_s2:
            client = SemanticScholarClient(cache_dir=cache_dir)
            try:
                papers = client.search_papers(args.query, limit=args.limit, year=args.year)
                active_source = "s2"
                if args.expand_refs and papers and papers[0].get("paperId"):
                    seen_ids = {p["paperId"] for p in papers if p.get("paperId")}
                    for ref in client.get_references(papers[0]["paperId"], limit=15):
                        if ref.get("paperId") and ref["paperId"] not in seen_ids:
                            papers.append(ref)
                            seen_ids.add(ref["paperId"])
            except Exception as exc:
                if args.source == "s2":
                    raise
                print(f"Semantic Scholar unavailable ({type(exc).__name__}: {exc}); falling back to OpenAlex.", file=sys.stderr)
                papers = OpenAlexClient(cache_dir=cache_dir).search_papers(args.query, limit=args.limit, year=args.year)
                active_source = "openalex"
        else:
            papers = OpenAlexClient(cache_dir=cache_dir).search_papers(args.query, limit=args.limit, year=args.year)
            active_source = "openalex"
        reranker = OpenScholarReranker(backend=args.backend)
        ranked = reranker.rerank(args.query, papers, top_k=args.top_k)
        dossier = build_dossier(args.query, ranked, backend=reranker.active_backend)
        dossier["retrieval_source"] = active_source
        paths = write_dossier(dossier, args.out)
        print(json.dumps({"ok": True, "source": active_source, "paper_count": len(ranked),
                          "backend": reranker.active_backend, "dossier_sha256": dossier["dossier_sha256"],
                          "paths": paths}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

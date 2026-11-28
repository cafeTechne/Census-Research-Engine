# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 194: Cross-corpus claim grounding & citation auditor for isolated Layer B (zero census imports)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .rag import query_hybrid_rag


def ground_claims(
    claims: Sequence[str],
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    top_k_papers: int = 4,
    top_k_passages: int = 2,
    vector_model: Optional[str] = None,
    embedder: Optional[Any] = None,
) -> Dict[str, Any]:
    """Ground a sequence of draft research claims against Layer B's 3-way Hybrid RAG index."""
    cleaned = [str(c).strip() for c in claims if str(c).strip()]
    items: List[Dict[str, Any]] = []
    all_dois: List[str] = []
    seen_dois: set[str] = set()
    bib_blocks: List[str] = []
    active_backend = ""
    active_vmodel = None

    for idx, claim in enumerate(cleaned, 1):
        rag = query_hybrid_rag(
            claim,
            db_path=db_path,
            passages_db_path=passages_db_path,
            vector_db_path=vector_db_path,
            top_k_papers=top_k_papers,
            top_k_passages=top_k_passages,
            vector_model=vector_model,
            embedder=embedder,
        )
        active_backend = rag["backend"]
        active_vmodel = rag.get("vector_model")
        lit_cites = [c for c in rag["citations"] if c["kind"] == "literature"]
        pas_cites = [c for c in rag["citations"] if c["kind"] == "passage"]
        claim_dois = [c["doi"] for c in lit_cites if c.get("doi")]
        for d in claim_dois:
            if d not in seen_dois:
                seen_dois.add(d)
                all_dois.append(d)
        if rag.get("bibtex"):
            bib_blocks.append(rag["bibtex"].strip())
        grounded = len(lit_cites) > 0 or len(pas_cites) > 0
        items.append({
            "claim_id": f"C{idx}",
            "claim": claim,
            "grounded": grounded,
            "paper_hits": len(lit_cites),
            "passage_hits": len(pas_cites),
            "top_papers": [
                {"title": c["title"], "year": c.get("year"), "doi": c.get("doi"), "rrf_score": c.get("rrf_score")}
                for c in lit_cites[:top_k_papers]
            ],
            "top_passages": [
                {"source": Path(str(c["source"])).name, "page": c.get("page")}
                for c in pas_cites[:top_k_passages]
            ],
            "dois": claim_dois,
        })

    n_grounded = sum(1 for it in items if it["grounded"])
    coverage = round(n_grounded / max(len(items), 1), 4) if items else 0.0
    sha = hashlib.sha256(
        json.dumps({"claims": cleaned, "items": items}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": active_backend,
        "vector_model": active_vmodel,
        "claim_count": len(items),
        "grounded_count": n_grounded,
        "grounding_coverage": coverage,
        "unique_doi_count": len(all_dois),
        "dois": all_dois,
        "grounding_sha256": sha,
        "items": items,
        "bibtex": "\n\n".join(bib_blocks) + ("\n" if bib_blocks else ""),
    }


def write_grounding_markdown(report: Dict[str, Any], out_md_path: str | Path, title: str = "Layer B Claim Grounding Audit") -> str:
    """Render a claim-grounding report to Markdown."""
    lines = [
        f"# {title}",
        "",
        f"- **Timestamp (UTC):** `{report['timestamp_utc']}`",
        f"- **Status:** `{report['status']}` (isolated Layer B; not confirmatory Layer A evidence)",
        f"- **Retrieval Backend:** `{report['backend']}`",
        f"- **Vector Model:** `{report.get('vector_model')}`",
        f"- **Coverage:** `{report['grounded_count']}/{report['claim_count']}` claims grounded (`{report['grounding_coverage']*100:.1f}%`), `{report['unique_doi_count']}` unique DOIs",
        f"- **Grounding SHA-256:** `{report['grounding_sha256']}`",
        "",
        "## Claim-by-Claim Literature & Passage Grounding",
    ]
    for it in report["items"]:
        lines.append(f"\n### {it['claim_id']}: {it['claim']}")
        lines.append(f"- **Grounded:** `{it['grounded']}` (`{it['paper_hits']}` papers, `{it['passage_hits']}` passages)")
        for p in it["top_papers"]:
            doi_s = f" — DOI:`{p['doi']}`" if p.get("doi") else ""
            lines.append(f"  - {p['title']} ({p.get('year') or 'n.d.'}){doi_s}")
        for ps in it["top_passages"]:
            lines.append(f"  - Passage: `{ps['source']}` (p.{ps.get('page')})")
    out_p = Path(out_md_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out_p)

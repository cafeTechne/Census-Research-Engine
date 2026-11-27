# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 169: Multi-Domain Research Agenda Synthesizer for isolated Layer B (zero census imports).

Scans the offline SSD corpus across multiple domains, ranks under-studied (geography x method)
research opportunities with supporting DOIs, and writes a human-reviewable exploratory agenda.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .corpus_miner import DOMAIN_TOPICS
from .gap_matrix import build_gap_matrix
from .local_index import LocalLiteratureIndex


def build_research_agenda(
    *,
    db_path: Optional[str | Path] = None,
    domain_ids: Optional[Sequence[str]] = None,
    limit_per_domain: int = 30,
    top_opportunities: int = 12,
) -> Dict[str, Any]:
    """Scan selected (or all 36) domains in index.sqlite and rank top exploratory research-gap opportunities."""
    idx = LocalLiteratureIndex(db_path)
    topics = (
        [t for t in DOMAIN_TOPICS if t["id"] in set(domain_ids)]
        if domain_ids is not None
        else list(DOMAIN_TOPICS)
    )

    domain_summaries: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []
    for t in topics:
        papers = idx.search_fts(t["query"], limit=limit_per_domain)
        mat = build_gap_matrix(papers, query=t["query"])
        dois = [p["doi"] for p in papers[:5] if p.get("doi")]
        domain_summaries.append({
            "id": t["id"],
            "domain": t["domain"],
            "paper_count": len(papers),
            "covered_cell_count": len(mat["covered_cells"]),
            "gap_count": len(mat["gap_proposals"]),
        })
        for prop in mat["gap_proposals"][:2]:
            opportunities.append({
                "domain_id": t["id"],
                "domain": t["domain"],
                "geography": prop.get("geography", "county"),
                "method": prop.get("method", "unknown"),
                "rationale": prop.get("rationale") or prop.get("proposed_question") or prop.get("gap_cell") or "",
                "supporting_paper_count": len(papers),
                "sample_dois": dois[:3],
                "status": "exploratory_hypothesis_seed",
            })

    # Prioritize opportunities in well-evidenced domains with clear method/geography gaps
    opportunities.sort(key=lambda o: (-o["supporting_paper_count"], o["domain_id"], o["geography"], o["method"]))
    top_opps = opportunities[:top_opportunities]
    agenda_sha = hashlib.sha256(
        json.dumps({"domains": domain_summaries, "top": top_opps}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "domains_scanned": len(topics),
        "index_stats": idx.stats(),
        "agenda_sha256": agenda_sha,
        "domain_summaries": domain_summaries,
        "top_opportunities": top_opps,
        "next_step": "Pick an opportunity, run `run-pipeline` for that topic, then pre-register in Layer A.",
    }


def write_research_agenda(agenda: Dict[str, Any], out_dir: str | Path) -> Dict[str, str]:
    """Write ``research_agenda.json`` and human-reviewable ``research_agenda.md``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jpath = out / "research_agenda.json"
    mpath = out / "research_agenda.md"
    jpath.write_text(json.dumps(agenda, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Exploratory Multi-Domain Research Agenda (Layer B)",
        "",
        f"- **Status:** `{agenda['status']}` (requires human review & Layer A pre-registration)",
        f"- **Domains Scanned:** {agenda['domains_scanned']}",
        f"- **Corpus Size:** {agenda['index_stats']['paper_count']} papers",
        f"- **Agenda SHA-256:** `{agenda['agenda_sha256']}`",
        "",
        "## Top Ranked Exploratory Opportunities",
        "",
        "| # | Domain | Gap Geography | Gap Method | Supporting Papers | Sample DOIs |",
        "| :---: | :--- | :--- | :--- | :---: | :--- |",
    ]
    for i, opp in enumerate(agenda["top_opportunities"], 1):
        dois = ", ".join(f"`{d}`" for d in opp["sample_dois"]) or "—"
        lines.append(
            f"| {i} | `{opp['domain_id']}` {opp['domain']} | `{opp['geography']}` | `{opp['method']}` | {opp['supporting_paper_count']} | {dois} |"
        )
    mpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(jpath), "markdown": str(mpath)}

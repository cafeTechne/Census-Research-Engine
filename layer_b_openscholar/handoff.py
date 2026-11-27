# SPDX-License-Identifier: AGPL-3.0-or-later
"""Literature dossier, BibTeX export, and pre-registration handoff (Layer B -> Layer A)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


def _citekey(paper: Dict[str, Any], used: set[str]) -> str:
    first_author = (paper.get("authors") or ["unknown"])[0].split()[-1]
    clean = re.sub(r"[^a-z0-9]", "", first_author.lower()) or "ref"
    yr = str(paper.get("year") or "nd")
    base = f"{clean}{yr}"
    key = base
    idx = 2
    while key in used:
        key = f"{base}_{idx}"
        idx += 1
    used.add(key)
    return key


def paper_to_bibtex(paper: Dict[str, Any], citekey: str) -> str:
    authors = " and ".join(paper.get("authors") or ["Unknown"])
    title = (paper.get("title") or "").replace("{", "").replace("}", "")
    venue = paper.get("venue") or ""
    year = paper.get("year") or ""
    doi = paper.get("doi") or ""
    url = paper.get("url") or ""
    kind = "article" if venue else "misc"
    lines = [
        f"@{kind}{{{citekey},",
        f"  author = {{{authors}}},",
        f"  title = {{{{{title}}}}},",
    ]
    if venue:
        lines.append(f"  journal = {{{venue}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if url:
        lines.append(f"  url = {{{url}}},")
    lines.append(f"  note = {{Semantic Scholar ID: {paper.get('paperId', '')}}}")
    lines.append("}")
    return "\n".join(lines)


def build_dossier(
    query: str,
    ranked_papers: Sequence[Dict[str, Any]],
    backend: str,
    created: str | None = None,
) -> Dict[str, Any]:
    """Assemble a canonical, content-hashed literature dossier for upstream hypothesis generation."""
    used_keys: set[str] = set()
    papers_out: List[Dict[str, Any]] = []
    bib_entries: List[str] = []
    for p in ranked_papers:
        ck = _citekey(p, used_keys)
        entry = dict(p)
        entry["citekey"] = ck
        papers_out.append(entry)
        bib_entries.append(paper_to_bibtex(entry, ck))

    body = {
        "schema_version": 1,
        "status": "exploratory_hypothesis_seed",
        "epistemic_notice": (
            "Upstream literature synthesis for hypothesis generation only; never confirmatory proof. "
            "Pre-register empirical designs separately in Census-Research-Engine."
        ),
        "query": query,
        "rerank_backend": backend,
        "created": created or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paper_count": len(papers_out),
        "papers": papers_out,
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    body["dossier_sha256"] = digest
    body["bibtex"] = "\n\n".join(bib_entries) + ("\n" if bib_entries else "")
    return body


def render_hypothesis_seeds_md(dossier: Dict[str, Any]) -> str:
    lines = [
        f"# Literature Dossier & Hypothesis Seeds",
        "",
        f"- **Query:** `{dossier['query']}`",
        f"- **Status:** `{dossier['status']}` (upstream discovery only — never confirmatory)",
        f"- **Reranker backend:** `{dossier['rerank_backend']}`",
        f"- **Dossier SHA-256:** `{dossier['dossier_sha256']}`",
        "",
        "## Top-Ranked Literature",
        "",
        "| Rank | Citekey | Year | Citations | Score | Title | DOI / S2 ID |",
        "| ---: | :--- | ---: | ---: | ---: | :--- | :--- |",
    ]
    for i, p in enumerate(dossier["papers"], 1):
        ident = p.get("doi") or p.get("paperId") or ""
        title = (p.get("title") or "").replace("|", "/")
        lines.append(
            f"| {i} | `{p['citekey']}` | {p.get('year') or ''} | {p.get('citationCount', 0)} | "
            f"{p.get('rerank_score', 0):.3f} | {title} | `{ident}` |"
        )
    lines += [
        "",
        "## Pre-Registration Handoff Stub (for Census-Research-Engine `protocol`)",
        "",
        "```json",
        json.dumps(
            {
                "literature_dossier": {
                    "query": dossier["query"],
                    "dossier_sha256": dossier["dossier_sha256"],
                    "citekeys": [p["citekey"] for p in dossier["papers"][:5]],
                    "dois": [p["doi"] for p in dossier["papers"][:5] if p.get("doi")],
                }
            },
            indent=2,
        ),
        "```",
        "",
    ]
    return "\n".join(lines)


def write_dossier(dossier: Dict[str, Any], out_dir: str | Path) -> Dict[str, str]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    dossier_json = dict(dossier)
    bib = dossier_json.pop("bibtex", "")
    p_json = root / "dossier.json"
    p_bib = root / "references.bib"
    p_md = root / "hypothesis_seeds.md"
    p_json.write_text(json.dumps(dossier_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    p_bib.write_text(bib, encoding="utf-8")
    p_md.write_text(render_hypothesis_seeds_md(dossier), encoding="utf-8")
    return {"dossier_json": str(p_json), "references_bib": str(p_bib), "hypothesis_seeds_md": str(p_md)}

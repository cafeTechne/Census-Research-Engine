# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 186: Europe PMC Open-Access JATS XML full-text section harvester for Layer B.

Fetches full-text JATS XML for open-access PMC articles stored in ``index.sqlite``,
parses structured sections (Introduction, Methods, Results, Discussion, Limitations),
chunks them cleanly, and ingests them into ``passages.sqlite`` with immutable SHA-256
source hashes. Strictly isolated from ``census/`` (zero census imports).
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .local_index import resolve_index_path
from .pdf_indexer import LocalPassageIndex, _chunk_text
from .rag import strip_jats_html

EPMC_FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
PMC_OAI_PMH_URL = "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{num}&metadataPrefix=pmc"
ARXIV_HTML_URL = "https://arxiv.org/html/{arxiv_id}"
USER_AGENT = "ResearchIntelligence-LayerB/0.1"
_PMC_RE = re.compile(r"\bPMC(\d+)\b")


def fetch_oa_fulltext_with_fallback(
    pmcid: str,
    *,
    arxiv_id: str = "",
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = 2,
    http_get_text: Optional[Callable[[str, Dict[str, str]], str]] = None,
) -> tuple[Optional[str], str, str]:
    """3-tier OA full-text fallback: Europe PMC XML -> NCBI PMC OAI-PMH -> arXiv HTML.

    Returns ``(text_or_none, source_used, last_error)``.
    """
    hdrs = headers or {"User-Agent": USER_AGENT, "Accept": "application/xml, text/html"}
    m_num = _PMC_RE.search(pmcid or "")
    attempts: List[tuple[str, str]] = []
    if pmcid:
        attempts.append(("epmc_xml", EPMC_FULLTEXT_URL.format(pmcid=pmcid)))
    if m_num:
        attempts.append(("pmc_oai_pmh", PMC_OAI_PMH_URL.format(num=m_num.group(1))))
    if arxiv_id:
        attempts.append(("arxiv_html", ARXIV_HTML_URL.format(arxiv_id=arxiv_id.strip())))

    last_err = ""
    for src_name, url in attempts:
        for attempt in range(max(int(max_retries), 1)):
            try:
                if http_get_text is not None:
                    txt = http_get_text(url, hdrs)
                    if txt and ("<article" in txt[:4000] or "<body" in txt[:4000] or len(txt) >= 120):
                        return txt, src_name, ""
                    last_err = f"{src_name}:empty_or_non_article"
                    break
                import requests

                resp = requests.get(url, headers=hdrs, timeout=20)
                if resp.status_code == 200 and (
                    "<article" in resp.text[:4000] or "<body" in resp.text[:4000]
                ):
                    return resp.text, src_name, ""
                last_err = f"{src_name}:HTTP {resp.status_code}"
                if resp.status_code >= 500 and attempt + 1 < max(int(max_retries), 1):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break
            except Exception as exc:
                last_err = f"{src_name}:{type(exc).__name__}: {exc}"
                if attempt + 1 < max(int(max_retries), 1):
                    time.sleep(0.5 * (attempt + 1))
                    continue
    return None, "", last_err or "unavailable"


def parse_jats_sections(xml_text: str) -> List[Dict[str, str]]:
    """Parse JATS XML into ordered ``[{section_title, text}]`` blocks."""
    if not (xml_text or "").strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        cleaned = strip_jats_html(xml_text)
        return [{"section_title": "Full Text", "text": cleaned}] if cleaned else []

    sections: List[Dict[str, str]] = []

    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].lower() if "}" in tag else tag.lower()

    # Extract abstract first if present
    for el in root.iter():
        if _local(el.tag) == "abstract":
            txt = " ".join(" ".join(el.itertext()).split())
            if len(txt) >= 40:
                sections.append({"section_title": "Abstract", "text": txt})
            break

    # Extract top-level body sections
    body = None
    for el in root.iter():
        if _local(el.tag) == "body":
            body = el
            break

    if body is not None:
        top_secs = [child for child in body if _local(child.tag) == "sec"]
        if top_secs:
            for sec in top_secs:
                title = "Section"
                for child in sec:
                    if _local(child.tag) == "title":
                        title = " ".join(" ".join(child.itertext()).split()) or "Section"
                        break
                txt = " ".join(" ".join(sec.itertext()).split())
                if txt.startswith(title):
                    txt = txt[len(title):].strip()
                if len(txt) >= 40:
                    sections.append({"section_title": title, "text": txt})
        else:
            txt = " ".join(" ".join(body.itertext()).split())
            if len(txt) >= 40:
                sections.append({"section_title": "Body", "text": txt})

    if not sections:
        fallback = " ".join(" ".join(root.itertext()).split())
        if len(fallback) >= 40:
            sections.append({"section_title": "Full Text", "text": fallback})
    return sections


def find_pmc_candidates(db_path: Optional[str | Path] = None, limit: int = 25) -> List[Dict[str, Any]]:
    """Find open-access PMC article IDs stored in ``index.sqlite``."""
    lit_path = resolve_index_path(db_path)
    if not lit_path.exists():
        return []
    candidates: List[Dict[str, Any]] = []
    seen: set[str] = set()
    with sqlite3.connect(lit_path) as conn:
        rows = conn.execute(
            "SELECT paper_id, title, doi, year, url, open_access_pdf FROM papers "
            "WHERE paper_id LIKE 'PMC%' OR url LIKE '%PMC%' OR open_access_pdf LIKE '%PMC%' "
            "ORDER BY citation_count DESC, year DESC LIMIT ?",
            (max(int(limit) * 4, 100),),
        ).fetchall()
    for paper_id, title, doi, year, url, oa_pdf in rows:
        pmcid = None
        if isinstance(paper_id, str) and _PMC_RE.fullmatch(paper_id.strip()):
            pmcid = paper_id.strip()
        else:
            for field in (oa_pdf, url):
                if field:
                    m = _PMC_RE.search(str(field))
                    if m:
                        pmcid = m.group(0)
                        break
        if pmcid and pmcid not in seen:
            seen.add(pmcid)
            candidates.append({
                "pmcid": pmcid,
                "paper_id": paper_id,
                "title": title or "",
                "doi": doi or "",
                "year": year,
            })
            if len(candidates) >= int(limit):
                break
    return candidates


def ingest_jats_xml_to_passages(
    pmcid: str,
    xml_text: str,
    *,
    passages_db_path: Optional[str | Path] = None,
    title: str = "",
    max_chars: int = 1000,
) -> int:
    """Parse JATS XML for ``pmcid`` and insert section-labelled chunks into ``passages.sqlite``."""
    sections = parse_jats_sections(xml_text)
    if not sections:
        return 0
    xml_sha = hashlib.sha256(xml_text.encode("utf-8", errors="replace")).hexdigest()
    doc_name = f"{pmcid}_fulltext.xml"
    doc_path = f"epmc://{pmcid}/fullTextXML"
    pidx = LocalPassageIndex(passages_db_path)
    inserted = 0
    with pidx._connect() as conn:
        for sec_num, sec in enumerate(sections, 1):
            sec_title = sec["section_title"]
            prefix = f"[{pmcid} | {sec_title}] " + (f"{title} — " if title and sec_num == 1 else "")
            chunks = _chunk_text(sec["text"], max_chars=max_chars)
            for chunk_idx, ch in enumerate(chunks, 1):
                full_text = f"{prefix}{ch['text']}"
                pid = hashlib.sha256(
                    f"{xml_sha}:{sec_num}:{chunk_idx}".encode("utf-8")
                ).hexdigest()[:24]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO passages
                    (passage_id, doc_path, doc_name, doc_sha256, page, chunk_index, char_start, char_end, text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (pid, doc_path, doc_name, xml_sha, sec_num, chunk_idx,
                     ch["char_start"], ch["char_end"], full_text),
                )
                conn.execute("DELETE FROM passages_fts WHERE passage_id = ?", (pid,))
                conn.execute(
                    "INSERT INTO passages_fts (passage_id, doc_name, text) VALUES (?, ?, ?)",
                    (pid, doc_name, full_text),
                )
                inserted += 1
    return inserted


def harvest_epmc_fulltext(
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    cache_dir: str | Path = ".cache/layer_b_epmc_xml",
    limit: int = 20,
    delay_seconds: float = 0.5,
    skip_existing: bool = True,
    max_retries: int = 2,
    pmcids: Optional[List[str]] = None,
    http_get_text: Optional[Callable[[str, Dict[str, str]], str]] = None,
) -> Dict[str, Any]:
    """Harvest open-access Europe PMC JATS XML full-text sections into ``passages.sqlite``."""
    cdir = Path(cache_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    pidx = LocalPassageIndex(passages_db_path)
    already_indexed: set[str] = set()
    if skip_existing:
        with pidx._connect() as conn:
            for (doc_name,) in conn.execute("SELECT DISTINCT doc_name FROM passages WHERE doc_name LIKE 'PMC%_fulltext.xml'").fetchall():
                already_indexed.add(str(doc_name).split("_fulltext.xml", 1)[0])

    if pmcids:
        targets = [{"pmcid": p.strip(), "title": ""} for p in pmcids if p.strip()]
    else:
        targets = find_pmc_candidates(db_path=db_path, limit=max(int(limit) * 2, int(limit) + len(already_indexed)))
    if skip_existing and already_indexed:
        targets = [t for t in targets if t["pmcid"] not in already_indexed]
    targets = targets[: max(int(limit), 1)]

    harvested_articles = 0
    total_passages = 0
    sources_used: Dict[str, int] = {}
    errors: List[Dict[str, str]] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml, text/html"}

    for idx_i, item in enumerate(targets):
        pmcid = item["pmcid"]
        cpath = cdir / f"{pmcid}.xml"
        xml_text: Optional[str] = None
        if cpath.exists():
            xml_text = cpath.read_text(encoding="utf-8", errors="replace")
            sources_used["cache"] = sources_used.get("cache", 0) + 1
        else:
            xml_text, src_used, last_err = fetch_oa_fulltext_with_fallback(
                pmcid,
                arxiv_id=item.get("arxiv", ""),
                headers=headers,
                max_retries=max_retries,
                http_get_text=http_get_text,
            )
            if xml_text:
                cpath.write_text(xml_text, encoding="utf-8")
                sources_used[src_used] = sources_used.get(src_used, 0) + 1
            else:
                errors.append({"pmcid": pmcid, "error": last_err or "empty"})
                continue
            if delay_seconds > 0 and idx_i + 1 < len(targets) and http_get_text is None:
                time.sleep(delay_seconds)

        if xml_text:
            added = ingest_jats_xml_to_passages(
                pmcid,
                xml_text,
                passages_db_path=passages_db_path,
                title=item.get("title", ""),
            )
            if added > 0:
                harvested_articles += 1
                total_passages += added

    pidx = LocalPassageIndex(passages_db_path)
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "candidates": len(targets),
        "harvested_articles": harvested_articles,
        "passages_added": total_passages,
        "sources_used": sources_used,
        "errors": errors[:10],
        "stats": pidx.stats(),
    }

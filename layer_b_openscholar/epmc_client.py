# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ungated Europe PMC / PubMed REST API client with disk caching."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
USER_AGENT = "ResearchIntelligence-LayerB/0.2"


class EuropePMCClient:
    """Free, ungated client for Europe PMC (PubMed + PMC Open Access epidemiology literature)."""

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        http_get: Optional[Callable[[str, Dict[str, Any], Dict[str, str]], Dict[str, Any]]] = None,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._http_get = http_get

    def _cache_path(self, params: Dict[str, Any]) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(
            json.dumps({"source": "epmc", "params": params}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"epmc_{key}.json"

    @staticmethod
    def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
        author_str = (raw.get("authorString") or "").strip().rstrip(".")
        authors = [a.strip() for a in author_str.split(",") if a.strip()] if author_str else []
        doi = (raw.get("doi") or "").strip()
        pmid = str(raw.get("pmid") or "").strip()
        pmcid = str(raw.get("pmcid") or "").strip()
        pid = pmcid or (f"PMID:{pmid}" if pmid else str(raw.get("id") or ""))
        yr_raw = raw.get("pubYear")
        year = int(yr_raw) if yr_raw and str(yr_raw).isdigit() else None
        oa_url = f"https://europepmc.org/articles/{pmcid}?pdf=render" if pmcid and raw.get("isOpenAccess") == "Y" else ""
        return {
            "paperId": pid,
            "title": (raw.get("title") or "").strip().rstrip("."),
            "abstract": (raw.get("abstractText") or "").strip(),
            "year": year,
            "authors": authors,
            "venue": (raw.get("journalTitle") or "").strip(),
            "citationCount": int(raw.get("citedByCount") or 0),
            "doi": doi,
            "arxiv": "",
            "url": f"https://doi.org/{doi}" if doi else (f"https://europepmc.org/article/MED/{pmid}" if pmid else ""),
            "openAccessPdf": oa_url,
        }

    def search_papers(self, query: str, limit: int = 25, year: Optional[str] = None) -> List[Dict[str, Any]]:
        q = f"({query}) AND (PUB_YEAR:[{year.replace('-', ' TO ')}])" if year and "-" in year else query
        params: Dict[str, Any] = {
            "query": q,
            "format": "json",
            "resultType": "core",
            "pageSize": min(max(int(limit), 1), 100),
        }
        cpath = self._cache_path(params)
        if cpath is not None and cpath.exists():
            data = json.loads(cpath.read_text(encoding="utf-8"))
        else:
            url = f"{EPMC_BASE}/search"
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            if self._http_get is not None:
                data = self._http_get(url, params, headers)
            else:
                import requests

                resp = requests.get(url, params=params, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            if cpath is not None:
                cpath.parent.mkdir(parents=True, exist_ok=True)
                cpath.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        rows = (data.get("resultList") or {}).get("result") or []
        return [self.normalize_record(r) for r in rows if r.get("title")]


def merge_and_deduplicate(*paper_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate papers across OpenAlex / Europe PMC / S2 by normalized DOI, else normalized title."""
    seen: set[str] = set()
    merged: List[Dict[str, Any]] = []
    for plist in paper_lists:
        for p in plist:
            doi_key = f"doi:{p['doi'].lower().strip()}" if p.get("doi") else ""
            title_key = f"title:{' '.join((p.get('title') or '').lower().split())}"
            key = doi_key or title_key
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(p)
    return merged

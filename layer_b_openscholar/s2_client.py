# SPDX-License-Identifier: AGPL-3.0-or-later
"""Semantic Scholar Graph API client with disk caching and polite backoff."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

S2_BASE = "https://api.semanticscholar.org/graph/v1"
OPENALEX_BASE = "https://api.openalex.org"
DEFAULT_FIELDS = "paperId,title,abstract,year,authors,venue,citationCount,externalIds,url,openAccessPdf"
USER_AGENT = "ResearchIntelligence-LayerB/0.1"


def _reconstruct_openalex_abstract(inv: Optional[Dict[str, List[int]]]) -> str:
    if not isinstance(inv, dict) or not inv:
        return ""
    pairs = [(pos, word) for word, positions in inv.items() for pos in positions]
    pairs.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pairs)


class OpenAlexClient:
    """Free, no-key-required fallback client for the OpenAlex Works API with polite pool support."""

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        http_get: Optional[Callable[[str, Dict[str, Any], Dict[str, str]], Dict[str, Any]]] = None,
        mailto: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._http_get = http_get
        self.mailto = mailto if mailto is not None else os.environ.get("OPENALEX_MAILTO", "").strip()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY", "").strip()
        self.max_retries = max(int(max_retries), 1)

    def _headers(self) -> Dict[str, str]:
        ua = f"{USER_AGENT} (mailto:{self.mailto})" if self.mailto else USER_AGENT
        return {"User-Agent": ua, "Accept": "application/json"}

    def _cache_path(self, params: Dict[str, Any]) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        cache_params = {k: v for k, v in params.items() if k not in ("api_key", "mailto")}
        key = hashlib.sha256(
            json.dumps({"source": "openalex", "params": cache_params}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"oa_{key}.json"

    @staticmethod
    def normalize_work(raw: Dict[str, Any]) -> Dict[str, Any]:
        doi = (raw.get("doi") or "").replace("https://doi.org/", "").strip()
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in (raw.get("authorships") or [])
            if (a.get("author") or {}).get("display_name")
        ]
        loc = raw.get("primary_location") or {}
        src = loc.get("source") or {}
        oa = raw.get("open_access") or {}
        return {
            "paperId": (raw.get("id") or "").rsplit("/", 1)[-1],
            "title": (raw.get("title") or "").strip(),
            "abstract": _reconstruct_openalex_abstract(raw.get("abstract_inverted_index")),
            "year": raw.get("publication_year"),
            "authors": authors,
            "venue": (src.get("display_name") or "").strip(),
            "citationCount": int(raw.get("cited_by_count") or 0),
            "doi": doi,
            "arxiv": "",
            "url": raw.get("id") or (f"https://doi.org/{doi}" if doi else ""),
            "openAccessPdf": oa.get("oa_url") or "",
        }

    def search_papers(self, query: str, limit: int = 25, year: Optional[str] = None, page: int = 1) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"search": query, "per-page": min(max(int(limit), 1), 100)}
        if int(page) > 1:
            params["page"] = int(page)
        if year:
            params["filter"] = f"publication_year:{year}"
        if self.mailto:
            params["mailto"] = self.mailto
        if self.api_key:
            params["api_key"] = self.api_key
        cpath = self._cache_path(params)
        if cpath is not None and cpath.exists():
            data = json.loads(cpath.read_text(encoding="utf-8"))
        else:
            url = f"{OPENALEX_BASE}/works"
            headers = self._headers()
            if self._http_get is not None:
                data = self._http_get(url, params, headers)
            else:
                import requests

                data = None
                for attempt in range(self.max_retries):
                    resp = requests.get(url, params=params, headers=headers, timeout=30)
                    if resp.status_code in (429, 500, 502, 503, 504) and attempt + 1 < self.max_retries:
                        retry_after = resp.headers.get("Retry-After")
                        try:
                            sleep_s = float(retry_after) if retry_after else 2.0 * (2 ** attempt)
                        except ValueError:
                            sleep_s = 2.0 * (2 ** attempt)
                        time.sleep(min(max(sleep_s, 0.5), 30.0))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
                if data is None:
                    raise RuntimeError(f"OpenAlex request failed after {self.max_retries} retries: {url}")
            if cpath is not None:
                cpath.parent.mkdir(parents=True, exist_ok=True)
                cpath.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return [self.normalize_work(w) for w in (data.get("results") or []) if w.get("title")]


class SemanticScholarClient:
    """Thin, cache-backed client for the Semantic Scholar Graph API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[str | Path] = None,
        http_get: Optional[Callable[[str, Dict[str, Any], Dict[str, str]], Dict[str, Any]]] = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("S2_API_KEY", "")
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._http_get = http_get
        self.max_retries = max_retries

    def _headers(self) -> Dict[str, str]:
        h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    def _cache_path(self, endpoint: str, params: Dict[str, Any]) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(
            json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cpath = self._cache_path(endpoint, params)
        if cpath is not None and cpath.exists():
            return json.loads(cpath.read_text(encoding="utf-8"))

        url = f"{S2_BASE}/{endpoint.lstrip('/')}"
        headers = self._headers()
        if self._http_get is not None:
            payload = self._http_get(url, params, headers)
        else:
            import requests

            payload = None
            for attempt in range(self.max_retries):
                resp = requests.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code == 429 and attempt + 1 < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                payload = resp.json()
                break
            if payload is None:
                raise RuntimeError(f"Semantic Scholar request failed after {self.max_retries} retries: {url}")

        if cpath is not None:
            cpath.parent.mkdir(parents=True, exist_ok=True)
            cpath.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    @staticmethod
    def normalize_paper(raw: Dict[str, Any]) -> Dict[str, Any]:
        ext = raw.get("externalIds") or {}
        authors = [a.get("name", "") for a in (raw.get("authors") or []) if a.get("name")]
        return {
            "paperId": raw.get("paperId") or "",
            "title": (raw.get("title") or "").strip(),
            "abstract": (raw.get("abstract") or "").strip(),
            "year": raw.get("year"),
            "authors": authors,
            "venue": (raw.get("venue") or "").strip(),
            "citationCount": int(raw.get("citationCount") or 0),
            "doi": ext.get("DOI") or "",
            "arxiv": ext.get("ArXiv") or "",
            "url": raw.get("url") or "",
            "openAccessPdf": (raw.get("openAccessPdf") or {}).get("url") or "",
        }

    def search_papers(self, query: str, limit: int = 25, year: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query, "limit": min(max(int(limit), 1), 100), "fields": DEFAULT_FIELDS}
        if year:
            params["year"] = year
        data = self._get("paper/search", params)
        return [self.normalize_paper(p) for p in (data.get("data") or []) if p.get("title")]

    def get_references(self, paper_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        params = {"limit": min(max(int(limit), 1), 100), "fields": DEFAULT_FIELDS}
        data = self._get(f"paper/{paper_id}/references", params)
        out = []
        for row in data.get("data") or []:
            cited = row.get("citedPaper") or {}
            if cited.get("title"):
                out.append(self.normalize_paper(cited))
        return out

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 201 tests: 3-tier OA full-text harvester fallback (EPMC XML -> PMC OAI-PMH -> arXiv HTML)."""
from __future__ import annotations

from pathlib import Path

from layer_b_openscholar.fulltext_harvester import fetch_oa_fulltext_with_fallback, harvest_epmc_fulltext
from layer_b_openscholar.local_index import LocalLiteratureIndex

_OAI_XML = "<OAI-PMH><article><body><sec><title>Methods</title><p>Multi-component BYM2 spatial smoothing across all 50 states and island counties.</p></sec></body></article></OAI-PMH>"


def test_3tier_oa_fallback_falls_back_to_pmc_oai_pmh(tmp_path: Path):
    calls = []

    def fake_get(url, headers):
        calls.append(url)
        if "ebi.ac.uk" in url:
            raise RuntimeError("HTTP 500")
        return _OAI_XML

    txt, src, err = fetch_oa_fulltext_with_fallback("PMC7654321", max_retries=1, http_get_text=fake_get)
    assert txt is not None and src == "pmc_oai_pmh" and err == ""
    assert len(calls) == 2 and "oai:pubmedcentral.nih.gov:7654321" in calls[1]

    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "PMC7654321", "title": "National BYM2", "abstract": "Test", "year": 2025}
    ])
    rep = harvest_epmc_fulltext(
        db_path=lit_db,
        passages_db_path=pas_db,
        cache_dir=tmp_path / "xml",
        limit=5,
        delay_seconds=0.0,
        max_retries=1,
        http_get_text=fake_get,
    )
    assert rep["ok"] is True
    assert rep["harvested_articles"] == 1
    assert rep["sources_used"].get("pmc_oai_pmh") == 1

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 161 tests: 36-domain taxonomy & OpenAlex 1-hop citation-graph expander."""
from pathlib import Path

from layer_b_openscholar.citation_expander import expand_seed_citations, top_openalex_seeds
from layer_b_openscholar.corpus_miner import DOMAIN_TOPICS


def test_r161_36_domains_and_citation_expander(tmp_path: Path):
    assert len(DOMAIN_TOPICS) == 36
    assert any(t["id"] == "D36" for t in DOMAIN_TOPICS)

    db = tmp_path / "idx.sqlite"

    def fake_get(url, params, headers):
        assert params["filter"] == "cites:W12345"
        return {
            "results": [
                {
                    "id": "https://openalex.org/W99901",
                    "title": "Follow-up spatial BYM2 stroke analysis",
                    "publication_year": 2025,
                    "doi": "https://doi.org/10.1000/cite1",
                    "cited_by_count": 7,
                    "abstract_inverted_index": {"BYM2": [0], "stroke": [1]},
                }
            ]
        }

    rep = expand_seed_citations("W12345", db_path=db, limit=10, http_get=fake_get)
    assert rep["ok"] is True
    assert rep["added"] == 1
    seeds = top_openalex_seeds(db_path=db, limit=5)
    assert len(seeds) == 1 and seeds[0]["paperId"] == "W99901"

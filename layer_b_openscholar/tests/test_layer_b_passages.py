# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 133 tests: page/section-level local passage indexer and MCP search_passages."""
from layer_b_openscholar.mcp_server import search_passages
from layer_b_openscholar.pdf_indexer import LocalPassageIndex


def test_local_passage_indexer_and_mcp_search(tmp_path):
    note = tmp_path / "epidemiology_notes.md"
    note.write_text(
        "Section 1: Appalachian Ohio and Pennsylvania counties show elevated cancer mortality.\n\n"
        "Section 2: Fay-Herriot empirical Bayes shrinkage borrows strength across small areas.",
        encoding="utf-8",
    )
    db = tmp_path / "passages.sqlite"
    idx = LocalPassageIndex(db)
    n = idx.index_file(note)
    assert n == 2
    assert idx.stats()["doc_count"] == 1 and idx.stats()["passage_count"] == 2

    res = search_passages("Fay Herriot empirical Bayes shrinkage", db_path=str(db), limit=5)
    assert res["ok"] is True and res["status"] == "exploratory_hypothesis_seed"
    assert res["passage_count"] >= 1
    hit = res["passages"][0]
    assert hit["doc_name"] == "epidemiology_notes.md"
    assert hit["page"] == 1 and len(hit["doc_sha256"]) == 64
    assert "Fay-Herriot" in hit["text"]

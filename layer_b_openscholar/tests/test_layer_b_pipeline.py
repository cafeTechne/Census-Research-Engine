# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 153 tests: Layer B end-to-end offline exploratory pipeline."""
from pathlib import Path

from layer_b_openscholar.handoff_bridge import run_exploratory_pipeline
from layer_b_openscholar.local_index import LocalLiteratureIndex


def test_layer_b_exploratory_pipeline_end_to_end(tmp_path: Path):
    db = tmp_path / "idx.sqlite"
    idx = LocalLiteratureIndex(str(db))
    idx.ingest_papers([
        {
            "paperId": "W1",
            "title": "County poverty spatial BYM2 mortality disparities",
            "abstract": "BYM2 spatial smoothing of county mortality across rural Appalachia.",
            "year": 2024,
            "doi": "10.1000/bym2-appalachia",
        },
        {
            "paperId": "W2",
            "title": "Small area estimation of county poverty using Fay-Herriot",
            "abstract": "Temporal Rao-Yu small area estimation improves county precision.",
            "year": 2023,
            "doi": "10.1000/fh-sae",
        },
    ], source="test")

    out_dir = tmp_path / "pipe_out"
    rep = run_exploratory_pipeline(
        "county poverty mortality",
        out_dir,
        geography="county",
        method_family="spatial_bym2",
        db_path=str(db),
        backend="bm25",
    )
    assert rep["ok"] is True
    assert rep["status"] == "exploratory_hypothesis_seed"
    assert rep["paper_count"] >= 1
    for key in ("dossier_json", "references_bib", "gap_matrix", "manifest_seed_json", "manifest_seed_md", "bridge_report"):
        assert Path(rep["paths"][key]).exists(), f"Missing output {key}"

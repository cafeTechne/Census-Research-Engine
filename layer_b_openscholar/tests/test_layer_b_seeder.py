# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 143 tests: Layer B Pre-Registration Manifest Seed Drafter & strict isolation."""
import json
from pathlib import Path

from layer_b_openscholar.manifest_seeder import draft_manifest_seed, write_manifest_seed
from layer_b_openscholar.mcp_server import draft_manifest_seed_tool, list_tool_names


def test_draft_manifest_seed_is_deterministic_and_exploratory(tmp_path: Path):
    papers = [
        {"paperId": "p1", "title": "County poverty spatial BYM2", "year": 2024, "doi": "10.1000/a"},
        {"paperId": "p2", "title": "Rural mortality disparities", "year": 2023, "doi": "10.1000/b"},
    ]
    s1 = draft_manifest_seed("County mortality disparities", papers, geography="county", method_family="spatial_bym2")
    s2 = draft_manifest_seed("County mortality disparities", papers, geography="county", method_family="spatial_bym2")
    assert s1["seed_sha256"] == s2["seed_sha256"]
    assert s1["status"] == "exploratory_hypothesis_seed"
    assert s1["requires_human_preregistration"] is True
    assert s1["proposed_design"]["candidate_layer_a_family"] == "disease_map_bym2"
    assert s1["provenance"]["dois"] == ["10.1000/a", "10.1000/b"]

    paths = write_manifest_seed(s1, tmp_path / "seed_out")
    assert Path(paths["json"]).exists() and Path(paths["markdown"]).exists()
    loaded = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert loaded["seed_sha256"] == s1["seed_sha256"]


def test_mcp_exposes_seven_tools_including_draft_manifest_seed(tmp_path: Path):
    names = list_tool_names()
    assert len(names) >= 7
    assert "draft_manifest_seed" in names
    res = draft_manifest_seed_tool(
        topic="Medicaid expansion RDD",
        geography="puma",
        method_family="rdd",
        db_path=str(tmp_path / "empty.sqlite"),
    )
    assert res["status"] == "exploratory_hypothesis_seed"
    assert res["requires_human_preregistration"] is True

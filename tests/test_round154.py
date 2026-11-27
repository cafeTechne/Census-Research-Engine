# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 154 tests: mcp_capabilities, recipe keyword search & Layer B 9-tool MCP."""
from pathlib import Path

import mcp_server as srv
from census import recipes
from layer_b_openscholar.mcp_server import list_tool_names, run_exploratory_pipeline


def test_r154_mcp_capabilities_and_recipe_query():
    caps = srv.mcp_capabilities()
    assert caps["success"] is True
    assert caps["recipe_count"] >= 32
    assert caps["manifest_method_count"] == 28
    assert "publication" in caps["profiles"] and "epidemiology" in caps["profiles"]

    filtered = recipes.get_recipe(query="layer b")
    assert filtered["success"] is True
    names = {r["name"] for r in filtered["recipes"]}
    assert "literature_to_preregistration" in names
    assert "layer_b_offline_corpus" in names


def test_r154_layer_b_mcp_nine_tools_including_pipeline(tmp_path: Path):
    names = list_tool_names()
    assert len(names) >= 9
    assert "run_exploratory_pipeline" in names
    res = run_exploratory_pipeline(
        "poverty",
        str(tmp_path / "out"),
        db_path=str(tmp_path / "empty.sqlite"),
        backend="bm25",
    )
    assert res["ok"] is True
    assert res["status"] == "exploratory_hypothesis_seed"

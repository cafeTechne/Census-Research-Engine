# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 147 tests: verify_bundle & list_manifest_methods MCP tools, new profiles & Layer B 8-tool MCP."""
from pathlib import Path

import mcp_server as srv
from census import mcp_profiles
from layer_b_openscholar.manifest_seeder import draft_manifest_seed, write_manifest_seed
from layer_b_openscholar.mcp_server import list_tool_names, validate_handoff_seed


def test_r147_layer_a_new_mcp_tools_and_profiles():
    registered = {t.name for t in srv.mcp._tool_manager.list_tools()}
    assert "verify_bundle" in registered
    assert "list_manifest_methods" in registered

    methods_res = srv.list_manifest_methods()
    assert methods_res["success"] is True
    assert methods_res["count"] == 28

    for prof in ("publication", "epidemiology"):
        assert prof in mcp_profiles.PROFILES
        sub = srv.server_for_profile(prof)
        names = {t.name for t in sub._tool_manager.list_tools()}
        assert "verify_bundle" in names
        assert "list_manifest_methods" in names
        assert "get_recipe" in names


def test_r147_layer_b_mcp_exposes_eight_tools_including_validate_handoff_seed(tmp_path: Path):
    names = list_tool_names()
    assert len(names) >= 8
    assert "validate_handoff_seed" in names

    seed = draft_manifest_seed("Rural diabetes disparities", [{"title": "T", "year": 2024, "doi": "10.1/x"}])
    paths = write_manifest_seed(seed, tmp_path / "seed")
    res = validate_handoff_seed(paths["json"])
    assert res["ok"] is True
    assert res["status"] == "exploratory_hypothesis_seed"

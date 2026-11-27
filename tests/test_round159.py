# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 159 tests: live async FastMCP protocol integration tests (Layer A + Layer B) & synthesis report."""
import asyncio
import json
from pathlib import Path

import mcp_server as layer_a_srv
from layer_b_openscholar import mcp_server as layer_b_srv

ROOT = Path(__file__).resolve().parents[1]


def _extract_json(call_result):
    # FastMCP call_tool returns a list of TextContent or (content_list, structured_dict)
    if isinstance(call_result, tuple):
        if isinstance(call_result[1], dict):
            return call_result[1].get("result", call_result[1])
        call_result = call_result[0]
    if isinstance(call_result, list) and call_result:
        text = getattr(call_result[0], "text", None) or str(call_result[0])
        return json.loads(text)
    return call_result


def test_r159_layer_a_fastmcp_async_protocol():
    pub = layer_a_srv.server_for_profile("publication")
    tools = asyncio.run(pub.list_tools())
    names = {t.name for t in tools}
    assert {"mcp_capabilities", "list_manifest_methods", "verify_bundle", "get_recipe"} <= names

    caps = _extract_json(asyncio.run(pub.call_tool("mcp_capabilities", {})))
    assert caps["success"] is True
    assert caps["recipe_count"] >= 32
    assert caps["manifest_method_count"] == 28

    rec = _extract_json(asyncio.run(pub.call_tool("get_recipe", {"query": "layer b"})))
    assert rec["success"] is True
    assert len(rec["recipes"]) >= 2


def test_r159_layer_b_fastmcp_async_protocol(tmp_path: Path):
    srv = layer_b_srv.create_server()
    tools = asyncio.run(srv.list_tools())
    names = {t.name for t in tools}
    assert len(names) >= 9
    assert {"local_search_literature", "build_gap_matrix", "draft_manifest_seed", "validate_handoff_seed", "run_exploratory_pipeline"} <= names

    stats = _extract_json(asyncio.run(srv.call_tool("index_stats", {"db_path": str(tmp_path / "empty.sqlite")})))
    assert stats["ok"] is True
    assert stats["status"] == "exploratory_hypothesis_seed"
    assert stats["paper_count"] == 0


def test_r159_cross_study_synthesis_exists():
    syn = ROOT / "docs/studies/r120_r156_synthesis.md"
    assert syn.exists()
    txt = syn.read_text(encoding="utf-8")
    assert "r156_layer_b_to_layer_a_study.md" in txt
    assert "Samsung 850 EVO SSD" in txt

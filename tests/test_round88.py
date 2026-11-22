# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 88: method attribution (source registry, method_sources on tool results, references in bundles)."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from census import references as R
from census.manifest.schema import REFERENCES as MANIFEST_TEXT

ROOT = Path(__file__).resolve().parents[1]


def _tools():
    import mcp_server
    return {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}


def test_every_registered_tool_has_sources_and_every_id_exists():
    names = _tools()
    assert names == set(R.TOOL_SOURCES), (names ^ set(R.TOOL_SOURCES))
    for tool in R.TOOL_SOURCES:
        for sid, role in R.tool_entries(tool):
            assert role in R.ROLES, (tool, role)
            if sid.startswith("audit:"):
                assert (ROOT/sid[len("audit:"):]).is_file(), (tool, sid)
            else:
                assert sid in R.SOURCES, (tool, sid)


def test_manifest_citation_text_unchanged_and_all_sources_format():
    for k, text in MANIFEST_TEXT.items():
        assert R.citation_text(k) == text
    for sid in list(R.SOURCES):
        assert R.citation_text(sid)
        bib = R.bibtex(sid)
        assert bib.startswith("@") and bib.endswith("}") and bib.count("{") == bib.count("}")
        assert " & " not in bib  # bare ampersands break LaTeX


def test_guidance_texts_registered_and_attributed():
    for sid in ("bovbjerg2020", "hernan_robins2020", "walker2023"):
        assert R.SOURCES[sid]["kind"] == "book"
    ids = {sid for sid, role in R.tool_entries("stratified_analysis") if role == "guidance"}
    assert {"bovbjerg2020", "hernan_robins2020"} <= ids
    assert ("walker2023", "guidance") in R.tool_entries("spatial_autocorrelation")


def test_bibtex_authors_and_escaping():
    bib = R.bibtex("rbg1986")
    assert "author = {Robins, J. and Breslow, N. and Greenland, S.}" in bib
    assert "pages = {311--323}" in bib
    assert r"Chapman \& Hall/CRC" in R.bibtex("hernan_robins2020")
    assert "author = {{U.S. Census Bureau}}" in R.bibtex("tiger")


def test_unverified_entries_are_flagged():
    unverified = [s for s, v in R.SOURCES.items() if v.get("verified") is False]
    assert unverified
    for sid in unverified:
        assert "[details to verify]" in R.citation_text(sid)


def test_module_reference_lists_are_included_verbatim():
    from census import sae
    texts = [R.citation_text(sid) for sid, _ in R.tool_entries("small_area_estimates") if not sid.startswith("audit:")]
    for ref in sae.REFERENCES:
        assert ref in texts


def test_attach_copies_and_skips_failures_and_discovery_tools():
    res = {"success": True, "summary": "x"}
    out = R.attach("stratified_analysis", res)
    assert "method_sources" not in res and out["method_sources"]
    assert {s["role"] for s in out["method_sources"]} >= {"method", "guidance", "validation"}
    fail = {"success": False, "error": "e"}
    assert R.attach("stratified_analysis", fail) is fail
    assert "method_sources" not in R.attach("list_states", {"success": True})
    assert R.attach("unknown_tool", {"success": True}) == {"success": True}


def test_mcp_boundary_adds_sources():
    import mcp_server
    tool = {t.name: t for t in mcp_server.mcp._tool_manager.list_tools()}["bias_analysis"]
    out = tool.fn(kind="e_value", estimate=1.8, lower=1.3, upper=2.4)
    assert out["success"] and any(s.get("id") == "vanderweele_ding2017" for s in out["method_sources"])
    # the module-level function stays unwrapped
    assert "method_sources" not in mcp_server.bias_analysis(kind="e_value", estimate=1.8, lower=1.3, upper=2.4)


def _cli(*args, cwd=ROOT):
    env = dict(os.environ, CENSUS_HEALTH_OFFLINE="1")
    return subprocess.run([sys.executable, "-m", "census", *args], cwd=cwd, env=env, capture_output=True, text=True)


def test_cli_cite_and_tool_and_bundle(tmp_path):
    r = _cli("cite", "--tool", "bias_analysis")
    assert r.returncode == 0 and "VanderWeele" in r.stdout and "Guidance texts" in r.stdout and "Zenodo" in r.stdout
    r = _cli("cite", "hernan_robins2020", "--format", "bibtex")
    assert r.returncode == 0 and r.stdout.startswith("@book{hernan_robins2020")
    assert _cli("cite", "no_such_id").returncode != 0
    saved = tmp_path/"e.json"
    r = _cli("tool", "bias_analysis", "--arg", "kind=e_value", "--arg", "estimate=1.8", "--arg", "lower=1.3",
             "--arg", "upper=2.4", "--save", str(saved), "--json")
    assert json.loads(r.stdout)["method_sources"]
    r = _cli("tool", "make_results_bundle", "--arg", f"output_dir={tmp_path/'b'}",
             "--arg", "results=" + json.dumps({"evalue": str(saved)}),
             "--arg", "design=none", "--json")
    assert json.loads(r.stdout)["success"], r.stdout
    b = tmp_path/"b"
    methods = (b/"methods.md").read_text()
    assert "## Sources" in methods and "VanderWeele" in methods and "bias_analysis_validation.md" in methods
    assert "@article{vanderweele_ding2017" in (b/"references.bib").read_text()
    files = json.loads((b/"bundle.json").read_text())["files"]
    assert {"references.md", "references.bib"} <= set(files)


def test_bundle_without_sources_says_so(tmp_path):
    from census.workflows_inference import make_results_bundle, save_json
    p = save_json({"success": True, "summary": "old result"}, str(tmp_path/"old.json"))
    out = make_results_bundle(str(tmp_path/"b"), {"old": p}, design="none")
    assert out["success"]
    assert "No saved result recorded method_sources" in (tmp_path/"b"/"methods.md").read_text()


def test_results_bundle_rejects_other_reference_names(tmp_path):
    from census.report_tables import results_bundle
    with pytest.raises(ValueError):
        results_bundle(tmp_path/"b", references={"../x.md": "x"})


def test_citation_cff_lists_guidance_texts():
    text = (ROOT/"CITATION.cff").read_text()
    for title in ("Foundations of Epidemiology", "Causal Inference: What If", "Analyzing US Census Data"):
        assert title in text

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regressions for the Round 18 code-review findings."""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from census import errors, manifest, tables, workflows, workflows_inference
from census.data_integrity import BundledDataIntegrityError
from census.metadata import MetadataIntegrityError

EXAMPLE = Path(__file__).parents[1] / "examples/manifests/income_population_tracts.json"


def _corrupt(*_a, **_k):
    raise MetadataIntegrityError("bundled metadata failed verification")


def test_integrity_errors_are_not_value_errors():
    assert not issubclass(BundledDataIntegrityError, ValueError)
    assert issubclass(MetadataIntegrityError, BundledDataIntegrityError)


def test_ordinary_input_handlers_do_not_misreport_corruption(monkeypatch):
    # median_from_distribution catches ValueError as bad input around distribution_brackets.
    monkeypatch.setattr(workflows, "distribution_brackets", _corrupt)
    res = workflows.median_from_distribution("B19001", 2022, counts=[1, 2, 3])
    assert res["error_code"] == errors.BUNDLED_DATA_INTEGRITY


def test_every_mcp_tool_translates_integrity_failures(monkeypatch):
    import mcp_server

    # fit_model has no _guided wrapper of its own; the registration boundary must translate.
    monkeypatch.setattr(workflows_inference, "_load_frame", _corrupt)
    content = asyncio.run(mcp_server.mcp.call_tool("fit_model", {"input_path": "x.csv", "formula": "y ~ x"}))
    blocks = content[0] if isinstance(content, tuple) else content
    text = "".join(getattr(b, "text", "") for b in blocks)
    assert json.loads(text)["error_code"] == errors.BUNDLED_DATA_INTEGRITY


def _manifest_with_ids(*ids):
    m = json.loads(EXAMPLE.read_text())
    base = m["analyses"][0]
    m["analyses"] = [dict(copy.deepcopy(base), id=i) for i in ids]
    m.pop("hypotheses", None)
    return m


@pytest.mark.parametrize("ids", [("m:1",), ("a/b",), ("model 1.",), ("CON",), ("M1", "m1")])
def test_unusable_analysis_ids_fail_validation_up_front(ids):
    errs = manifest.validate_manifest(_manifest_with_ids(*ids), resolve=False)
    assert any("id" in e and ("filename" in e or "case-insensitive" in e) for e in errs), errs


def test_portable_analysis_ids_still_validate():
    errs = manifest.validate_manifest(_manifest_with_ids("m1", "model-2.b"), resolve=False)
    assert not [e for e in errs if "filename" in e or "case-insensitive" in e]


def test_occupied_output_dir_is_not_called_an_invalid_manifest(tmp_path, monkeypatch):
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle" / "old.txt").write_text("keep")
    monkeypatch.setattr(manifest, "validate_manifest", lambda *a, **k: [])
    res = workflows_inference.run_manifest(str(EXAMPLE), output_dir=str(tmp_path))
    assert res["error_code"] == errors.INVALID_INPUT
    assert "Manifest invalid" not in res["error"] and "output_dir" in res["next_step"]
    assert (tmp_path / "bundle" / "old.txt").read_text() == "keep"


def test_clear_cache_keeps_snapshots_callers_hold(monkeypatch):
    held = tables.load_variable_metadata()
    before = dict(held)
    tables.clear_cache()
    assert held == before

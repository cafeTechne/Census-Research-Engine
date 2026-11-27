# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 124 tests: verify_bundle() SHA-256/BibTeX/LaTeX audit and Phase 4 verification orchestration eval."""
import importlib.util
import json
from pathlib import Path

from census.manifest import run_manifest
from census.report_tables import verify_bundle
from tests.test_manifest import FakeClient

ROOT = Path(__file__).resolve().parents[1]


def test_verify_bundle_detects_valid_and_tampered_bundles(tmp_path):
    manifest = {
        "schema_version": 1,
        "title": "Round 124 Bundle Integrity Test",
        "authors": ["human:example-researcher"],
        "created": "2026-11-26T00:00:00Z",
        "releases": [2019],
        "geography": {"level": "tract", "state": "36", "codes": ["061"]},
        "variables": [
            {"name": "income", "ref": "2019:B19013_001"},
            {"name": "pop", "ref": "2019:B01003_001"},
        ],
        "missing": "complete_case",
        "confidence_level": 0.90,
        "correction": {"method": "holm", "family": "all"},
        "analyses": [
            {"id": "ag1", "method": "agreement", "first": "income", "second": "pop"},
        ],
        "hypotheses": [
            {"id": "H1", "statement": "Non-zero CCC.", "analysis": "ag1", "statistic": "ccc", "null_value": 0.0},
        ],
    }
    mpath = tmp_path / "m124.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run_manifest(str(mpath), output_dir=str(out_dir), client=FakeClient(), use_cache=False)
    assert res["success"] is True

    bundle_dir = out_dir / "bundle"
    chk = verify_bundle(bundle_dir)
    assert chk["ok"] is True and chk["checked_files"] >= 4 and chk["errors"] == []

    # Tamper with references.bib -> must fail closed
    bib = bundle_dir / "references.bib"
    bib.write_text(bib.read_text(encoding="utf-8") + "\n% tampered\n", encoding="utf-8")
    chk_bad = verify_bundle(bundle_dir)
    assert chk_bad["ok"] is False and any("sha256 mismatch" in e for e in chk_bad["errors"])


def test_phase4_verification_orchestration_eval_passes():
    spec = importlib.util.spec_from_file_location("v_eval", ROOT / "scripts/verification_orchestration_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rep = mod.run_eval()
    assert rep["ok"] is True
    assert rep["cases_passed"] == 6
    assert rep["binding_attacks_blocked"] == 2

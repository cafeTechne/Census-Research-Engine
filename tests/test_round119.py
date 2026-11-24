# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 119 tests: citation integrity, modern manifest templates, and offline end-to-end run_manifest integration."""
import json
from pathlib import Path

import numpy as np

from census.manifest import load_manifest, run_manifest, validate_manifest
from census.manifest.methods import METHODS
from census.references import SOURCES
from tests.test_manifest import FakeClient

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "examples/manifests/templates"


def test_all_manifest_citation_keys_exist_in_sources():
    missing = sorted({k for spec in METHODS.values() if spec.text for k in spec.text[1] if k not in SOURCES})
    assert missing == [], f"Unresolved manifest citation keys: {missing}"


def test_modern_manifest_templates_validate():
    templates = sorted(TEMPLATE_DIR.glob("*.json"))
    assert len(templates) == 4
    for path in templates:
        m = load_manifest(str(path))
        errs = validate_manifest(m, resolve=False)
        assert errs == [], f"{path.name} failed validation: {errs}"


def test_end_to_end_run_manifest_for_agreement_and_bias_analysis(tmp_path):
    """Full offline run_manifest pipeline using SyntheticClient: manifest JSON -> run.json, methods.md, references.bib."""
    manifest = {
        "schema_version": 1,
        "title": "E2E Round 119 Agreement & Bias Analysis",
        "authors": ["human:example-researcher"],
        "created": "2026-11-24T00:00:00Z",
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
            {"id": "ba1", "method": "bias_analysis", "kind": "e_value", "args": {"estimate": 2.0, "lower": 1.4, "upper": 2.8}},
        ],
        "hypotheses": [
            {"id": "H1", "statement": "Income and population exhibit non-zero CCC.",
             "analysis": "ag1", "statistic": "ccc", "null_value": 0.0, "direction": "two-sided"},
            {"id": "H2", "statement": "E-value for RR=2.0 exceeds 3.",
             "analysis": "ba1", "statistic": "e_value", "direction": "two-sided"},
        ],
    }
    mpath = tmp_path / "m119.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")

    out_dir = tmp_path / "run_out"
    res = run_manifest(str(mpath), output_dir=str(out_dir), client=FakeClient(), use_cache=False)

    bundle = out_dir / "bundle"
    assert res["success"] is True
    assert res["analysis_status"] == "confirmatory"
    assert (bundle / "bundle.json").exists()
    assert (bundle / "methods.md").exists()
    methods_md = (bundle / "methods.md").read_text(encoding="utf-8")
    assert "Lin" in methods_md and "VanderWeele" in methods_md
    hyps = res["hypotheses"].set_index("id")
    assert hyps.loc["H1", "status"] == "tested" and np.isfinite(hyps.loc["H1", "estimate"])
    assert float(hyps.loc["H2", "estimate"]) > 3.0

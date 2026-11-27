# SPDX-License-Identifier: AGPL-3.0-or-later
"""Track B regression tests: automatic references.bib emission in manifest bundles."""
import json
from pathlib import Path

from census.manifest import load_manifest, run_manifest
from census.manifest.methods_text import manifest_bibtex, manifest_citations
from tests.test_manifest import FakeClient

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_bibtex_emits_registry_entries():
    m = load_manifest(str(ROOT / "examples/manifests/r120_mi_ny_cancer_surveillance.json"))
    cites = manifest_citations(m)
    assert "riebler2016" in cites and "kulldorff1997" in cites and "lin1989" in cites
    bib = manifest_bibtex(m, only_if_registry=True)
    assert "@article{riebler2016" in bib or "@book{moraga2023" in bib
    assert "Kulldorff" in bib and "Lin" in bib


def test_run_manifest_writes_bundle_references_bib(tmp_path):
    manifest = {
        "schema_version": 1,
        "title": "Track B BibTeX Bundle Check",
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
            {"id": "ba1", "method": "bias_analysis", "kind": "e_value",
             "args": {"estimate": 2.0, "lower": 1.4, "upper": 2.8}},
        ],
        "hypotheses": [
            {"id": "H1", "statement": "Non-zero CCC.", "analysis": "ag1", "statistic": "ccc", "null_value": 0.0},
            {"id": "H2", "statement": "E-value > 3.", "analysis": "ba1", "statistic": "e_value"},
        ],
    }
    mpath = tmp_path / "m_bib.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run_manifest(str(mpath), output_dir=str(out_dir), client=FakeClient(), use_cache=False)
    assert res["success"] is True
    bib_path = out_dir / "bundle" / "references.bib"
    assert bib_path.exists()
    bib_text = bib_path.read_text(encoding="utf-8")
    assert "lin1989" in bib_text and "vanderweele_ding2017" in bib_text
    bundle_meta = json.loads((out_dir / "bundle" / "bundle.json").read_text(encoding="utf-8"))
    assert "references.bib" in bundle_meta.get("files", {})

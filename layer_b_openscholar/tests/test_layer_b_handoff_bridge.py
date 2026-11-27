# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 146 tests: Layer B handoff bridge provenance verification & tamper detection."""
import json
from pathlib import Path

from layer_b_openscholar.handoff_bridge import validate_and_bridge_seed
from layer_b_openscholar.manifest_seeder import draft_manifest_seed, write_manifest_seed


def test_handoff_bridge_validates_seed_and_detects_tampering(tmp_path: Path):
    papers = [{"paperId": "W1", "title": "County mortality BYM2", "year": 2024, "doi": "10.1000/bym2"}]
    seed = draft_manifest_seed("County mortality BYM2", papers, geography="county", method_family="spatial_bym2")
    paths = write_manifest_seed(seed, tmp_path / "seed")

    ok = validate_and_bridge_seed(paths["json"])
    assert ok["ok"] is True
    assert ok["status"] == "exploratory_hypothesis_seed"
    assert ok["layer_a_template"]["human_signoff_required"] is True
    assert ok["layer_a_template"]["upstream_provenance"]["layer_b_seed_sha256"] == seed["seed_sha256"]

    # Tamper with topic and verify SHA-256 check catches it
    tampered = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    tampered["topic"] = "Altered topic after hashing"
    Path(paths["json"]).write_text(json.dumps(tampered), encoding="utf-8")
    bad = validate_and_bridge_seed(paths["json"])
    assert bad["ok"] is False
    assert any("seed_sha256 mismatch" in e for e in bad["errors"])

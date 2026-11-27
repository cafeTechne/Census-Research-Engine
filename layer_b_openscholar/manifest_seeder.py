# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 143: Deterministic Pre-Registration Manifest Seed Drafter (strictly isolated Layer B).

Converts a Layer B literature dossier or gap-matrix report into a human-reviewable
pre-registration scaffold carrying full provenance (dossier SHA-256, DOIs, citation keys).
Never imports ``census`` and never auto-registers a confirmatory manifest.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


_METHOD_TO_DESIGN = {
    "rdd": "regression_discontinuity",
    "did": "difference_in_differences",
    "spatial_bym2": "disease_map_bym2",
    "small_area": "small_area_estimation",
    "decomposition": "oaxaca_or_arriaga_decomposition",
    "segregation": "tract_segregation_indices",
    "inequality": "who_or_pums_inequality",
    "causal_aipw": "aipw_treatment_effect",
}


def _slug(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (s or "study_seed")[:max_len]


def draft_manifest_seed(
    topic: str,
    papers: Sequence[Mapping[str, Any]],
    *,
    geography: str = "county",
    method_family: str = "small_area",
    primary_states: Sequence[str] = ("26", "36"),
    replication_states: Sequence[str] = ("39", "42"),
    dossier_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a deterministic exploratory pre-registration draft scaffold from Layer B evidence."""
    dois: List[str] = []
    refs: List[Dict[str, Any]] = []
    for p in papers[:15]:
        doi = str(p.get("doi") or "").strip()
        if doi and doi not in dois:
            dois.append(doi)
        refs.append({
            "title": str(p.get("title") or "").strip(),
            "year": p.get("year"),
            "doi": doi or None,
            "paperId": p.get("paperId"),
        })

    if not dossier_sha256:
        canon = json.dumps({"topic": topic, "dois": sorted(dois), "n_papers": len(papers)}, sort_keys=True)
        dossier_sha256 = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    seed_id = f"seed_{_slug(topic)}_{dossier_sha256[:8]}"
    scaffold: Dict[str, Any] = {
        "schema": "layer_b_manifest_seed.v1",
        "status": "exploratory_hypothesis_seed",
        "requires_human_preregistration": True,
        "seed_id": seed_id,
        "topic": topic,
        "proposed_design": {
            "geography": geography,
            "method_family": method_family,
            "candidate_layer_a_family": _METHOD_TO_DESIGN.get(method_family, "exploratory_review"),
            "primary_states": list(primary_states),
            "replication_states": list(replication_states),
            "confidence_level": 0.90,
        },
        "provenance": {
            "dossier_sha256": dossier_sha256,
            "paper_count": len(papers),
            "dois": dois,
            "references": refs,
        },
        "checklist_before_layer_a": [
            "Verify target estimand, exposure/outcome coding, and inclusion criteria.",
            "Confirm geography and vintage availability (ACS 5-year VRE / PUMS / WONDER).",
            "Confirm chosen method is validated in Layer A (not exploratory-only).",
            "Register frozen manifest SHA-256 prior to running confirmatory analyses.",
        ],
    }
    seed_sha = hashlib.sha256(
        json.dumps(scaffold, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    scaffold["seed_sha256"] = seed_sha
    return scaffold


def write_manifest_seed(scaffold: Mapping[str, Any], out_dir: str | Path) -> Dict[str, str]:
    """Write ``manifest_seed.json`` and human-reviewable ``manifest_seed.md``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jpath = out / "manifest_seed.json"
    mpath = out / "manifest_seed.md"
    jpath.write_text(json.dumps(scaffold, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    design = scaffold["proposed_design"]
    prov = scaffold["provenance"]
    lines = [
        f"# Exploratory Pre-Registration Seed: {scaffold['topic']}",
        "",
        f"- **Status:** `{scaffold['status']}` (`requires_human_preregistration: {scaffold['requires_human_preregistration']}`)",
        f"- **Seed ID:** `{scaffold['seed_id']}`",
        f"- **Seed SHA-256:** `{scaffold['seed_sha256']}`",
        f"- **Dossier SHA-256:** `{prov['dossier_sha256']}`",
        f"- **Candidate Design:** `{design['candidate_layer_a_family']}` (`{design['geography']}`, primary `{design['primary_states']}`, replication `{design['replication_states']}`)",
        "",
        "## Supporting Literature DOIs",
    ]
    for doi in prov["dois"]:
        lines.append(f"- `{doi}`")
    if not prov["dois"]:
        lines.append("- *(No DOIs attached — populate from Layer B search before pre-registration.)*")
    lines.append("")
    lines.append("## Human Pre-Registration Checklist")
    for item in scaffold["checklist_before_layer_a"]:
        lines.append(f"- [ ] {item}")
    mpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(jpath), "markdown": str(mpath)}

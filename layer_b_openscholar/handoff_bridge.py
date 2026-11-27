# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 146: Layer B -> Layer A Handoff Bridge Validator (strictly isolated, zero census imports).

Validates a Layer B ``manifest_seed.json`` (and optional ``dossier.json``) provenance chain
and produces a human-reviewable Layer A ``create_manifest`` parameter template.
Never imports ``census`` and never executes or registers a Layer A manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


_REQUIRED_SEED_KEYS = ("schema", "status", "requires_human_preregistration", "seed_id", "topic", "proposed_design", "provenance", "seed_sha256")


def _compute_seed_sha256(seed: Mapping[str, Any]) -> str:
    body = {k: v for k, v in seed.items() if k != "seed_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_and_bridge_seed(
    seed_path: str | Path,
    dossier_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Validate a Layer B manifest_seed.json and emit a human-reviewable Layer A handoff template."""
    sp = Path(seed_path)
    errors: List[str] = []
    if not sp.exists():
        return {
            "ok": False,
            "status": "exploratory_hypothesis_seed",
            "errors": [f"Seed file not found: {sp}"],
            "next_step": "Run `python -m layer_b_openscholar draft-seed` first.",
        }

    seed = json.loads(sp.read_text(encoding="utf-8"))
    for key in _REQUIRED_SEED_KEYS:
        if key not in seed:
            errors.append(f"Missing required seed field: {key}")

    if seed.get("status") != "exploratory_hypothesis_seed":
        errors.append(f"Unexpected seed status: {seed.get('status')!r}")
    if seed.get("requires_human_preregistration") is not True:
        errors.append("Seed must have requires_human_preregistration=true")

    if "seed_sha256" in seed:
        expected = _compute_seed_sha256(seed)
        if seed["seed_sha256"] != expected:
            errors.append(f"seed_sha256 mismatch: recorded={seed['seed_sha256']} computed={expected}")

    if dossier_path is not None:
        dp = Path(dossier_path)
        if not dp.exists():
            errors.append(f"Dossier file not found: {dp}")
        else:
            dossier = json.loads(dp.read_text(encoding="utf-8"))
            d_sha = dossier.get("dossier_sha256")
            s_sha = (seed.get("provenance") or {}).get("dossier_sha256")
            if d_sha and s_sha and d_sha != s_sha:
                errors.append(f"dossier_sha256 mismatch between seed ({s_sha}) and dossier ({d_sha})")

    design = seed.get("proposed_design") or {}
    prov = seed.get("provenance") or {}
    layer_a_template = {
        "study_title": seed.get("topic", ""),
        "geography": design.get("geography", "county"),
        "primary_states": design.get("primary_states", ["26", "36"]),
        "replication_states": design.get("replication_states", ["39", "42"]),
        "candidate_method_family": design.get("candidate_layer_a_family", "exploratory_review"),
        "confidence_level": design.get("confidence_level", 0.90),
        "upstream_provenance": {
            "layer_b_seed_id": seed.get("seed_id"),
            "layer_b_seed_sha256": seed.get("seed_sha256"),
            "layer_b_dossier_sha256": prov.get("dossier_sha256"),
            "dois": prov.get("dois", []),
        },
        "human_signoff_required": True,
    }

    return {
        "ok": len(errors) == 0,
        "status": "exploratory_hypothesis_seed",
        "errors": errors,
        "layer_a_template": layer_a_template if not errors else None,
        "next_step": (
            "Review layer_a_template, confirm a validated method via Layer A `list_manifest_methods`, "
            "then call Layer A `create_manifest`."
            if not errors
            else "Fix the reported provenance errors before handoff."
        ),
    }


def run_exploratory_pipeline(
    topic: str,
    out_dir: str | Path,
    *,
    geography: str = "county",
    method_family: str = "small_area",
    db_path: Optional[str] = None,
    limit: int = 40,
    top_k: int = 10,
    backend: str = "bm25",
) -> Dict[str, Any]:
    """Run the end-to-end offline Layer B pipeline: local-search -> gap-matrix -> draft-seed -> bridge validation."""
    from .gap_matrix import build_gap_matrix
    from .handoff import build_dossier, write_dossier
    from .local_index import LocalLiteratureIndex, resolve_index_path
    from .manifest_seeder import draft_manifest_seed, write_manifest_seed
    from .reranker import OpenScholarReranker

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    idx = LocalLiteratureIndex(db_path)
    papers = idx.search_fts(topic, limit=limit)
    reranker = OpenScholarReranker(backend=backend)
    ranked = reranker.rerank(topic, papers, top_k=top_k)

    dossier = build_dossier(topic, ranked, backend=reranker.active_backend)
    dossier["retrieval_source"] = f"local_fts5:{resolve_index_path(db_path)}"
    dossier_paths = write_dossier(dossier, out)

    gap = build_gap_matrix(ranked, query=topic)
    gap_path = out / "gap_matrix.json"
    gap_path.write_text(json.dumps(gap, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    seed = draft_manifest_seed(
        topic,
        ranked,
        geography=geography,
        method_family=method_family,
        dossier_sha256=dossier["dossier_sha256"],
    )
    seed_paths = write_manifest_seed(seed, out)

    bridge = validate_and_bridge_seed(seed_paths["json"], dossier_path=dossier_paths["dossier_json"])
    bridge_path = out / "bridge_report.json"
    bridge_path.write_text(json.dumps(bridge, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "ok": bool(bridge["ok"]),
        "status": "exploratory_hypothesis_seed",
        "topic": topic,
        "paper_count": len(ranked),
        "dossier_sha256": dossier["dossier_sha256"],
        "seed_id": seed["seed_id"],
        "seed_sha256": seed["seed_sha256"],
        "paths": {
            **dossier_paths,
            "gap_matrix": str(gap_path),
            "manifest_seed_json": seed_paths["json"],
            "manifest_seed_md": seed_paths["markdown"],
            "bridge_report": str(bridge_path),
        },
        "next_step": bridge["next_step"],
    }

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 138: Deterministic Evidence & Hypothesis-Gap Matrix builder (Architecture v11 Layer B)."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Dict, List, Sequence

GEOGRAPHY_PATTERNS: Dict[str, tuple[str, ...]] = {
    "national": ("united states", "u.s.", "national"),
    "state": ("state-level", "state level", "across states"),
    "county": ("county", "counties"),
    "tract": ("census tract", "tracts", "neighborhood"),
    "pums_microdata": ("pums", "microdata", "individual-level", "person-level"),
}

METHOD_PATTERNS: Dict[str, tuple[str, ...]] = {
    "spatial_disease_map": ("bym2", "besag", "disease mapping", "spatial smoothing", "icar"),
    "spatial_scan": ("kulldorff", "spatial scan", "cluster detection"),
    "rdd": ("regression discontinuity", "rdd", "age 65", "cutoff"),
    "did_policy": ("difference-in-differences", "difference in differences", "staggered", "synthetic control"),
    "small_area_fh": ("fay-herriot", "fay herriot", "small area estimation", "empirical bayes"),
    "decomposition": ("oaxaca", "blinder", "fairlie", "kitagawa", "arriaga"),
    "segregation": ("dissimilarity", "segregation", "theil", "isolation index"),
}


def _extract_tags(text: str, vocab: Dict[str, tuple[str, ...]]) -> List[str]:
    low = (text or "").lower()
    return [tag for tag, phrases in vocab.items() if any(p in low for p in phrases)]


def build_gap_matrix(papers: Sequence[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
    """Build a deterministic (geography x method x recency) coverage matrix and ranked gap proposals."""
    geo_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    cell_counts: Counter[tuple[str, str]] = Counter()
    recency = {"pre_2020": 0, "2020_plus": 0, "unknown": 0}
    annotated: List[Dict[str, Any]] = []

    for p in papers:
        blob = f"{p.get('title', '')} {p.get('abstract', '')}"
        geos = _extract_tags(blob, GEOGRAPHY_PATTERNS)
        meths = _extract_tags(blob, METHOD_PATTERNS)
        yr = p.get("year")
        if isinstance(yr, int):
            recency["2020_plus" if yr >= 2020 else "pre_2020"] += 1
        else:
            recency["unknown"] += 1
        for g in geos:
            geo_counts[g] += 1
        for m in meths:
            method_counts[m] += 1
        for g in geos:
            for m in meths:
                cell_counts[(g, m)] += 1
        annotated.append({
            "paperId": p.get("paperId", ""),
            "doi": p.get("doi", ""),
            "year": yr,
            "geographies": geos,
            "methods": meths,
        })

    # Identify under-studied (geography x method) cells relative to active geographies/methods
    active_geos = list(GEOGRAPHY_PATTERNS.keys())
    active_methods = list(METHOD_PATTERNS.keys())
    gap_seeds = []
    for g in active_geos:
        for m in active_methods:
            cnt = int(cell_counts[(g, m)])
            if cnt == 0:
                gap_seeds.append({
                    "geography": g,
                    "method": m,
                    "observed_papers": 0,
                    "status": "exploratory_hypothesis_seed",
                    "proposal": f"Under-studied combination in retrieved corpus: apply {m} at {g} scale.",
                })

    body = {
        "schema_version": 1,
        "status": "exploratory_hypothesis_seed",
        "query": query,
        "paper_count": len(papers),
        "recency": recency,
        "geography_counts": dict(sorted(geo_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "covered_cells": {f"{g}::{m}": c for (g, m), c in sorted(cell_counts.items())},
        "gap_proposals": gap_seeds[:15],
        "annotated_papers": annotated,
    }
    body["matrix_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return body

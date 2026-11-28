# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 209: Deterministic domain-synonym query expansion for Layer B Hybrid RAG (zero census imports)."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

DOMAIN_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "bym2": ("Besag York Mollie", "disease mapping", "ICAR"),
    "scpc": ("spatial correlation", "Muller Watson", "spatial inference"),
    "rpp": ("regional price parity", "cost of living", "BEA"),
    "kww": ("rank confidence", "ranking uncertainty", "Mogstad"),
    "pums": ("public use microdata", "American Community Survey"),
    "maup": ("modifiable areal unit", "spatial aggregation"),
    "qba": ("quantitative bias analysis", "unmeasured confounding"),
    "sae": ("small area estimation", "Fay Herriot"),
    "vre": ("variance replicate", "successive difference replication"),
    "rdd": ("regression discontinuity", "cutoff bandwidth"),
    "did": ("difference in differences", "staggered adoption"),
    "e-value": ("VanderWeele", "unmeasured confounding sensitivity"),
    "fay-herriot": ("small area estimation", "empirical best linear unbiased"),
}

_WORD_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")


def expand_domain_query(query: str) -> Tuple[str, List[str]]:
    """Append domain-synonym terms for recognized epidemiology/demography acronyms.

    Returns ``(expanded_query, added_terms)``. Never duplicates terms already in ``query``.
    """
    q_low = (query or "").lower()
    tokens = set(_WORD_RE.findall(q_low))
    added: List[str] = []
    for key, syns in DOMAIN_SYNONYMS.items():
        if key in tokens or key in q_low:
            for syn in syns:
                if syn.lower() not in q_low and syn not in added:
                    added.append(syn)
    if not added:
        return query, []
    return f"{query} {' '.join(added)}".strip(), added

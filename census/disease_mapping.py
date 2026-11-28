# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 96: spatial disease mapping of counts with BYM2 and exceedance probabilities (backlog N73; Moraga 2023,
chapters 9-10). Laplace approximation (``census/disease_mapping_core.py``); no INLA dependency.

Validation (``docs/audits/disease_mapping_validation.md``; criterion tag ``criterion-r96``), MI counties and Wayne
County tracts, 500 draws per cell: relative-risk intervals covered .840-.896 (B1) and .851-.897 (B2) in 15 of 16
cells but .796/.790 in one (83 counties, median expected count 5, weak and mostly unstructured variation), so the
pre-set rule failed and the intervals are exploratory. Exceedance probabilities were calibrated in every cell (areas
with P(RR > 1.2) >= .8 were truly above 1.2 in 75-96% of cases). BYM2 had lower error than Poisson-gamma EB and raw
SMRs in every cell.
Suppressed counts (WONDER 1-9, given as missing) contribute no likelihood: those areas' relative risks are
predictions from their neighbours and covariates, labelled as such, and nothing is derived from the hidden count.
"""
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from . import disease_mapping_core as dm

AUDIT = "docs/audits/disease_mapping_validation.md"
REPAIRS_AUDIT = "docs/audits/repairs104_validation.md"
VALIDATED = {"B1": False, "B2": False}   # criterion not met in 1 of 16 cells (see module docstring)
B3_MIN_MEDIAN_E = 30.0                   # Round 104: B3 (PC prior + log-grid Jacobian) validated from median E >= 30
EXCEEDANCE_CALIBRATED = True


def _fit_with_missing(y, E, X, eigen, method: str = "B2"):
    """Missing counts: drop their likelihood terms by giving them zero exposure (E = 0 contributes nothing)."""
    obs = np.isfinite(y)
    y2 = np.where(obs, y, 0.0); E2 = np.where(obs, E, 1e-12)
    if method == "B3":
        from . import repairs104_core as r104
        return {"B3": r104.bym2_pc(y2, E2, X=X, eigen=eigen)}
    return dm.bym2(y2, E2, X=X, eigen=eigen)


def disease_map(frame: pd.DataFrame, observed: str, expected: str, edges: Sequence[Tuple[int, int]],
                covariates: Sequence[str] = (), threshold: float = 1.2, method: str = "B2",
                allow_disconnected: bool = False) -> Dict[str, Any]:
    """Relative risks (observed / expected, smoothed by BYM2) with 90% intervals and P(RR > threshold) per area.
    ``frame`` rows align with the 0-based ``edges`` (a connected neighbour graph unless ``allow_disconnected=True``,
    Round 200 / N132). ``method="B3"`` (Round 104) adds the Riebler et al. (2016) PC prior and log-grid Jacobian
    (validated when median expected count >= 30, single connected component, and all counts are observed)."""
    if method not in ("B1", "B2", "B3"):
        raise ValueError("method must be 'B1' (empirical Bayes), 'B2' (flat grid) or 'B3' (PC-prior grid)")
    y = pd.to_numeric(frame[observed], errors="coerce").to_numpy(float)
    E = pd.to_numeric(frame[expected], errors="coerce").to_numpy(float)
    if not (np.isfinite(E).all() and (E > 0).all()):
        raise ValueError("expected counts must be positive for every area")
    if np.any(y[np.isfinite(y)] < 0) or not np.allclose(y[np.isfinite(y)], np.round(y[np.isfinite(y)])):
        raise ValueError("observed must be non-negative integer counts (missing = suppressed)")
    X = frame[list(covariates)].apply(pd.to_numeric, errors="coerce").to_numpy(float) if covariates else None
    if X is not None and not np.isfinite(X).all():
        raise ValueError("covariates must be complete")
    comps = dm.graph_components(len(frame), edges)
    n_components = len(comps)
    n_islands = sum(1 for c in comps if len(c) == 1)
    eigen = dm.scaled_icar_eigen(len(frame), edges, allow_disconnected=allow_disconnected)
    fit = _fit_with_missing(y, E, X, eigen, method=method)[method]
    p = dm.exceedance(fit, threshold)
    missing = ~np.isfinite(y)
    out = pd.DataFrame({"GEOID": frame.GEOID.astype(str).to_numpy(), "expected": E, "relative_risk": fit["rr"],
                        "ci_lower": fit["lower"], "ci_upper": fit["upper"], "p_exceed": p,
                        "count_used": ~missing})
    med_e = float(np.median(E))
    if method == "B3":
        validated = bool(med_e >= B3_MIN_MEDIAN_E and not missing.any() and n_components == 1)
    else:
        validated = bool(VALIDATED[method])
    notes = ["BYM2 Poisson model (scaled ICAR + unstructured effects), Laplace approximation; relative risks are "
             "shrunk toward the neighbourhood and overall level (Moraga 2023 ch. 10).",
             f"Hyperparameters: sigma {fit['sigma']:.3g}, phi {fit['phi']:.2f} (share of spatially structured variance)."]
    if n_components > 1:
        notes.append(f"Multi-component BYM2 scaling (Freni-Sterrantino et al. 2018) applied across {n_components} "
                     f"connected components ({n_islands} isolated island(s) given unstructured IID prior); intervals "
                     "are exploratory until multi-component coverage is validated.")
    if missing.any():
        notes.append(f"{int(missing.sum())} area(s) with suppressed counts: relative risks predicted from neighbours "
                     "only (not validated; nothing derived from the hidden counts).")
    if not validated:
        if method == "B3":
            notes.append(f"Relative-risk intervals are exploratory: B3 (PC-prior grid) is validated from median "
                         f"expected count >= {B3_MIN_MEDIAN_E:.0f} on a single connected component without suppressed "
                         f"counts (median here {med_e:.1f}, components {n_components}; {REPAIRS_AUDIT}). Exceedance "
                         "probabilities were calibrated in validation.")
        else:
            notes.append(f"Relative-risk intervals are exploratory: they under-covered (.79-.80) with very small expected "
                         f"counts (median 5) across few areas, and covered .84-.90 otherwise ({AUDIT}). Exceedance "
                         "probabilities were calibrated in validation.")
    return dict(method=method, threshold=threshold, table=out, sigma=fit["sigma"], phi=fit["phi"],
                n_components=n_components, n_islands=n_islands,
                validated=validated, notes=notes, audit=REPAIRS_AUDIT if method == "B3" else AUDIT)

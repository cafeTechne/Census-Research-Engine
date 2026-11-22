# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 73 frozen core: indices with published (fixed) loadings, e.g. Monnat's factor-weighted distress index.

Each indicator is standardised with full-sample means and SDs, the published loadings are applied, and per-area
replicate intervals follow Round 36 (census.index_core.score_intervals) with the loadings held fixed.
"""
import numpy as np

from . import index_core as ic


def fixed_loadings(indicators, loadings):
    missing = [c for c in indicators if c not in loadings]
    if missing:
        raise ValueError(f"no loading for {missing}")
    l = np.array([float(loadings[c]) for c in indicators])
    if not np.isfinite(l).all() or np.all(l == 0):
        raise ValueError("loadings must be finite and not all zero")
    return l


def scores_and_intervals(X, reps, loadings_vec, level=.90):
    m, s = ic.standardize(X)
    return ic.score_intervals(X, reps, m, s, loadings_vec, level), (m, s)

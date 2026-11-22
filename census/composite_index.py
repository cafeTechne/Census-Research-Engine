# SPDX-License-Identifier: AGPL-3.0-or-later
"""Composite indices from ACS estimates with replicate uncertainty (Round 36).

Validated by ``docs/audits/index_validation.md`` (criterion e86907d): per-area 90% score intervals
(first principal component or equal weights; full-sample standardisation and loadings fixed in every
replicate) covered the area's error-free score (mean .898-.899, every area >= .873); the Feldt
interval for Cronbach's alpha covered for independent areas (.891-.912) but under-covered with
spatially correlated areas (.58-.67). Quintile stability and typologies are descriptive.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.vq import kmeans2

from . import index_core as ic

AUDIT = "docs/audits/index_validation.md"


# Round 73 (docs/audits/methods73_validation.md): per-area intervals with fixed published loadings.
LOADINGS_VALIDATED = True   # LI passed (mean .897-.899, every area >= .878)
LOADINGS_AUDIT = "docs/audits/methods73_validation.md"


def _ari(a, b):
    from scipy.special import comb
    ct = pd.crosstab(a, b).to_numpy()
    sum_comb = comb(ct, 2).sum(); a_c = comb(ct.sum(1), 2).sum(); b_c = comb(ct.sum(0), 2).sum()
    expected = a_c*b_c/comb(ct.sum(), 2)
    return float((sum_comb-expected)/(.5*(a_c+b_c)-expected)) if (a_c+b_c)/2 != expected else 1.0


def build_index(frame: pd.DataFrame, indicators: Sequence[str], *, replicates: Optional[pd.DataFrame] = None,
                method: str = "pca", reverse: Sequence[str] = (), outcome: Optional[str] = None,
                typology_k: Optional[int] = None, level: float = 0.90, label_col: str = "GEOID",
                seed: int = 20270121, coords: Optional[pd.DataFrame] = None,
                loadings: Optional[Dict[str, float]] = None, standardize: bool = False) -> Dict[str, Any]:
    """Index of ``indicators`` (higher = more deprived after flipping ``reverse``).

    ``method="loadings"`` (Round 73) applies published fixed ``loadings`` (e.g. a factor-weighted index from a
    paper) to the standardised indicators; two indicators are allowed. ``standardize=True`` rescales the scores
    (and their intervals) to mean 0, SD 1."""
    indicators = list(indicators)
    if method == "loadings":
        if not loadings:
            raise ValueError("method='loadings' needs loadings={indicator: weight}")
        if len(indicators) < 2:
            raise ValueError("a loadings index needs at least two indicators")
    elif len(indicators) < 3:
        raise ValueError("an index needs at least three indicators")
    if outcome is not None and outcome in indicators:
        raise ValueError(f"CIRCULARITY: the outcome {outcome!r} cannot be an indicator of an index used to explain it")
    bad = [r for r in reverse if r not in indicators]
    if bad:
        raise ValueError(f"reverse lists non-indicators: {bad}")
    data = frame.dropna(subset=indicators).reset_index(drop=True)
    X = data[indicators].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(X).all():
        raise ValueError("indicators must be numeric")
    sign = np.array([-1. if c in reverse else 1. for c in indicators])
    X = X*sign
    m, s = ic.standardize(X)
    Z = (X-m)/s
    if method == "loadings":
        from . import loadings_index_core as lc
        l, share = lc.fixed_loadings(indicators, loadings), None
    else:
        l, share = ic.loadings(Z, method)
    labels = data[label_col].astype(str).tolist() if label_col in data else list(map(str, range(len(data))))
    notes = [f"Indicators standardised with full-sample means and SDs; {method} weights fixed in every replicate."]
    quint = pd.qcut(ic.scores(X, m, s, l), 5, labels=False)+1
    out: Dict[str, Any] = dict(indicators=indicators, method=method, loadings=dict(zip(indicators, map(float, l))),
                               explained_variance=share, n=len(X))
    if replicates is not None:
        from .correlation import _replicate_cube
        cube = _replicate_cube(data, replicates, indicators)
        missing = [c for c in indicators if c not in cube]
        if missing:
            raise ValueError(f"no replicates for {missing}")
        reps = np.stack([cube[c]*sg for c, sg in zip(indicators, sign)], axis=1)
        sc, se, lo, hi = ic.score_intervals(X, reps, m, s, l, level)
        rep_scores = np.einsum("nkr,k->nr", (reps-m[None, :, None])/s[None, :, None], l)
        cuts = np.quantile(sc, [.2, .4, .6, .8])
        same = (np.digitize(rep_scores, cuts)+1 == quint[:, None]).mean(axis=1)
        out["validated_scores"] = True if method != "loadings" else LOADINGS_VALIDATED
    else:
        sc = ic.scores(X, m, s, l); se = lo = hi = np.full(len(sc), np.nan); same = np.full(len(sc), np.nan)
        out["validated_scores"] = False
        notes.append("EXPLORATORY: no replicates, so score intervals are unavailable.")
    if standardize:
        mu, sd = float(np.mean(sc)), float(np.std(sc, ddof=1))
        sc, lo, hi, se = (sc-mu)/sd, (lo-mu)/sd, (hi-mu)/sd, se/sd
        notes.append("Scores standardised to mean 0, SD 1 after weighting (intervals rescaled alike).")
    out["table"] = pd.DataFrame(dict(area=labels, score=sc, se=se, lower=lo, upper=hi, quintile=quint,
                                     quintile_stability=same)).sort_values("score", ascending=False).reset_index(drop=True)
    if coords is not None:
        from . import small_spatial as ss
        from . import small_spatial_core as ssc
        alpha = ssc.alpha_neff(Z, ss.distance_classes(data.assign(GEOID=data[label_col].astype(str)), coords), level)
        out["cronbach_alpha"] = dict(alpha, method="Feldt (effective n)", validated=ss.NEFF_ALPHA_VALIDATED,
                                     note=f"n replaced by the effective sample size of the total score (Round 48, {ss.AUDIT})")
    else:
        alpha = ic.alpha_interval(Z, level)
        out["cronbach_alpha"] = dict(alpha, method="Feldt", validated=True,
                                     note="validated for independent areas; under-covered with spatial dependence "
                                          "(pass coords for the Round 48 effective-n interval)")
    if typology_k:
        rng = np.random.default_rng(seed)
        _, grp = kmeans2(Z, typology_k, minit="++", seed=rng)
        typ = {"k": typology_k, "groups": pd.Series(grp).value_counts().sort_index().to_dict(), "note": "descriptive"}
        if replicates is not None:
            aris = []
            for r in range(reps.shape[2]):
                _, g_r = kmeans2((reps[:, :, r]-m)/s, typology_k, minit="++", seed=np.random.default_rng(seed+r+1))
                aris.append(_ari(grp, g_r))
            typ["replicate_adjusted_rand_median"] = float(np.median(aris))
        out["typology"] = typ
        out["typology_labels"] = dict(zip(labels, map(int, grp)))
    out.update(notes=notes, audit=AUDIT)
    return out

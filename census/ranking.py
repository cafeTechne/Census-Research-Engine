# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ranking areas and comparing them with a reference, with ACS uncertainty (Round 34).

Validated by ``docs/audits/ranking_validation.md`` (criterion 6286ad9):
- Klein-Wright-Wieczorek rank intervals, individual (Bonferroni over K-1) and joint (over
  K(K-1)/2): both passed, conservatively. Parametric-bootstrap percentile ranks under-covered
  badly (per-area coverage down to .33) and are not offered.
- Each area versus a reference (a weighted mean of the areas, which shares their errors, or a fixed
  value): Holm and simultaneous max-|z| both kept familywise error <= .11; simultaneous intervals
  covered jointly (.89-.91).
Areas are treated as independent samples. Non-numeric values (e.g. WONDER "suppressed") are
excluded and listed, never ranked.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import ranking_core as rc

AUDIT = "docs/audits/ranking_validation.md"


def _inputs(frame, variable, replicates=None, se_col=None, moe_col=None, label_col="GEOID", extra=()):
    values = pd.to_numeric(frame[variable], errors="coerce")
    keep = values.notna().to_numpy()
    excluded = frame.loc[~keep, label_col].astype(str).tolist() if label_col in frame else []
    f = frame.loc[keep].reset_index(drop=True)
    x = values[keep].to_numpy(float)
    reps = None
    if replicates is not None:
        from .correlation import _replicate_cube
        cube = _replicate_cube(f, replicates, [variable]+[c for c in extra if c])
        if variable not in cube:
            raise ValueError(f"no replicates for {variable!r}")
        reps = cube
        s = np.sqrt(.05*np.sum((cube[variable]-x[:, None])**2, axis=1))
    elif se_col:
        s = pd.to_numeric(f[se_col], errors="coerce").to_numpy(float)
    elif moe_col:
        s = pd.to_numeric(f[moe_col], errors="coerce").to_numpy(float)/1.645
    else:
        raise ValueError("give replicates, se_col or moe_col")
    if not (np.isfinite(s).all() and (s > 0).all()):
        raise ValueError("every ranked area needs a finite, positive standard error")
    labels = f[label_col].astype(str).tolist() if label_col in f else list(map(str, range(len(f))))
    return f, x, s, reps, labels, excluded


def rank_intervals(frame: pd.DataFrame, variable: str, *, replicates: Optional[pd.DataFrame] = None,
                   se_col: Optional[str] = None, moe_col: Optional[str] = None, joint: bool = False,
                   level: float = 0.90, label_col: str = "GEOID") -> Dict[str, Any]:
    """Rank 1 = the highest value. Returns one row per area with its point rank and rank interval."""
    f, x, s, _, labels, excluded = _inputs(frame, variable, replicates, se_col, moe_col, label_col)
    lo, hi = rc.rank_intervals(x, s, joint, level)
    K = len(x)
    point = K-pd.Series(x).rank(method="first").to_numpy(int)+1
    table = pd.DataFrame(dict(area=labels, estimate=x, se=s, rank=point, rank_lower=lo, rank_upper=hi))
    table = table.sort_values("rank").reset_index(drop=True)
    notes = [("Joint" if joint else "Individual") + " rank intervals (Klein, Wright and Wieczorek 2020): "
             + ("all intervals hold together" if joint else "each interval holds for its own area")
             + f" with {level:.0%} confidence. Rank 1 is the highest value."]
    if excluded:
        notes.append(f"{len(excluded)} area(s) without a numeric value were excluded, not ranked: {excluded[:10]}")
    certain_top = table.loc[table.rank_upper <= max(1, K//10), "area"].tolist()
    return dict(table=table, K=K, joint=joint, validated=True, median_interval_width=float(np.median(hi-lo+1)),
                surely_top_decile=certain_top, excluded=excluded, notes=notes, audit=AUDIT)


def compare_to_reference(frame: pd.DataFrame, variable: str, *, replicates: Optional[pd.DataFrame] = None,
                         se_col: Optional[str] = None, moe_col: Optional[str] = None, reference: Any = "weighted_mean",
                         weights: Optional[str] = None, method: str = "holm", level: float = 0.90,
                         label_col: str = "GEOID") -> Dict[str, Any]:
    """Each area minus the reference: the weighted mean of the areas (``weights``) or a fixed number."""
    if method not in ("holm", "simultaneous"):
        raise ValueError("method must be 'holm' or 'simultaneous'")
    f, x, s, reps, labels, excluded = _inputs(frame, variable, replicates, se_col, moe_col, label_col)
    if isinstance(reference, str):
        if reference != "weighted_mean" or not weights:
            raise ValueError("reference must be a number, or 'weighted_mean' with weights")
        w = pd.to_numeric(f[weights], errors="coerce").to_numpy(float)
        if not (np.isfinite(w).all() and (w >= 0).all() and w.sum() > 0):
            raise ValueError("weights must be finite, non-negative and not all zero")
        w = w/w.sum()
        ref_value = float(w @ x)
        d = x-ref_value
        if reps is not None:
            dr = reps[variable]-(w @ reps[variable])[None, :]
            cov = .05*(dr-d[:, None]) @ (dr-d[:, None]).T
            basis = "ACS replicates (the reference shares the areas' errors)"
        else:
            cov = rc.reference_covariance(s, w)
            basis = "independent area errors (exact formula)"
    else:
        ref_value = float(reference)
        d = x-ref_value
        cov = np.diag(s**2)
        basis = "fixed reference value (no reference uncertainty)"
    out = rc.versus_reference(d, cov, level)
    pcol = "p_holm" if method == "holm" else "p_simultaneous"
    table = pd.DataFrame(dict(area=labels, estimate=x, difference=d, se=out["se"], z=out["z"], p_raw=out["p_raw"],
                              p_adjusted=out[pcol]))
    if method == "simultaneous":
        table["lower"], table["upper"] = out["lower"], out["upper"]
    table["differs"] = table.p_adjusted < 1-level
    notes = [f"Covariance basis: {basis}.", f"Multiplicity: {method}."]
    if excluded:
        notes.append(f"{len(excluded)} area(s) without a numeric value were excluded: {excluded[:10]}")
    return dict(table=table, reference_value=ref_value, method=method, validated=True,
                n_differ=int(table.differs.sum()), K=len(x), excluded=excluded, notes=notes, audit=AUDIT)

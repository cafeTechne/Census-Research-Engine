# SPDX-License-Identifier: AGPL-3.0-or-later
"""Agreement between two sources of the same quantity (Round 37).

Validated by ``docs/audits/agreement_validation.md`` (criterion e6d4be6), for independent areas:
- the mean difference (bias) with a t interval (coverage .894-.900);
- Cohen's kappa of the two sources' quintile classes (.883-.912).
Failed (estimates reported, intervals labelled exploratory): Bland-Altman limits of agreement for
the observed values (.838) and for the error-free values (.826), Lin's concordance correlation
(.859) and its error-corrected version (.38-.77). Differences of noisy estimates have heavier tails
than the normal theory behind those intervals.
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from . import agreement_core as ag

AUDIT = "docs/audits/agreement_validation.md"


def check_agreement(frame: pd.DataFrame, a: str, b: str, *, a_se: Optional[str] = None, b_se: Optional[str] = None,
                    replicates: Optional[pd.DataFrame] = None, level: float = 0.90) -> Dict[str, Any]:
    """Compare source ``b`` with source ``a`` (difference = b - a), one row per area."""
    f = frame.copy()
    f[a], f[b] = pd.to_numeric(f[a], errors="coerce"), pd.to_numeric(f[b], errors="coerce")
    f = f.dropna(subset=[a, b]).reset_index(drop=True)
    if len(f) < 10:
        raise ValueError("agreement needs at least ten areas with both values")
    x, y = f[a].to_numpy(float), f[b].to_numpy(float)
    sa = sb = None
    if replicates is not None:
        from .correlation import _replicate_cube
        cube = _replicate_cube(f, replicates, [c for c in (a, b)])
        if a in cube:
            sa = np.sqrt(.05*np.sum((cube[a]-x[:, None])**2, axis=1))
        if b in cube:
            sb = np.sqrt(.05*np.sum((cube[b]-y[:, None])**2, axis=1))
    if sa is None and a_se:
        sa = pd.to_numeric(f[a_se], errors="coerce").to_numpy(float)
    if sb is None and b_se:
        sb = pd.to_numeric(f[b_se], errors="coerce").to_numpy(float)
    out: Dict[str, Any] = dict(n=len(f), a=a, b=b, audit=AUDIT)
    out["bias"] = dict(ag.bias(x, y, level), validated=True)
    out["kappa_quintiles"] = dict(ag.kappa_quintiles(x, y, level), validated=True)
    out["limits_observed"] = dict(ag.limits_observed(x, y, level), validated=False)
    out["ccc"] = dict(ag.ccc(x, y, level=level), validated=False)
    notes = ["Areas assumed independent. Validated: bias and kappa. Limits of agreement and concordance are "
             "estimates whose intervals failed validation (exploratory)."]
    if sa is not None:
        try:
            out["limits_error_free"] = dict(ag.limits_true(x, y, sa, sb, level), validated=False)
            out["ccc_error_free"] = dict(ag.ccc(x, y, sa, sb, level), validated=False)
        except ValueError as exc:
            notes.append(f"Error-free quantities unavailable: {exc}")
    else:
        notes.append("No standard errors for source A: error-free limits and concordance are not computed.")
    out["notes"] = notes
    return out

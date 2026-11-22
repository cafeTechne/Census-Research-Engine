# SPDX-License-Identifier: AGPL-3.0-or-later
"""Three-level random-intercept models (Round 73, backlog N51; was N46), e.g. tracts in counties in states.

Fixed effects use t(G_top - 1) Wald intervals (M1); variance shares (bottom / middle / top) come with
delete-one-top-unit jackknife intervals (M3), which stay exploratory (Round 73 screened them on 100 draws only).
"""
from typing import Any, Dict, Sequence

import pandas as pd

from . import multilevel3_core as core

AUDIT = "docs/audits/methods73_validation.md"
FIXED_VALIDATED = True       # M1 passed (.904-.913; docs/audits/methods73_validation.md)
SHARES_VALIDATED = False    # M3 is screening only


def fit_three_level(formula: str, frame: pd.DataFrame, groups: Sequence[str], level: float = .90,
                    share_intervals: bool = True) -> Dict[str, Any]:
    if len(groups) != 2:
        raise ValueError("groups must be [top, middle], e.g. ['state', 'county']")
    top, mid = groups
    cols = [top, mid]
    data = frame.dropna(subset=cols).copy()
    data[top] = data[top].astype(str); data[mid] = data[top]+"|"+data[mid].astype(str)
    m, v = core.fit3(data, formula, top, mid)
    G = data[top].nunique()
    fixed = core.fixed_intervals(m, G, level)
    fixed["validated"] = bool(FIXED_VALIDATED)
    sh = core.shares(v)
    out: Dict[str, Any] = dict(model="three-level random intercepts (REML)", groups=list(groups), n=int(len(data)),
                               n_top=int(G), n_middle=int(data[mid].nunique()), table=fixed, variances=v,
                               shares={"bottom": sh["bottom"], "middle": sh["mid"], "top": sh["top"]},
                               audit=AUDIT, validated=bool(FIXED_VALIDATED))
    notes = [f"Fixed-effect intervals: t({G-1}) Wald (Round 73 M1); "
             + ("validated." if FIXED_VALIDATED else "exploratory (not validated).")]
    if share_intervals:
        jk = core.jackknife_shares(data, formula, top, mid, level)
        out["share_intervals"] = {("middle" if k == "mid" else k): r for k, r in jk.items()}
        notes.append(f"Share intervals: delete-one-{top} jackknife on the logit scale; EXPLORATORY (Round 73 screened "
                     "them on 100 draws only).")
    out["notes"] = notes
    return out

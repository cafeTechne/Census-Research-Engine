# SPDX-License-Identifier: AGPL-3.0-or-later
"""Income inequality from PUMS microdata with SDR replicate variance (Round 56).

Validated (``docs/audits/pums_inequality_validation.md``, criterion d91201b; Round 32 generator, 8 cells,
lognormal, heavier-tailed and zero-inflated incomes): the Gini coefficient (.861-.908), log P90/P10 and log
P80/P20 (.888-.923) and the difference in Gini between two groups (.873-.899). Failed (exploratory, reported
with a note): Theil T (.811-.904), Atkinson .5 (.845-.898) and 1 (.858-.902), and the top-decile share
(.850-.906). Quantile ratios of heaped dollar amounts get the same heaping check as medians (Round 32).
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from . import pums
from . import pums_inequality_core as core
from .pums_inference import HEAPING_LIMIT, _flags, _frame, _label

AUDIT = "docs/audits/pums_inequality_validation.md"
VALIDATED = {"gini": True, "theil_t": False, "atkinson_0.5": False, "atkinson_1": False, "log_p90_p10": True,
             "log_p80_p20": True, "top10_share": False}
GINI_DIFFERENCE_VALIDATED = True
QUANTILES = {"log_p90_p10": (.9, .1), "log_p80_p20": (.8, .2)}


def _heaping(y, w, qs):
    o = np.argsort(y, kind="mergesort"); ys, ws = y[o], w[o]
    cum = np.cumsum(ws)/ws.sum()
    out = 0.
    for q in qs:
        v = ys[np.argmax(cum >= q-1e-12)]
        out = max(out, float(ws[ys == v].sum()/ws.sum()))
    return out


def _table(y, W, min_n):
    positive = y > 0
    vals = core.measures(y, W)
    if not positive.all() and positive.sum() >= 2:
        vals_pos = core.measures(y[positive], W[positive])
        for m in core.NEEDS_POSITIVE:
            vals[m] = vals_pos[m]
    rows, notes = [], []
    for m in core.MEASURES:
        if m not in vals:
            continue
        s = core.sdr_summary(vals[m])
        ok = VALIDATED[m] and s["se"] > 0
        note = None
        if m in QUANTILES:
            ys = y[positive] if not positive.all() else y
            heap = _heaping(ys, W[positive, 0] if not positive.all() else W[:, 0], QUANTILES[m])
            if heap > HEAPING_LIMIT:
                ok = False
                note = (f"{heap:.0%} of the weight sits exactly at a quantile used (heaped values); replicate SEs are "
                        "unreliable (validation used continuous incomes)")
        if not VALIDATED[m]:
            note = "failed the Round 56 coverage validation; exploratory only"
        rows.append(dict(measure=m, **s, validated=bool(ok), note=note))
    if not positive.all():
        notes.append(f"{int((~positive).sum())} zero income record(s): included in the Gini and top share; excluded "
                     "from Theil, Atkinson and the quantile ratios.")
    notes += _flags(len(y), min_n)
    return pd.DataFrame(rows), notes


def pums_inequality(df: pd.DataFrame, var: Any, weight: str = "person", where: Any = None, by: Any = None,
                    min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Inequality of ``var`` (nonnegative incomes) with SDR 90% intervals; with ``by`` (two groups) also each
    group's measures and the Gini difference (second group minus first, per-replicate differences)."""
    cols = {"var": var} if by is None else {"var": var, "by": by}
    v, W = _frame(df, cols, where, weight)
    y = np.asarray(v["var"], float)
    if (y < 0).any():
        raise ValueError("negative incomes are refused (e.g. PINCP losses); restrict with where='... >= 0'")
    table, notes = _table(y, W, min_n)
    out = dict(var=str(var), weight=weight, n=int(len(y)), table=table, notes=notes, audit=AUDIT)
    if by is not None:
        levels = sorted(pd.unique(v["by"]))
        if len(levels) != 2:
            raise ValueError("by must define exactly two groups")
        groups, ginis = {}, []
        for g in levels:
            m = v["by"] == g
            t, n_ = _table(y[m], W[m], min_n)
            groups[_label(g)] = dict(n=int(m.sum()), table=t, notes=n_)
            ginis.append(core.measures(y[m], W[m])["gini"])
        d = core.sdr_summary(ginis[1]-ginis[0])
        out.update(groups=groups, gini_difference=dict(**d, validated=bool(GINI_DIFFERENCE_VALIDATED and d["se"] > 0),
                                                       groups=[_label(g) for g in levels]))
    return out

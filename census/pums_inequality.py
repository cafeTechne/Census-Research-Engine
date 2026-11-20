# SPDX-License-Identifier: AGPL-3.0-or-later
"""Income inequality from PUMS microdata with SDR replicate variance (Round 56).

Validated (``docs/audits/pums_inequality_validation.md``, criterion d91201b; Round 32 generator, 8 cells,
lognormal, heavier-tailed and zero-inflated incomes): the Gini coefficient (.861-.908), log P90/P10 and log
P80/P20 (.888-.923) and the difference in Gini between two groups (.873-.899). Failed (exploratory, reported
with a note): Theil T (.811-.904), Atkinson .5 (.845-.898) and 1 (.858-.902), and the top-decile share
(.850-.906). Round 60 repaired three of them with logit-transformed SDR intervals (Atkinson 1 everywhere;
Atkinson .5 and the top-decile share from 7,000 records); Theil T stays exploratory. Quantile ratios of heaped
dollar amounts get the same heaping check as medians (Round 32).
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
# Round 60 (criterion 60a3b06; docs/audits/pums_inequality_repair_validation.md): transformed SDR intervals (logit)
# validated Atkinson 1 everywhere (.872-.893) and Atkinson .5 and the top-decile share with at least 7,000
# unweighted records (at least .871 in the 3,000-household cells; down to .846 in smaller samples). Theil T still
# failed (.820-.889 with the log transform; .859 at 3,000 households); the SDR bias correction lowered coverage.
REPAIR_AUDIT = "docs/audits/pums_inequality_repair_validation.md"
REPAIRED = {"atkinson_1": None, "atkinson_0.5": 7000, "top10_share": 7000}   # measure -> minimum records (None: none)
# Round 62 (docs/audits/leftover_failures_validation.md): Theil T failed again with 8,000 households (log interval,
# .858 for the heavy-tailed income): a confirmed limit, exploratory at any sample size tested.
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
    n_records = len(y)
    for m in core.MEASURES:
        if m not in vals:
            continue
        s = core.sdr_summary(vals[m]); method = "normal"
        ok = VALIDATED[m] and s["se"] > 0
        note = None
        if m in REPAIRED:
            try:
                t = core.transformed_summary(vals[m], core.TRANSFORM[m])
                s = dict(s, lower=t["lower"], upper=t["upper"]); method = core.TRANSFORM[m]
                gate = REPAIRED[m]
                ok = s["se"] > 0 and (gate is None or n_records >= gate)
                if not ok and gate is not None:
                    note = (f"{n_records} records, fewer than the {gate} the Round 60 validation required for this measure; "
                            "exploratory")
            except ValueError:
                note = "transformed interval undefined; exploratory"
        if m in QUANTILES:
            ys = y[positive] if not positive.all() else y
            heap = _heaping(ys, W[positive, 0] if not positive.all() else W[:, 0], QUANTILES[m])
            if heap > HEAPING_LIMIT:
                ok = False
                note = (f"{heap:.0%} of the weight sits exactly at a quantile used (heaped values); replicate SEs are "
                        "unreliable (validation used continuous incomes)")
        if not VALIDATED[m] and m not in REPAIRED:
            note = "failed the Round 56, 60 and 62 coverage validations (also with 8,000 households); exploratory only"
        rows.append(dict(measure=m, **s, interval=method, validated=bool(ok), note=note))
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

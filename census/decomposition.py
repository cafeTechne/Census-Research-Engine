# SPDX-License-Identifier: AGPL-3.0-or-later
"""Oaxaca-Blinder and Fairlie decompositions of a PUMS group gap (Round 79; backlog N56).

Validation: ``docs/audits/decomposition_validation.md`` (criterion ``decomposition_validation_criterion.md``); the
computation is the frozen core :mod:`census.decomposition_core` with SDR replicate-weight variance. "Explained" is
the part of the gap attributable to differences in the covariates' distributions (composition), not a causal effect.
"""
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import decomposition_core as dc

AUDIT = "docs/audits/decomposition_validation.md"
# family -> smallest validated group-B record count, or None (failed: exploratory). Set from the audit.
VALIDATED_FROM = {"O1_totals": 300, "O1_detailed": 1000, "F1_totals": 1000, "F1_detailed": 1000}
# docs/audits/decomposition_validation.json "outcome": O1 totals pass from 300 records in the smaller group;
# O1 detailed (.851 at 300), F1 totals (.853) and F1 detailed (.802) fail only at 300 and pass from 1,000.
ORDERINGS = 100
INTERPRETATION = ("'Explained' is statistical composition (differences in the covariates' distributions), not a "
                  "causal effect; the unexplained part is not a measure of discrimination.")


def _values(sub, expr):
    from . import pums
    x = pums._values(sub, expr)
    return np.asarray(x, float), pums._defined(sub, expr, x)


def pums_decomposition(df: pd.DataFrame, outcome: str, group_a: str, group_b: str, covariates: Sequence[str] = (),
                       categorical: Sequence[str] = (), model: str = "linear", where: Optional[str] = None,
                       weight: str = "person", level: float = .90, orderings: int = ORDERINGS,
                       seed: int = 20281979) -> Dict[str, Any]:
    """Decompose the weighted gap mean_A(outcome) - mean_B(outcome) between two mutually exclusive groups.

    ``group_a``/``group_b``: PUMS conditions (e.g. "RAC1P == 2 and HISP == 1"); records matching both are refused.
    ``covariates``: numeric PUMS columns or expressions; ``categorical``: code columns, each one block of dummies
    (the most common code is the reference; results are normalised so they do not depend on it). ``model``:
    "linear" (Oaxaca-Blinder, twofold with the pooled reference) or "logit" (Fairlie; outcome a 0/1 condition).
    """
    from . import pums
    if model not in ("linear", "logit"):
        raise ValueError("model must be 'linear' (Oaxaca-Blinder) or 'logit' (Fairlie)")
    if not covariates and not categorical:
        raise ValueError("give at least one covariate")
    sub = df.loc[pums._mask(df, where)]
    a = np.asarray(pums._values(sub, group_a), bool); b = np.asarray(pums._values(sub, group_b), bool)
    if (a & b).any():
        raise ValueError("group_a and group_b overlap: the groups must be mutually exclusive")
    keep = a | b
    y, ok = _values(sub, outcome)
    cols, blocks, cat_blocks = [np.ones(len(sub))], {}, []
    for c in covariates:
        v, d = _values(sub, c); ok &= d
        blocks[c] = [len(cols)]; cols.append(v)
    for c in categorical:
        codes = sub[c].to_numpy(object)
        ok &= pd.notna(codes)
        levels = pd.Series(codes[keep & ok]).value_counts().index.tolist()
        if len(levels) < 2:
            raise ValueError(f"categorical {c} has fewer than two levels in the groups")
        blocks[c] = list(range(len(cols), len(cols)+len(levels)-1))
        cols += [(codes == lv).astype(float) for lv in levels[1:]]
        cat_blocks.append(c)
    _, W = pums._weight_matrix(sub, weight)
    ok &= keep & np.isfinite(W).all(axis=1)
    X = np.column_stack(cols)[ok]; y = y[ok]; g = a[ok].astype(int); W = W[ok]
    if model == "logit" and not np.isin(y, (0, 1)).all():
        raise ValueError("the logit (Fairlie) model needs a 0/1 outcome condition, e.g. 'HICOV == 2'")
    n_a, n_b = int(g.sum()), int((1-g).sum())
    if min(n_a, n_b) < 30:
        raise ValueError(f"too few records (A {n_a}, B {n_b}); at least 30 per group")
    kind = "oaxaca" if model == "linear" else "fairlie"
    res = dc.with_replicates(kind, y, X, g, W, blocks, cat_blocks, R=orderings, rng=np.random.default_rng(seed),
                             level=level)
    fam = ("O1" if kind == "oaxaca" else "F1")
    smallest = min(n_a, n_b)
    rows = []
    for name, (est, se, lo, hi) in res.items():
        family = f"{fam}_totals" if ":" not in name else f"{fam}_detailed"
        if name in ("gap", "endowments", "coefficients", "interaction"):
            family = None
        gate = VALIDATED_FROM.get(family) if family else None
        rows.append(dict(component=name, estimate=est, se=se, ci_lower=lo, ci_upper=hi,
                         validated=bool(gate is not None and smallest >= gate)))
    table = pd.DataFrame(rows)
    notes = [INTERPRETATION]
    if kind == "oaxaca":
        notes.append("Threefold components (endowments, coefficients, interaction) and the gap itself are "
                     "descriptive (not judged in validation).")
    return dict(model=model, method="Oaxaca-Blinder (pooled reference)" if kind == "oaxaca" else "Fairlie (logit)",
                table=table, records=dict(group_a=n_a, group_b=n_b), reference_levels={c: None for c in cat_blocks},
                notes=notes, audit=AUDIT, level=level)

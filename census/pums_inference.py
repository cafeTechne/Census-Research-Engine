# SPDX-License-Identifier: AGPL-3.0-or-later
"""Design-based tests and intervals on PUMS data frames (Round 32).

Wraps the frozen procedures in :mod:`census.pums_tests` with PUMS column handling
(``where`` universes, expressions, missing codes, small-sample flags). Validation status
is fixed from ``docs/audits/pums_tests_validation.md`` (criterion d65d034); the
placeholder ``census.pums_tests.VALIDATED`` is not used.

Validated (90% intervals, nominal .10 tests; 8 cells of household clustering, weight
CV and sample size with ACS-style SDR replicate weights):
- independence in r x c tables: first-order Rao-Scott (T1), tables up to 3 x 4
  (q <= 6; larger tables are exploratory). Second-order Rao-Scott also passed; the
  design Wald F failed for 3 x 4 tables. The design-blind Pearson test is far oversized.
- k-group means: design Wald F (M3); two groups: z test (M1).
- differences of proportions, odds ratios, relative risks, differences of means and of
  medians (SDR standard errors, normal intervals).
- one proportion: Korn-Graubard (the Wald interval failed for a rare proportion in a small domain).
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from . import pums, pums_tests as pt

AUDIT = "docs/audits/pums_tests_validation.md"
INDEPENDENCE_MAX_Q = 6
VALIDATED_PROPORTION_METHOD = "korn_graubard"
HEAPING_LIMIT = .02   # share of a group's weight exactly at its median above which median SEs are not trusted


def _frame(df, columns, where, weight):
    keep = pums._mask(df, where)
    sub = df.loc[keep]
    vals = {}
    ok = np.ones(len(sub), bool)
    for name, expr in columns.items():
        if isinstance(expr, str) and expr in sub.columns and not pd.api.types.is_numeric_dtype(sub[expr]):
            x = sub[expr].to_numpy(object)          # a categorical code column kept as is (e.g. PUMA strings)
            ok &= pd.notna(x)
        else:
            x = pums._values(sub, expr)             # numeric column or expression; blanks stay missing
            ok &= pums._defined(sub, expr, x)
        vals[name] = x
    _, W = pums._weight_matrix(sub, weight)
    ok &= np.isfinite(W).all(axis=1)
    return {k: v[ok] for k, v in vals.items()}, W[ok]


def _label(value):
    """PUMS codes read as floats print as integers ('1', not '1.0')."""
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _flags(n, min_n):
    return [f"fewer than {min_n} records ({n}): estimates are unreliable"] if n < min_n else []


def independence_test(df: pd.DataFrame, row: Any, col: Any, weight: str = "person", where: Any = None,
                      min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Rao-Scott test that ``row`` and ``col`` are independent in the weighted population."""
    v, W = _frame(df, {"row": row, "col": col}, where, weight)
    out = pt.independence(v["row"], v["col"], W)
    validated = out["q"] <= INDEPENDENCE_MAX_Q
    rl, cl = out["levels"]
    table = pd.DataFrame([dict(row=_label(r), col=_label(c), share=float(out["shares"][i, j]))
                          for i, r in enumerate(rl) for j, c in enumerate(cl)])
    notes = _flags(out["n"], min_n)
    if not validated:
        notes.append(f"EXPLORATORY: tables larger than 3 x 4 (q = {out['q']} > {INDEPENDENCE_MAX_Q}) were not validated ({AUDIT})")
    notes.append("Pearson X2 ignoring the design is shown only for comparison; it is far too liberal for PUMS.")
    return dict(test="first-order Rao-Scott", statistic=out["T1"]["statistic"], df=out["T1"]["df"],
                p_value=out["T1"]["p"], validated=validated, n=out["n"], q=out["q"],
                design_effect_mean=out["deff_mean"], design_effect_a2=out["deff_a2"], table=table,
                alternatives=dict(second_order_rao_scott=out["T2"], design_wald_F=out["T3"],
                                  pearson_ignoring_design=out["T0"]),
                notes=notes, audit=AUDIT)


def two_by_two(df: pd.DataFrame, exposure: Any, outcome: Any, weight: str = "person", where: Any = None,
               min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Difference of proportions, odds ratio and relative risk of ``outcome`` by ``exposure`` (both true/false)."""
    v, W = _frame(df, {"exposure": exposure, "outcome": outcome}, where, weight)
    e, o = v["exposure"].astype(bool), v["outcome"].astype(bool)
    ratios = pt.two_by_two(e, o, W)
    diff = pt.difference_of_proportions(o.astype(float), e.astype(int), W)
    return dict(difference_of_proportions=diff, odds_ratio=ratios["odds_ratio"],
                relative_risk=ratios["relative_risk"], n=int(len(e)), n_exposed=int(e.sum()),
                validated=True, notes=_flags(min(int(e.sum()), int((~e).sum())), min_n)
                + ["Differences are exposed minus unexposed; ratios compare exposed with unexposed."], audit=AUDIT)


def compare_means(df: pd.DataFrame, var: Any, by: Any, weight: str = "person", where: Any = None,
                  min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Weighted means of ``var`` by ``by``: differences from the first group, z test (2 groups) or design F (3+)."""
    v, W = _frame(df, {"var": var, "by": by}, where, weight)
    out = pt.means_test(v["var"], v["by"], W)
    levels = out["levels"]
    counts = pd.Series(v["by"]).value_counts()
    se = np.sqrt(np.diag(out["cov"]))
    diffs = pd.DataFrame(dict(group=[_label(g) for g in levels[1:]], reference=_label(levels[0]),
                              difference=out["differences"], se=se,
                              lower=out["differences"]-pt.Z90*se, upper=out["differences"]+pt.Z90*se))
    test = out["M1"] if len(levels) == 2 else out["M3"]
    small = [_label(g) for g in levels if counts.get(g, 0) < min_n]
    notes = [f"groups with fewer than {min_n} records: {small}"] if small else []
    return dict(means=dict(zip(map(_label, levels), map(float, out["means"]))), differences=diffs,
                test="z test" if len(levels) == 2 else "design Wald F", p_value=test["p"], statistic=test["statistic"],
                validated=True, notes=notes, audit=AUDIT)


def compare_medians(df: pd.DataFrame, var: Any, by: Any, weight: str = "person", where: Any = None,
                    min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """Difference of weighted medians of ``var`` between the two groups of ``by`` (second minus first)."""
    v, W = _frame(df, {"var": var, "by": by}, where, weight)
    levels = sorted(pd.unique(v["by"]))
    if len(levels) != 2:
        raise ValueError("compare_medians needs exactly two groups")
    codes = (v["by"] == levels[1]).astype(int)
    out = pt.difference_of_medians(v["var"], codes, W)
    counts = [int((codes == k).sum()) for k in (0, 1)]
    notes = _flags(min(counts), min_n) + ["Weighted medians (no bracket interpolation); SDR standard error."]
    # Validation used continuous values. Reported dollar amounts are heaped (round numbers), so
    # replicate medians can coincide and the SDR SE collapses toward 0: label such results.
    shares = []
    for k in (0, 1):
        x, w = v["var"][codes == k], W[codes == k, 0]
        shares.append(float(w[x == _median(x, w)].sum()/w.sum()))
    heap = max(shares)
    validated = out["se"] > 0 and heap <= HEAPING_LIMIT
    if not validated:
        notes.append(f"EXPLORATORY: {heap:.0%} of a group's weight sits exactly at its median (heaped values); "
                     "replicate SEs of medians are unreliable here (validation used continuous values). "
                     "Use bracket-interpolated medians (pums_tabulate statistic='median' with bins) or compare means.")
    return dict(groups=[_label(g) for g in levels], difference=out, validated=validated, heaping_share=heap,
                notes=notes, audit=AUDIT)


def _median(x, w):
    return float(pums.weighted_median(np.asarray(x, float), np.asarray(w, float))[0])


def proportion_interval(df: pd.DataFrame, var: Any, weight: str = "person", where: Any = None,
                        method: str = VALIDATED_PROPORTION_METHOD, min_n: int = pums.MIN_UNWEIGHTED_N) -> Dict[str, Any]:
    """One weighted proportion with a Korn-Graubard (default, validated) or Wald interval."""
    v, W = _frame(df, {"var": var}, where, weight)
    out = pt.proportion_interval(v["var"].astype(float), W, method)
    validated = method == VALIDATED_PROPORTION_METHOD
    notes = _flags(len(v["var"]), min_n)
    if not validated:
        notes.append(f"EXPLORATORY: the Wald interval under-covered for rare proportions in small domains ({AUDIT})")
    return dict(**out, n=int(len(v["var"])), validated=validated, notes=notes, audit=AUDIT)

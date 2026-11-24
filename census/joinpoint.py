# SPDX-License-Identifier: AGPL-3.0-or-later
"""Joinpoint regression and rate ratios of age-adjusted rates (Round 77; backlog N54).

Validation: ``docs/audits/joinpoint_validation.md`` (criterion ``joinpoint_validation_criterion.md``); computation is
the frozen core :mod:`census.joinpoint_core`. Joinpoint describes trend changes without a pre-set date; for a known
policy date use ``interrupted_series``. Overlapping ACS five-year releases are not annual observations and are refused.
"""
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import joinpoint_core as jc

AUDIT = "docs/audits/joinpoint_validation.md"
REPAIRS_AUDIT = "docs/audits/repairs109_validation.md"
# Set from the audit (docs/audits/joinpoint_validation.json "passed").
VALIDATED = {"J1": True, "J2": False, "J3": False, "J2b": False, "J3b": False, "R1": True, "R1b": True}
AAPC_BOOTSTRAP_T_VALIDATED = True
AAPC_MIN_EVENTS = 200
# J1: false-joinpoint rate .012-.023 (<= .10). APC/AAPC intervals failed: t given the true k .51-.91, AAPC .75-.92,
# empirical quantile with selection .02-.88 (joinpoint location uncertainty). R1 Tiwari .900-.921, R1b .887-.900.
MIN_POINTS, MIN_EVENTS = 15, 50
SEED = 20281777
NOT_POLICY = ("Joinpoint describes where trends changed without a pre-set date; for a known policy date use "
              "interrupted_series.")


def joinpoint(years: Sequence[int], counts: Optional[Sequence[float]] = None, population: Optional[Sequence[float]] = None,
              rates: Optional[Sequence[float]] = None, se: Optional[Sequence[float]] = None, max_joinpoints: int = 3,
              permutations: int = 4999, bootstrap: int = 999, level: float = .90, alpha: float = .05,
              product: str = "annual", seed: int = SEED) -> Dict[str, Any]:
    """Log-linear joinpoint model of an annual rate series.

    Give ``counts`` and ``population`` (Poisson weights; the rate is counts / population), or ``rates`` with their
    ``se`` (weights 1 / (se / rate)^2). Missing values (e.g. WONDER-suppressed years) are refused: complete years
    only. ``product``: "annual" (default; vital statistics, ACS 1-year) — "5-year" is refused.
    Returns the selected number of joinpoints (Kim et al. permutation tests), joinpoint years, per-segment APCs and
    the whole-period AAPC with intervals, and validation flags.
    """
    if str(product).lower().replace("_", "-") in ("5-year", "acs5", "five-year"):
        raise ValueError("overlapping ACS five-year releases are not annual observations; joinpoint is refused "
                         "(use trend_test with non-overlapping releases)")
    x = np.asarray(years, float)
    if len(x) < 5 or np.any(np.diff(x) <= 0) or not np.allclose(x, np.round(x)):
        raise ValueError("years must be increasing integers (at least 5 points)")
    notes = [NOT_POLICY]
    if counts is not None:
        if population is None or rates is not None:
            raise ValueError("give counts with population, or rates with se")
        d = np.asarray(counts, float); n = np.asarray(population, float)
        if np.isnan(d).any() or np.isnan(n).any():
            raise ValueError("missing counts (e.g. suppressed years) are refused: complete years only")
        if (d <= 0).any():
            raise ValueError("every year needs a positive count (the log rate is undefined at zero)")
        y, w = np.log(d/n), d
        events = float(d.min())
    else:
        if rates is None or se is None:
            raise ValueError("give counts with population, or rates with se")
        r = np.asarray(rates, float); s = np.asarray(se, float)
        if np.isnan(r).any() or np.isnan(s).any() or (r <= 0).any() or (s <= 0).any():
            raise ValueError("rates and SEs must be positive and complete")
        y, w = np.log(r), (r/s)**2
        events = float(w.min())  # Poisson-equivalent count
    if len(np.unique(np.diff(x))) > 1:
        notes.append("Years are not evenly spaced (e.g. a skipped year); slopes are per calendar year.")
    K = min(int(max_joinpoints), jc.max_feasible(len(x)))
    rng = np.random.default_rng(seed)
    k, pvals = jc.select_k(x, y, w, K, alpha=alpha, B=permutations, rng=rng)
    f = jc.fit_with_residuals(x, y, w, k)
    a = jc.apc_intervals(f, level)
    g = jc.aapc_interval(f, level)
    b = jc.bootstrap_intervals(f, w, B=bootstrap, level=level, rng=rng)
    cuts = [x[0], *x[f["cfg"]], x[-1]]
    seg = pd.DataFrame(dict(start=[int(v) for v in cuts[:-1]], end=[int(v) for v in cuts[1:]], apc=a["apc"],
                            ci_lower=a["lower"], ci_upper=a["upper"]))
    in_range = len(x) >= MIN_POINTS and events >= MIN_EVENTS
    if not in_range:
        notes.append(f"Outside the validated range ({MIN_POINTS}+ points and {MIN_EVENTS}+ events per year): "
                     "exploratory.")
    use_eq = bool(VALIDATED["J2b"])
    if not (VALIDATED["J2"] or VALIDATED["J2b"]):
        notes.append("APC and AAPC intervals failed validation (they under-cover when joinpoints are estimated): "
                     "report them as exploratory; the number of joinpoints is validated.")
    if use_eq:
        seg.loc[seg.index[-1], ["ci_lower", "ci_upper"]] = [b["last_apc_lower"], b["last_apc_upper"]]
        notes.append("The last segment's APC and the AAPC use empirical-quantile (bootstrap) intervals, which "
                     "include joinpoint selection and location uncertainty.")
    aapc = dict(aapc=g["aapc"], ci_lower=b["aapc_lower"] if VALIDATED["J3b"] else g["lower"],
                ci_upper=b["aapc_upper"] if VALIDATED["J3b"] else g["upper"])
    from . import repairs109_core as r109
    aapc_bt = r109.joinpoint_aapc_bootstrap_t(x, y, w, k, B=min(int(bootstrap), 200), level=level, rng=rng)
    aapc_bt["validated"] = bool(AAPC_BOOTSTRAP_T_VALIDATED and len(x) >= MIN_POINTS and events >= AAPC_MIN_EVENTS and k <= 1)
    aapc_bt["audit"] = REPAIRS_AUDIT
    return dict(joinpoints=[int(v) for v in x[f["cfg"]]], n_joinpoints=k, max_joinpoints=K, permutation_p=pvals,
                segments=seg, aapc=aapc, aapc_bootstrap_t=aapc_bt,
                validated=dict(selection=bool(VALIDATED["J1"]) and in_range,
                               apc=bool(VALIDATED["J2b"] or VALIDATED["J2"]) and in_range,
                               aapc=bool(VALIDATED["J3b"] or VALIDATED["J3"]) and in_range),
                interval_basis=("empirical quantile" if use_eq else "t, conditional on the selected joinpoints"),
                level=level, notes=notes, audit=AUDIT)


def age_adjusted_rate_ratio(cases1: Sequence[float], population1: Sequence[float], cases2: Sequence[float],
                            population2: Sequence[float], standard: Sequence[float], level: float = .90) -> Dict[str, Any]:
    """Ratio of two directly age-adjusted rates with the Tiwari et al. (2006) interval (R1) and the log-delta
    interval (R1b). ``standard``: standard population weights per age band (normalised)."""
    arrs = [np.asarray(a, float) for a in (cases1, population1, cases2, population2, standard)]
    if len({len(a) for a in arrs}) != 1:
        raise ValueError("all inputs need one value per age band")
    if any(np.isnan(a).any() for a in arrs) or (arrs[1] <= 0).any() or (arrs[3] <= 0).any():
        raise ValueError("complete counts and positive populations are required (suppressed bands are refused)")
    r = jc.tiwari_ratio(*arrs, level=level)
    use = "tiwari" if VALIDATED["R1"] else ("delta" if VALIDATED["R1b"] else "tiwari")
    lo, hi = (r["tiwari_lower"], r["tiwari_upper"]) if use == "tiwari" else (r["delta_lower"], r["delta_upper"])
    return dict(ratio=float(r["ratio"]), ci_lower=float(lo), ci_upper=float(hi), method=use,
                rate1=float(r["rate1"]), rate2=float(r["rate2"]), tiwari=(float(r["tiwari_lower"]), float(r["tiwari_upper"])),
                delta=(float(r["delta_lower"]), float(r["delta_upper"])),
                validated=bool(VALIDATED["R1"] if use == "tiwari" else VALIDATED["R1b"]), level=level, audit=AUDIT)

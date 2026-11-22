# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staggered-adoption difference-in-differences and synthetic control (Round 78; backlog N55).

Validation: ``docs/audits/policy_validation.md`` (criterion ``policy_validation_criterion.md``); computation is the
frozen core :mod:`census.policy_core`.

- Sun and Abraham (2021) interaction-weighted event study (never-treated controls, CR1 state clusters):
  **validated** (overall ATT and every event time .881-.899 over 51 units, 12 or 18 annual periods, AR(1) errors
  .3/.7, ACS-like sampling error). The default.
- Callaway and Sant'Anna (2021) with never-treated controls and the multiplier bootstrap: **validated only with the
  ACS sampling variance added** (``se`` column; .882-.906). Without it the bootstrap intervals under-covered
  (.848-.868) and the result is exploratory. Uniform bands under-covered (.76-.81) and are descriptive.
- Synthetic control (Abadie et al. 2010): **failed** (placebo test size .12-.19 at .10; conformal intervals .73-.86
  with 9 pre-periods, though .87-.95 with 15). Library only, exploratory.
"""
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from scipy import stats

from . import policy_core as pc

AUDIT = "docs/audits/policy_validation.md"
VALIDATED = {"sun_abraham": True, "callaway_santanna": False, "callaway_santanna_acs": True, "synthetic_control": False}
MIN_UNITS = 30  # the simulation used 51 units; fewer is outside the validated range
PRETREND_NOTE = "Pre-trend check: Holm-adjusted t tests of the pre-treatment event-time effects (Sun-Abraham)."


def _panel(frame, outcome, first_treated, period, unit, se):
    need = [unit, period, outcome, first_treated]+([se] if se else [])
    miss = [c for c in need if c not in frame.columns]
    if miss:
        raise ValueError(f"columns not in the frame: {miss}")
    f = frame[need].copy()
    f[unit] = f[unit].astype(str)
    if f[[unit, period, outcome]].isna().any().any() or (se and f[se].isna().any()):
        raise ValueError("the panel has missing outcome values; staggered DiD needs a balanced panel")
    if f.duplicated([unit, period]).any():
        raise ValueError("each unit needs one row per period")
    periods = sorted(f[period].astype(int).unique())
    Y = f.pivot(index=unit, columns=period, values=outcome)
    if Y.isna().any().any():
        raise ValueError("unbalanced panel: every unit needs every period")
    S = f.pivot(index=unit, columns=period, values=se).to_numpy(float) if se else None
    ft = f.groupby(unit)[first_treated].first().reindex(Y.index)
    return Y, S, ft, periods


def staggered_did(frame: pd.DataFrame, outcome: str, first_treated: str, period: str = "Year", unit: str = "GEOID",
                  se: Optional[str] = None, method: str = "sun_abraham", product: str = "1-year",
                  level: float = .90, seed: int = 20281878) -> Dict[str, Any]:
    """Event-study and overall ATT for staggered adoption.

    ``first_treated``: the first treated period (year) per unit; missing, 0 or infinite = never treated.
    ``method``: "sun_abraham" (default, validated) or "callaway_santanna" (validated with ``se``, the outcome's
    sampling SE column, whose variance is added in quadrature). ``product``: "1-year" (annual ACS or another annual
    source); five-year releases are refused (they overlap). ACS 1-year 2020 values are refused (no standard release).
    Event times count observed periods. Units treated in the first observed period have no pre-period and are dropped.
    """
    if method not in ("sun_abraham", "callaway_santanna"):
        raise ValueError("method must be 'sun_abraham' or 'callaway_santanna'")
    if str(product).lower().replace("_", "-") not in ("1-year", "annual"):
        raise ValueError("staggered designs need annual, non-overlapping periods (ACS 1-year or another annual "
                         "source); overlapping five-year releases are refused")
    Y, S, ft, periods = _panel(frame, outcome, first_treated, period, unit, se)
    notes = []
    if str(product) == "1-year" and 2020 in periods:
        raise ValueError("ACS 1-year 2020 values are refused: there is no standard 2020 1-year release")
    if len(periods) != periods[-1]-periods[0]+1:
        notes.append("Periods are not consecutive years (e.g. 2020 skipped); event times count observed periods.")
    idx = {p: i for i, p in enumerate(periods)}
    G = np.full(len(Y), np.inf)
    for i, v in enumerate(ft.to_numpy()):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v == 0 or v == np.inf:
            continue
        later = [p for p in periods if p >= int(v)]
        if not later:
            continue  # treated after the panel ends: never treated within it
        G[i] = idx[later[0]]
        if later[0] != int(v):
            notes.append(f"Unit {Y.index[i]}: first treated {int(v)} is not an observed period; mapped to {later[0]}.")
    early = G == 0
    if early.any():
        notes.append(f"{int(early.sum())} unit(s) treated in the first observed period have no pre-period and were dropped.")
    keep = ~early
    Yk, Gk = Y.to_numpy(float)[keep], G[keep]
    Sk = S[keep] if S is not None else None
    if not np.isfinite(Gk).any() or np.isfinite(Gk).all():
        raise ValueError("staggered DiD needs treated and never-treated units")
    n_units = int(keep.sum())
    sa = pc.sun_abraham(Yk, Gk, level=level)
    if method == "sun_abraham":
        res = sa
        validated = VALIDATED["sun_abraham"]
        basis = "Sun-Abraham interaction-weighted, CR1 state clusters, t(N - 1)"
    else:
        cs = pc.cs_estimate(Yk, Gk, B=999, level=level, rng=np.random.default_rng(seed), se_y=Sk)
        use_r = Sk is not None
        res = dict(event=[dict(r, lower=r["lower_r"], upper=r["upper_r"], se=r["se_r"]) if use_r else r for r in cs["event"]],
                   overall=dict(cs["overall"], lower=cs["overall"]["lower_r"], upper=cs["overall"]["upper_r"], se=cs["overall"]["se_r"])
                   if use_r else cs["overall"], band_crit=cs["band_crit"])
        validated = VALIDATED["callaway_santanna_acs"] if use_r else VALIDATED["callaway_santanna"]
        basis = ("Callaway-Sant'Anna multiplier bootstrap" + (" plus ACS sampling variance" if use_r else ""))
        if not use_r:
            notes.append("Callaway-Sant'Anna without the se column under-covered (.848-.868): exploratory; give se or "
                         "use method='sun_abraham'.")
        notes.append("Uniform event-study bands under-covered (.76-.81) in validation: descriptive only.")
    if n_units < MIN_UNITS:
        validated = False
        notes.append(f"{n_units} units: validation used 51 (states + DC); below {MIN_UNITS} the result is exploratory.")
    pre = [r for r in sa["event"] if int(r["key"]) < -1]
    pre_p = [2*stats.t.sf(abs(r["estimate"]/r["se"]), n_units-1) for r in pre if r["se"] > 0]
    holm = min((min(1.0, p*(len(pre_p)-i)) for i, p in enumerate(sorted(pre_p))), default=np.nan)
    to_year = lambda e: int(e)  # noqa: E731
    event = pd.DataFrame([dict(event_time=to_year(r["key"]), estimate=r["estimate"], se=r["se"], ci_lower=r["lower"],
                               ci_upper=r["upper"]) for r in res["event"]]).sort_values("event_time")
    o = res["overall"]
    notes.append(PRETREND_NOTE)
    return dict(method=method, overall=dict(estimate=o["estimate"], se=o["se"], ci_lower=o["lower"], ci_upper=o["upper"]),
                event_study=event, pretrend_min_holm_p=float(holm) if np.isfinite(holm) else None,
                validated=bool(validated), basis=basis, units=n_units, periods=periods,
                cohorts={str(periods[int(g)]): int((Gk == g).sum()) for g in sorted(set(Gk[np.isfinite(Gk)]))},
                never_treated=int((~np.isfinite(Gk)).sum()), level=level, notes=notes, audit=AUDIT)


def synthetic_control(frame: pd.DataFrame, outcome: str, treated_unit: str, treatment_period: int,
                      period: str = "Year", unit: str = "GEOID", level: float = .90) -> Dict[str, Any]:
    """Synthetic control for one treated unit (library only; **exploratory**: failed validation, see AUDIT).

    Returns donor weights, per-period gaps, the placebo-in-space p-value of the post/pre RMSPE ratio, conformal
    per-period intervals and the pre-fit ratio (treated pre-RMSPE / median placebo pre-RMSPE; above 2 = poor fit).
    """
    f = frame[[unit, period, outcome]].copy(); f[unit] = f[unit].astype(str)
    Y = f.pivot(index=unit, columns=period, values=outcome)
    if Y.isna().any().any():
        raise ValueError("unbalanced panel")
    periods = list(Y.columns)
    if str(treated_unit) not in Y.index or treatment_period not in periods:
        raise ValueError("treated_unit and treatment_period must be in the panel")
    order = [str(treated_unit)]+[u for u in Y.index if u != str(treated_unit)]
    M = Y.loc[order].to_numpy(float)
    T0 = periods.index(treatment_period)
    if T0 < 2:
        raise ValueError("synthetic control needs pre-treatment periods")
    pt = pc.placebo_test(M, 0, T0)
    gap = pt["main"]["gap"]
    sd = max(float(np.std(gap[:T0], ddof=1)), 1e-9)
    rows = []
    for t in range(T0, len(periods)):
        lo, hi = pc.conformal_interval(M, 0, T0, t, np.linspace(gap[t]-6*sd, gap[t]+6*sd, 241), alpha=1-level)
        rows.append(dict(period=periods[t], gap=float(gap[t]), ci_lower=lo, ci_upper=hi))
    weights = {order[1:][j]: float(w) for j, w in enumerate(pt["main"]["weights"]) if w > 1e-6}
    return dict(weights=weights, gaps=pd.DataFrame(rows), placebo_p=pt["p"], prefit_ratio=pt["prefit_ratio"],
                poor_prefit=pt["prefit_ratio"] > 2, validated=False,
                notes=["Synthetic control failed validation (placebo size .12-.19 at .10; conformal intervals "
                       "under-covered with 9 pre-periods): exploratory only.", f"See {AUDIT}."], audit=AUDIT)

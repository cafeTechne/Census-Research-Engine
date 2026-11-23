# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 94: WHO health inequality monitoring (backlog N71; WHO, *Handbook on Health Inequality Monitoring*, 2013).

Validation (``docs/audits/inequality_monitoring_validation.md``; criterion tag ``criterion-r94``), ACS group rates
with replicate intervals, 4-8 groups, smallest-group rate CV up to .50:
- passed: population attributable risk against a declared reference or the data-selected best group (par, par_pct;
  .884-.987, the data-selected version conservative), the slope index of inequality (.882-) and the change in
  mdm_w, mdb_w, par and sii between two independent releases (.879-.908);
- failed: the mean differences from the overall mean (mdm) and from the best or reference group (mdb). They covered
  .82-.92 when group rates are far apart but fell to .39-.85 when the true spread is small next to the sampling
  error (absolute values of noisy differences are biased upward): exploratory.
"""
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

from . import inequality_monitoring_core as im
from .disparity import _keys, _rep_mats

AUDIT = "docs/audits/inequality_monitoring_validation.md"
VALIDATED = {"mdm_u": False, "mdm_w": False, "mdb_u": False, "mdb_w": False, "par": True, "par_pct": True,
             "sii": True}
CHANGE_VALIDATED = ("mdm_w", "mdb_w", "par", "sii")
MAX_CV = .50
MAX_GROUPS = 8
MD_NOTE = ("Mean differences (mdm, mdb) are biased upward when group rates are close relative to their sampling "
           "error (validation coverage as low as .39): exploratory; report them beside par and sii.")


def _intervals(data, groups, populations, replicates, reference, level):
    est = data[groups].to_numpy(float); pops = data[populations].to_numpy(float)
    mats = _rep_mats(data, replicates, groups+populations)
    absent = [g for g in groups if g not in mats]
    if absent:
        raise ValueError(f"group rates need replicates; none for {absent}")
    r_reps = np.stack([mats[g] for g in groups], 1)
    p_reps = np.stack([mats[p] for p in populations], 1) if all(p in mats for p in populations) else None
    ref = "best" if reference == "best" else groups.index(reference)
    iv = im.replicate_intervals(est, pops, r_reps, p_reps, ref, level)
    se_r = np.sqrt(im.REP_FACTOR*((r_reps-est[:, :, None])**2).sum(2))
    with np.errstate(divide="ignore", invalid="ignore"):
        cv = np.max(np.where(est > 0, se_r/est, np.inf), 1)
    best = np.array(groups)[np.argmin(est, 1)]
    return iv, cv, best


def monitoring_measures(frame: pd.DataFrame, groups: Sequence[str], populations: Sequence[str],
                        replicates: pd.DataFrame, reference: str = "best", level: float = .90,
                        compare_years: Optional[Sequence[int]] = None) -> pd.DataFrame:
    """WHO measures per area (rows: area, measure). ``groups``: rate columns of an adverse outcome (lower is better),
    ordered from most to least advantaged for sii; ``reference``: a group column or "best" (lowest rate, chosen in
    each replicate too). ``compare_years=[y1, y2]`` (non-overlapping releases in a Year column): the change y2 - y1."""
    groups, populations = list(groups), list(populations)
    if len(groups) < 2 or len(groups) != len(populations):
        raise ValueError("give at least two groups and one population column per group")
    if reference != "best" and reference not in groups:
        raise ValueError("reference must be one of the groups or 'best'")
    data = frame.dropna(subset=groups+populations).reset_index(drop=True)
    if (data[populations].to_numpy(float) <= 0).any():
        raise ValueError("group populations must be positive")
    if compare_years is not None:
        return _change(data, groups, populations, replicates, reference, level, compare_years)
    iv, cv, best = _intervals(data, groups, populations, replicates, reference, level)
    rows = []
    for i in range(len(data)):
        base = {k: data.at[i, k] for k in _keys(data)}
        ok_range = bool(cv[i] <= MAX_CV) and len(groups) <= MAX_GROUPS
        for m in im.MEASURES:
            r = iv[m]
            valid = VALIDATED[m] and ok_range and bool(np.isfinite(r["se"][i]))
            notes = [] if valid else ([MD_NOTE] if m.startswith("md") else
                                      [f"Outside the validated range (largest group CV {cv[i]:.2f}; up to {MAX_CV} and "
                                       f"{MAX_GROUPS} groups validated)."])
            if m == "sii":
                notes.append("SII orders the groups as given (first = most advantaged); meaningless for unordered groups.")
            rows.append({**base, "measure": m, "reference": best[i] if reference == "best" else reference,
                         "estimate": float(r["estimate"][i]), "se": float(r["se"][i]),
                         "se_scale": "log" if m in im.POSITIVE else "identity",
                         "ci_lower": float(r["lower"][i]), "ci_upper": float(r["upper"][i]),
                         "interval_touches_zero": bool(r["lower"][i] <= 1e-12) if m in im.POSITIVE else None,
                         "validated": valid, "max_group_cv": float(cv[i]), "notes": notes})
    out = pd.DataFrame(rows)
    out.attrs.update(audit=AUDIT, level=level, reference=reference)
    return out


def _change(data, groups, populations, replicates, reference, level, years):
    if "Year" not in data.columns or len(years) != 2:
        raise ValueError("compare_years needs two years and a Year column")
    y1, y2 = map(int, years)
    if abs(y2-y1) < 5:
        raise ValueError("compare_years must be non-overlapping five-year releases (at least 5 years apart)")
    parts = {}
    for y in (y1, y2):
        d = data[data.Year.astype(int) == y].reset_index(drop=True)
        if d.empty:
            raise ValueError(f"no rows for Year {y}")
        reps = replicates[replicates.Year.astype(int) == y] if "Year" in replicates.columns else replicates
        parts[y] = (d, *_intervals(d, groups, populations, reps, reference, level))
    a, b = parts[y1], parts[y2]
    common = sorted(set(a[0].GEOID.astype(str)) & set(b[0].GEOID.astype(str)))
    ia = [list(a[0].GEOID.astype(str)).index(g) for g in common]; ib = [list(b[0].GEOID.astype(str)).index(g) for g in common]
    pick = lambda iv, idx: {m: {k: np.asarray(v)[idx] for k, v in iv[m].items()} for m in iv}  # noqa: E731
    d = im.change(pick(a[1], ia), pick(b[1], ib), level)
    rows = []
    for k, g in enumerate(common):
        ok = bool(max(a[2][ia[k]], b[2][ib[k]]) <= .30)
        for m in im.MEASURES:
            valid = m in CHANGE_VALIDATED and ok and (reference != "best" or m in ("par", "sii", "mdm_w"))
            rows.append({"GEOID": g, "measure": m, "from_year": y1, "to_year": y2, "change": float(d[m]["estimate"][k]),
                         "se": float(d[m]["se"][k]), "ci_lower": float(d[m]["lower"][k]),
                         "ci_upper": float(d[m]["upper"][k]), "validated": valid,
                         "notes": [] if valid else ["Exploratory: change validated for mdm_w, mdb_w (declared reference), "
                                                    "par and sii with group CVs up to .30."]})
    out = pd.DataFrame(rows)
    out.attrs.update(audit=AUDIT, level=level, reference=reference)
    return out


def double_disaggregation(frame: pd.DataFrame, cells: Mapping[str, Mapping[str, str]], max_cv: float = .30
                          ) -> pd.DataFrame:
    """A two-stratifier table (WHO chapter 5): ``cells = {row_label: {column_label: estimate_column}}``; each
    estimate column needs ``<col>_se`` or ``<col>_moe``. Returns one row per area and cell with the estimate, SE,
    CV and a reliability flag (CV above ``max_cv`` = unreliable)."""
    rows = []
    for _, r in frame.iterrows():
        for a, sub in cells.items():
            for b, col in sub.items():
                se = r[f"{col}_se"] if f"{col}_se" in frame else (r[f"{col}_moe"]/1.645 if f"{col}_moe" in frame else None)
                if se is None:
                    raise ValueError(f"{col} needs {col}_se or {col}_moe")
                est = float(r[col]); cv = float(se)/est if est else np.inf
                rows.append({"GEOID": r["GEOID"], "stratifier_1": a, "stratifier_2": b, "estimate": est, "se": float(se),
                             "cv": cv, "reliable": bool(cv <= max_cv)})
    return pd.DataFrame(rows)


def priority_quadrants(table: pd.DataFrame, level: str, inequality: str, benchmark: Optional[float] = None,
                       higher_is_worse: bool = True) -> pd.DataFrame:
    """WHO four-quadrant view (chapter 4.7): each row (area) classified by its level against ``benchmark`` (default:
    median) and its inequality against the median inequality. Needs ``<col>_lower``/``<col>_upper`` columns for
    both; a quadrant is "uncertain" when an interval spans the cut-off."""
    t = table.copy()
    lb = benchmark if benchmark is not None else float(t[level].median())
    ib = float(t[inequality].median())

    def side(col, cut, worse_high=True):
        lo, hi = t[f"{col}_lower"], t[f"{col}_upper"]
        worse = (lo > cut) if worse_high else (hi < cut)
        better = (hi < cut) if worse_high else (lo > cut)
        return np.where(worse, "worse", np.where(better, "better", "uncertain"))
    t["level_side"] = side(level, lb, higher_is_worse)
    t["inequality_side"] = side(inequality, ib, True)
    t["priority"] = np.where((t.level_side == "worse") & (t.inequality_side == "worse"), "high: worse level and larger inequality",
                    np.where((t.level_side == "uncertain") | (t.inequality_side == "uncertain"), "uncertain", "lower"))
    t.attrs.update(level_cutoff=lb, inequality_cutoff=ib)
    return t

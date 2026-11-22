# SPDX-License-Identifier: AGPL-3.0-or-later
"""Between-group disparity measures and Kitagawa decomposition (Round 76; backlog N53).

Validation: ``docs/audits/disparity_validation.md`` (criterion ``disparity_validation_criterion.md``). Computation
is the frozen core :mod:`census.disparity_core`; this module adds input handling, the validated ranges and notes.

Validated (90% coverage >= .86 in every cell):
- ACS replicate rates: rd and idisp up to a largest group-rate CV of .50 (the simulated maximum); log_rr, bgv, theil
  and mld up to .30 (they under-covered at .50: log_rr .65-.66, mld .50-.65, bgv/theil .82-.84).
- Counts with known populations (Poisson): rd and log_rr (delta method) with at least 20 events per group. The
  bootstrap index measures (idisp, bgv, theil, mld) failed (as low as .07 at 20 expected events) and are exploratory.
- Kitagawa: every component, ACS stratum-rate CV up to .50 and counts with a mean of 20+ events per stratum.
- Two to six groups (the simulated range); more groups are exploratory.
"""
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import disparity_core as dc

AUDIT = "docs/audits/disparity_validation.md"
MEASURES = dc.GROUP_MEASURES+dc.INDEX_MEASURES
ACS_MAX_CV = {"rd": .50, "idisp": .50, "log_rr": .30, "bgv": .30, "theil": .30, "mld": .30}
COUNT_VALIDATED = ("rd", "log_rr")
MIN_COUNT = 20
MAX_GROUPS = 6
KITAGAWA_ACS_MAX_CV = .50
KITAGAWA_MIN_MEAN_COUNT = 20
KITAGAWA_PARTS = ("crude_difference", "rate_effect", "composition_effect")
UNIVERSE_NOTE = ("Declared groups are taken as mutually exclusive; shares for bgv, theil and mld are relative to "
                 "the declared groups only.")
BOOT_SEED = 20281676


def _p(est, se, null=0.0):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 2*stats.norm.sf(np.abs((est-null)/se))


def _keys(frame):
    return ["GEOID"]+(["Year"] if "Year" in frame.columns else [])


def _rep_mats(frame, replicates, cols):
    """Replicate matrices (n, 80) per column, NaN where an area's replicates are missing or not finite (never
    filled: those areas get an undefined interval). Columns without any replicate rows are absent."""
    from .replicate import REPLICATE_COLUMNS
    keys = _keys(frame) if "Year" in replicates.columns else ["GEOID"]
    idx = pd.MultiIndex.from_frame(frame[keys].astype({"GEOID": str})) if len(keys) > 1 else \
        pd.Index(frame["GEOID"].astype(str))
    mats = {}
    for v in cols:
        sub = replicates[replicates["variable"] == v]
        if len(sub):
            sub = sub.assign(GEOID=sub["GEOID"].astype(str)).set_index(keys)
            mats[v] = sub[REPLICATE_COLUMNS].reindex(idx).to_numpy(float)
    return mats


def disparity_measures(frame: pd.DataFrame, groups: Sequence[str], reference: str, populations: Sequence[str],
                       replicates: Optional[pd.DataFrame] = None, counts: bool = False, level: float = .90,
                       omitted_groups: Optional[Sequence[str]] = None, total: Optional[str] = None,
                       bootstrap: int = 500, seed: int = BOOT_SEED) -> pd.DataFrame:
    """Between-group disparity measures per area (one row per area, measure and contrast group).

    ``groups``: rate columns (ACS; with ``replicates``) or event-count columns (``counts=True``, Poisson with known
    ``populations``), one per mutually exclusive group; ``reference`` is one of them, declared in advance.
    ``populations``: the matching group population columns (shares for bgv/theil/mld; denominators for counts).
    ``omitted_groups``: names of groups outside the declared set (reported in the notes). ``total``: optional
    universe population column; the share of it the declared groups cover is reported.
    Returns columns GEOID[, Year], measure, group, estimate, se, se_scale, ci_lower, ci_upper, p_value (rd/log_rr
    against zero), validated, basis, max_group_cv / min_group_count, notes.
    """
    groups, populations = list(groups), list(populations)
    if len(groups) < 2 or len(set(groups)) != len(groups):
        raise ValueError("groups must name at least two distinct columns")
    if len(populations) != len(groups):
        raise ValueError("populations must list one population column per group, in the same order")
    if reference not in groups:
        raise ValueError(f"reference {reference!r} must be one of the groups")
    if not 0 < level < 1:
        raise ValueError("level must be between zero and one")
    missing = [c for c in groups+populations+([total] if total else []) if c not in frame.columns]
    if missing:
        raise ValueError(f"columns not in the frame: {missing}")
    data = frame.dropna(subset=groups+populations).reset_index(drop=True)
    ref = groups.index(reference)
    G = len(groups)
    est = data[groups].to_numpy(float); pops = data[populations].to_numpy(float)
    if (pops <= 0).any():
        raise ValueError("group populations must be positive")
    notes = [UNIVERSE_NOTE]
    if omitted_groups:
        notes.append("Groups outside the declared set (omitted): "+", ".join(map(str, omitted_groups))+".")
    if G > MAX_GROUPS:
        notes.append(f"{G} groups: validation covered 2-{MAX_GROUPS}; results are exploratory.")
    if counts:
        if (est < 0).any() or not np.allclose(est, np.round(est)):
            raise ValueError("counts=True needs non-negative integer event counts")
        res = dc.poisson_intervals(est, pops, ref, level=level, B=bootstrap, rng=np.random.default_rng(seed))
        gate = est.min(axis=1)
        basis = {m: ("poisson_delta" if m in dc.GROUP_MEASURES else "poisson_bootstrap") for m in MEASURES}
        ok = {m: (m in COUNT_VALIDATED) & (gate >= MIN_COUNT) & (G <= MAX_GROUPS) for m in MEASURES}
        gate_col = "min_group_count"
        notes.append("Count measures: rates are events / population with populations treated as known.")
    else:
        if replicates is None:
            raise ValueError("ACS group rates need replicates (or use counts=True for event counts)")
        mats = _rep_mats(data, replicates, groups+populations)
        absent = [g for g in groups if g not in mats]
        if absent:
            raise ValueError(f"group rates need replicates; none for {absent}")
        r_reps = np.stack([mats[g] for g in groups], axis=1)
        if all(p in mats for p in populations):
            p_reps = np.stack([mats[p] for p in populations], axis=1)
        else:
            p_reps = None
            notes.append("Group populations had no replicates: shares are held fixed in the replicate refits.")
        res = dc.replicate_intervals(est, pops, r_reps, p_reps, ref, level=level)
        se_r = np.sqrt(dc.REP_FACTOR*((r_reps-est[:, :, None])**2).sum(axis=2))
        with np.errstate(divide="ignore", invalid="ignore"):
            gate = np.max(np.where(est > 0, se_r/est, np.inf), axis=1)  # NaN (missing replicates) stays NaN: not validated
        basis = {m: "replicate" for m in MEASURES}
        ok = {m: (gate <= ACS_MAX_CV[m]) & (G <= MAX_GROUPS) for m in MEASURES}
        gate_col = "max_group_cv"
    if total:
        cover = pops.sum(axis=1)/data[total].to_numpy(float)
    rows: List[Dict[str, Any]] = []
    keys = _keys(data)
    others = [g for i, g in enumerate(groups) if i != ref]
    for i in range(len(data)):
        base = {k: data.at[i, k] for k in keys}
        extra = list(notes)
        if total:
            extra.append(f"Declared groups cover {cover[i]:.1%} of {total}.")
        for m in MEASURES:
            r = res[m]
            for j, grp in (enumerate(others) if m in dc.GROUP_MEASURES else [(None, None)]):
                pick = (lambda x: x[i, j]) if j is not None else (lambda x: x[i])  # noqa: E731
                e, se = float(pick(r["estimate"])), float(pick(r["se"]))
                valid = bool(ok[m][i]) and np.isfinite(se)
                row_notes = list(extra)
                if not valid:
                    row_notes.append(_why(m, counts, float(gate[i]), G, se))
                rows.append({**base, "measure": m, "group": grp, "reference": reference, "estimate": e, "se": se,
                             "se_scale": "log" if dc.LOG_SCALE[m] else "identity",
                             "ci_lower": float(pick(r["lower"])), "ci_upper": float(pick(r["upper"])),
                             "p_value": float(_p(e, se)) if m in dc.GROUP_MEASURES else np.nan,
                             "validated": valid, "basis": basis[m], gate_col: float(gate[i]), "notes": row_notes})
    out = pd.DataFrame(rows)
    out.attrs.update(audit=AUDIT, level=level, groups=groups, reference=reference, counts=counts)
    return out


def _why(m, counts, gate, G, se):
    if not np.isfinite(se):
        return "Uncertainty undefined (a replicate or bootstrap statistic was not finite); exploratory."
    if G > MAX_GROUPS:
        return f"Exploratory: more than {MAX_GROUPS} groups."
    if counts:
        if m not in COUNT_VALIDATED:
            return f"Exploratory: the count bootstrap interval for {m} failed validation ({AUDIT})."
        return f"Exploratory: a group has fewer than {MIN_COUNT} events (validated down to {MIN_COUNT})."
    return f"Exploratory: largest group-rate CV {gate:.2f} exceeds the validated {ACS_MAX_CV[m]:.2f} for {m} ({AUDIT})."


def index_test(row: Dict[str, Any], null_value: float) -> Dict[str, float]:
    """Wald test of an index measure (idisp, bgv, theil, mld) against a pre-registered positive null on the log
    scale, the scale of its interval."""
    if not null_value > 0:
        raise ValueError("index measures are tested against a pre-registered positive null_value (log scale)")
    est, se = float(row["estimate"]), float(row["se"])
    if not (est > 0 and np.isfinite(se) and se > 0):
        raise ValueError("index estimate or its uncertainty is undefined")
    return {"test_estimate": float(np.log(est)-np.log(null_value)), "p_two_sided": float(_p(np.log(est), se, np.log(null_value)))}


def kitagawa_decomposition(frame: pd.DataFrame, area: str, compare_area: str, rates: Sequence[str],
                           populations: Sequence[str], replicates: Optional[pd.DataFrame] = None,
                           counts: bool = False, level: float = .90, year: Optional[int] = None) -> pd.DataFrame:
    """Kitagawa (1955) decomposition of the crude-rate difference area minus compare_area.

    ``rates``: stratum rate columns (ACS, with replicates) or stratum event counts (``counts=True``, Poisson with
    known populations); ``populations``: the matching stratum populations (composition). Symmetric weights:
    crude_difference = rate_effect + composition_effect. Rows: component, estimate, se, ci_lower, ci_upper,
    p_value (against zero), validated, notes.
    """
    rates, populations = list(rates), list(populations)
    if len(rates) < 2 or len(rates) != len(populations):
        raise ValueError("rates and populations must list the same strata (at least two)")
    data = frame.assign(GEOID=frame["GEOID"].astype(str))
    if year is not None:
        data = data[data["Year"] == year]
    pick = []
    for g in (str(area), str(compare_area)):
        sub = data[data["GEOID"] == g]
        if len(sub) != 1:
            raise ValueError(f"area {g} must select exactly one row (give year for multi-release frames)")
        pick.append(sub)
    if pick[0].index[0] == pick[1].index[0]:
        raise ValueError("cannot decompose an area against itself")
    two = pd.concat(pick).reset_index(drop=True)
    r = two[rates].to_numpy(float); n = two[populations].to_numpy(float)
    if (n <= 0).any():
        raise ValueError("stratum populations must be positive")
    notes = []
    if counts:
        res = dc.kitagawa_poisson(r[0], n[0], r[1], n[1], level=level)
        mean_count = float(min(r[0].mean(), r[1].mean()))
        valid = mean_count >= KITAGAWA_MIN_MEAN_COUNT
        gate = {"min_mean_stratum_count": mean_count}
        if not valid:
            notes.append(f"Exploratory: mean events per stratum {mean_count:.1f} is below the validated "
                         f"{KITAGAWA_MIN_MEAN_COUNT}.")
    else:
        if replicates is None:
            raise ValueError("ACS stratum rates need replicates (or use counts=True)")
        mats = _rep_mats(two, replicates, rates+populations)
        if any(v not in mats or not np.isfinite(mats[v]).all() for v in rates):
            raise ValueError("stratum rates need complete, finite replicates for both areas")
        rr = np.stack([mats[v] for v in rates], axis=1)
        cr = np.stack([mats[v] for v in populations], axis=1) if all(v in mats for v in populations) else None
        if cr is None:
            notes.append("Stratum populations had no replicates: composition is held fixed in the refits.")
        res = dc.kitagawa_replicate(r[0], n[0], r[1], n[1], rr[0], None if cr is None else cr[0], rr[1],
                                    None if cr is None else cr[1], level=level)
        se_r = np.sqrt(dc.REP_FACTOR*((rr-r[:, :, None])**2).sum(axis=2))
        with np.errstate(divide="ignore", invalid="ignore"):
            cv = float(np.nanmax(np.where(r > 0, se_r/r, np.inf)))
        valid = cv <= KITAGAWA_ACS_MAX_CV
        gate = {"max_stratum_cv": cv}
        if not valid:
            notes.append(f"Exploratory: largest stratum-rate CV {cv:.2f} exceeds the validated {KITAGAWA_ACS_MAX_CV}.")
    names = dict(crude_difference="difference", rate_effect="rate_effect", composition_effect="composition_effect")
    rows = []
    for comp, key in names.items():
        x = res[key]
        e, se = float(x["estimate"]), float(x["se"])
        rows.append(dict(GEOID=str(area), compare_geoid=str(compare_area), component=comp, estimate=e, se=se,
                         ci_lower=float(x["lower"]), ci_upper=float(x["upper"]), p_value=float(_p(e, se)),
                         validated=bool(valid and np.isfinite(se)), basis="poisson" if counts else "replicate",
                         **gate, notes=list(notes)))
    out = pd.DataFrame(rows)
    out.attrs.update(audit=AUDIT, level=level)
    return out

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derived replicate-statistic algebra and wide-frame helpers (extracted from census/replicate.py in Round 167)."""
from census.replicate import (  # noqa: F401
    Any,
    Callable,
    List,
    Optional,
    REPLICATE_COUNT,
    Sequence,
    Variables,
    _as_list,
    _combine,
    _cube,
    _finish,
    _result,
    np,
    pd,
    warnings,
)



def replicate_sum(
    frame: pd.DataFrame,
    variables: Variables,
    geoids: Optional[Sequence[str]] = None,
    across_geographies: bool = False,
) -> pd.DataFrame:
    """Sum of variables within each geography (or over all ``geoids`` combined).

    Exact replicate MOE (VRE documentation, Examples 1 and 2).
    """
    vars_ = _as_list(variables)
    geo_list, names, values, moe, ctrl = _cube(frame, vars_, geoids)
    total, c = _combine(values, ctrl, across_geographies)
    est = values[0]
    zero_moe = np.where(est == 0, moe, np.nan)  # published MOEs of zero cells
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        fallback = np.nanmax(zero_moe, axis=1)
        if across_geographies:
            fallback = np.array([np.nanmax(zero_moe)]) if np.isfinite(zero_moe).any() else np.array([np.nan])
    label = f"sum of {len(vars_)} variable(s)"
    if across_geographies:
        label += f" over {len(geo_list)} geographies"
    notes = [[label] for _ in range(total.shape[1])]
    body = _finish(total, c, notes, zero_fallback_moe=fallback)
    return _result(geo_list, names, across_geographies, body)


def replicate_difference(
    frame: pd.DataFrame,
    minuend: Variables,
    subtrahend: Variables,
    geoids: Optional[Sequence[str]] = None,
    across_geographies: bool = False,
) -> pd.DataFrame:
    """(sum of ``minuend``) - (sum of ``subtrahend``), with exact replicate MOE."""
    a, b = _as_list(minuend), _as_list(subtrahend)
    geo_list, names, va, _, ca = _cube(frame, a, geoids)
    _, _, vb, _, cb = _cube(frame, b, geo_list)
    ta, ctrl_a = _combine(va, ca, across_geographies)
    tb, ctrl_b = _combine(vb, cb, across_geographies)
    notes = [[f"difference: {'+'.join(a)} minus {'+'.join(b)}"] for _ in range(ta.shape[1])]
    body = _finish(ta - tb, ctrl_a & ctrl_b, notes)
    return _result(geo_list, names, across_geographies, body)


def _ratio_stat(num: np.ndarray, den: np.ndarray, notes: List[List[str]]) -> np.ndarray:
    """num/den on (81, n); undefined replicate ratios become 0 (VRE doc, Example 7)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(den != 0, num / den, np.nan)
    for i in range(out.shape[1]):
        if den[0, i] == 0:
            notes[i].append("zero_denominator: the estimate's denominator is 0, so the ratio is undefined")
            out[:, i] = np.nan
            continue
        bad = ~np.isfinite(out[1:, i])
        if bad.any():
            notes[i].append(
                f"zero_replicate_denominator: {int(bad.sum())} replicate ratio(s) undefined and set to 0 "
                "(VRE documentation, Example 7)"
            )
            out[1:, i][bad] = 0.0
    return out


def replicate_ratio(
    frame: pd.DataFrame,
    numerator: Variables,
    denominator: Variables,
    geoids: Optional[Sequence[str]] = None,
    across_geographies: bool = False,
    multiplier: float = 1.0,
) -> pd.DataFrame:
    """Ratio of summed numerator to summed denominator variables, exact replicate MOE.

    ``multiplier`` scales the estimate and MOE (100 for a percent).
    """
    nv, dv = _as_list(numerator), _as_list(denominator)
    geo_list, names, vn, _, cn = _cube(frame, nv, geoids)
    _, _, vd, _, cd = _cube(frame, dv, geo_list)
    tn, ctrl_n = _combine(vn, cn, across_geographies)
    td, ctrl_d = _combine(vd, cd, across_geographies)
    notes = [[f"ratio: {'+'.join(nv)} / {'+'.join(dv)}"] for _ in range(tn.shape[1])]
    stat = _ratio_stat(tn, td, notes) * multiplier
    body = _finish(stat, ctrl_n & ctrl_d, notes)
    return _result(geo_list, names, across_geographies, body)


def replicate_proportion(
    frame: pd.DataFrame,
    numerator: Variables,
    denominator: Variables,
    geoids: Optional[Sequence[str]] = None,
    across_geographies: bool = False,
    as_percent: bool = False,
) -> pd.DataFrame:
    """Proportion (numerator a subset of denominator), exact replicate MOE.

    The replicate method needs no subset/non-subset distinction; a note is added
    when an estimate's numerator exceeds its denominator, which signals that the
    numerator is not actually a subset.
    """
    out = replicate_ratio(
        frame, numerator, denominator, geoids, across_geographies, 100.0 if as_percent else 1.0
    )
    top = 100.0 if as_percent else 1.0
    for i, value in enumerate(out["estimate"]):
        if np.isfinite(value) and value > top + 1e-12:
            out.at[i, "notes"] = out.at[i, "notes"] + [
                "not_a_subset: numerator exceeds denominator; use replicate_ratio"
            ]
    return out


def replicate_apply(
    frame: pd.DataFrame,
    func: Callable[[Any], Any],
    variables: Optional[Variables] = None,
    geoids: Optional[Sequence[str]] = None,
    as_dict: bool = False,
    note: Optional[str] = None,
) -> pd.DataFrame:
    """Exact replicate MOE for any statistic of the replicate frame.

    ``func`` receives an array shaped (n_geographies, n_variables) - or, with
    ``as_dict=True``, a dict {variable: array(n_geographies)} - and returns a
    scalar or a 1-D array. It is evaluated on the published estimates and on
    each of the 80 replicate columns, then census.variance.replicate_moe
    formula is applied. ``variables`` defaults to every variable in the frame
    (in first-seen order); ``geoids`` to every geography.

    A result of length n_geographies is labelled with GEOID/NAME; a scalar gives
    one row labelled with all GEOIDs; any other length is labelled by position.
    Medians (census.medians) and aggregation (census.aggregate) build on this.
    """
    vars_ = _as_list(variables) or list(dict.fromkeys(frame["variable"]))
    geo_list, names, values, _, ctrl = _cube(frame, vars_, geoids)

    def call(mat: np.ndarray) -> np.ndarray:
        arg = {v: mat[:, j] for j, v in enumerate(vars_)} if as_dict else mat
        return np.atleast_1d(np.asarray(func(arg), dtype=float))

    results = [call(values[k]) for k in range(REPLICATE_COUNT + 1)]
    shapes = {r.shape for r in results}
    if len(shapes) != 1 or len(results[0].shape) != 1:
        raise ValueError("func must return a scalar or a 1-D array of the same length for every replicate.")
    stat = np.vstack(results)  # (81, n)
    n = stat.shape[1]
    base = [note] if note else ["replicate_apply"]
    notes = [list(base) for _ in range(n)]
    if n == len(geo_list):
        body = _finish(stat, ctrl.all(axis=1), notes)
        return _result(geo_list, names, False, body)
    body = _finish(stat, np.full(n, bool(ctrl.all())), notes)
    if n == 1:
        return _result(geo_list, names, True, body)
    body.insert(0, "index", range(n))
    return body


def replicate_frame_to_wide(frame: pd.DataFrame) -> pd.DataFrame:
    """Published estimates and MOEs as a wide frame (GEOID, NAME, <var>E, <var>M)."""
    est = frame.pivot(index="GEOID", columns="variable", values="estimate").add_suffix("E")
    moe = frame.pivot(index="GEOID", columns="variable", values="moe").add_suffix("M")
    names = frame.groupby("GEOID", sort=False)["NAME"].first()
    wide = pd.concat([names, est, moe], axis=1)
    order = [c for v in dict.fromkeys(frame["variable"]) for c in (f"{v}E", f"{v}M")]
    return wide[["NAME"] + order].reset_index()

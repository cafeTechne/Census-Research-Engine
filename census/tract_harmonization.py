# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tract harmonization for pre-registered manifests (PLAN_ROUND_19 A1-A2).

A manifest with ``geography.harmonize_tracts_to`` (2020 or 2010) puts every
release on one tract vintage before the analysis frame is built. Releases
already on the target vintage are kept; the others are apportioned with
:func:`census.geo_crosswalk.apportion` through one crosswalk per weight type
(block housing-unit weights for household/housing tables, block population
weights otherwise; :func:`census.block_weights.weight_for_variable`).

The Census VRE replicates of an apportioned release go through **the same
crosswalk**. Every replicate is a count, so the apportioned replicates give the
exact replicate SE of the apportioned estimate, sum_s w_s X_s, including the
sampling covariance between source tracts. The published-MOE route
(sqrt(sum (w MOE)^2)) assumes those source tracts are independent.

Only additive counts can be apportioned. The crosswalk's own error
(block-weight interpolation) is not part of any SE.
"""

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

HARMONIZE_TARGETS = (2010, 2020)
# Connecticut's 2022+ releases use planning-region GEOIDs; the 2010-2020 tract
# relationship file uses the former county codes. Not supported in manifests.
UNSUPPORTED_STATES = ("09",)


def direction_for(target: int) -> str:
    return "2010_to_2020" if int(target) == 2020 else "2020_to_2010"


def releases_to_apportion(releases: Sequence[int], target: int) -> List[int]:
    """Releases whose tract vintage differs from ``target``."""
    from .geo_crosswalk import tract_vintage
    return sorted(int(r) for r in releases if tract_vintage(int(r)) != int(target))


def weight_kind(code: str) -> str:
    from .block_weights import weight_for_variable
    return weight_for_variable(str(code))


def validation_errors(geo: Mapping[str, Any], manifest: Mapping[str, Any]) -> List[str]:
    """Errors for ``geography.harmonize_tracts_to`` (empty when absent or valid)."""
    if "harmonize_tracts_to" not in geo:
        return []
    from .pipeline import normalize_geo_level
    errs: List[str] = []
    target = geo.get("harmonize_tracts_to")
    if target not in HARMONIZE_TARGETS or isinstance(target, bool):
        return [f"geography.harmonize_tracts_to must be one of {list(HARMONIZE_TARGETS)} (a tract vintage)"]
    try:
        level = normalize_geo_level(str(geo.get("level", "")))
    except Exception:  # noqa: BLE001 - reported by the geography check
        level = geo.get("level")
    if level != "tract":
        errs.append("geography.harmonize_tracts_to applies only to level 'tract'")
    states = [str(s) for s in (geo.get("states") or [geo.get("state")]) if s]
    if any(s.strip().lower() == "all" or s.strip() in UNSUPPORTED_STATES
           for st in states for s in str(st).split(",")):
        errs.append("geography.harmonize_tracts_to: Connecticut (09, also part of 'all') is not supported: its "
                    "2022+ releases use planning-region GEOIDs that the 2010-2020 tract relationship file does not "
                    "use; list the other states in geography.states")
    if manifest.get("aggregation") is not None:
        errs.append("geography.harmonize_tracts_to cannot be combined with aggregation")
    from .geo_crosswalk import check_additive
    from .stats import parse_variable_code
    for v in manifest.get("variables") or []:
        ref = str((v or {}).get("ref", "")) if isinstance(v, Mapping) else ""
        code = ref.split(":", 1)[1] if ":" in ref else None
        parsed = parse_variable_code(code) if code else None
        base = parsed[0] if parsed else code
        if not base:
            continue  # concept-id refs are checked when the run apportions them
        _, refused, _ = check_additive([f"{base}E"])
        if refused:
            errs.append(f"geography.harmonize_tracts_to: variable {v.get('name')!r} ({base}) cannot be apportioned "
                        f"between tract vintages: {next(iter(refused.values()))}. Only additive counts can be "
                        "apportioned; derive rates, means and shares from apportioned counts (derivations)")
    return errs


def crosswalks(target: int, states: Sequence[str], kinds: Sequence[str]) -> Dict[str, pd.DataFrame]:
    """One tract crosswalk per weight kind, built for ``states`` only."""
    from .geo_crosswalk import tract_crosswalk
    # No silent land-area fallback: the pre-registered method is block weights; a failure is a deviation.
    return {k: tract_crosswalk(direction_for(target), weight=k, states=list(states) or None, block_fallback=False)
            for k in sorted(set(kinds))}


def harmonize_wide(wide: pd.DataFrame, codes: Mapping[str, str], target: int,
                   crosswalk_by_kind: Mapping[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Put a code-keyed wide frame (GEOID, Year, ``<code>E``/``<code>M``) on ``target`` tracts.

    ``codes``: manifest name -> ACS base code. Returns (frame, record).
    """
    from .geo_crosswalk import apportion, normalize_tract_geoids
    years = sorted(int(y) for y in pd.unique(wide["Year"]))
    moved = releases_to_apportion(years, target)
    native = wide[~wide["Year"].astype(int).isin(moved)].copy()
    native["GEOID"] = normalize_tract_geoids(native["GEOID"]).values
    source = wide[wide["Year"].astype(int).isin(moved)]
    by_kind: Dict[str, List[str]] = {}
    for name, code in codes.items():
        by_kind.setdefault(weight_kind(code), []).append(code)
    parts: List[pd.DataFrame] = []
    kinds: Dict[str, Any] = {}
    for kind, kind_codes in sorted(by_kind.items()):
        est = [f"{c}E" for c in dict.fromkeys(kind_codes)]
        moe = {e: e[:-1] + "M" for e in est if e[:-1] + "M" in source.columns}
        cw = crosswalk_by_kind[kind]
        if source.empty:
            continue
        out = apportion(source[["GEOID", "Year"] + est + list(moe.values())], cw, estimate_cols=est,
                        moe_cols=moe, group_cols=("Year",))
        kinds[kind] = {"variables": est, "weight_type": out.attrs.get("weight_type"),
                       "notes": out.attrs.get("notes"), "source": cw.attrs.get("source"),
                       "fallbacks": cw.attrs.get("fallbacks"),
                       "unmatched_source_tracts": len(out.attrs.get("unmatched_geoids") or []),
                       "dropped_targets": out.attrs.get("incomplete_targets") or []}
        parts.append(out)
    apportioned = None
    for p in parts:
        apportioned = p if apportioned is None else apportioned.merge(p, on=["GEOID", "Year"], how="outer")
    frames = [native] + ([apportioned] if apportioned is not None else [])
    result = pd.concat(frames, ignore_index=True, sort=False)
    record = {"target_vintage": int(target), "direction": direction_for(target), "apportioned_releases": moved,
              "native_releases": [y for y in years if y not in moved], "weights": kinds,
              "rows": {str(y): int((result["Year"].astype(int) == y).sum()) for y in years},
              "uncertainty": "Apportioned MOEs (and _se) use the independence approximation sqrt(sum (w*MOE)^2); "
                             "replicate analyses use apportioned replicates (exact sampling SE of sum w*X). The "
                             "crosswalk's interpolation error is in neither."}
    return result, record


def apportion_replicates(reps: pd.DataFrame, code: str, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Apportion one variable's replicate rows (GEOID, estimate, rep_1..rep_80) with ``crosswalk``.

    Each replicate column is apportioned exactly like the estimate (sum w * X), so
    replicate variance of the result is the exact sampling variance of the
    apportioned estimate. Returns the same columns on target GEOIDs.
    """
    from .analysis import REPLICATE_COLUMNS
    from .geo_crosswalk import apportion
    cols = ["estimate"] + [c for c in REPLICATE_COLUMNS if c in reps.columns]
    out = apportion(reps[["GEOID"] + cols], crosswalk, estimate_cols=cols, assume_additive=True)
    out.attrs["code"] = code
    return out[["GEOID"] + cols]


def replicate_estimate_check(frame: pd.DataFrame, reps: pd.DataFrame, names: Sequence[str],
                             years: Sequence[int]) -> Dict[str, Any]:
    """Agreement of apportioned VRE ``estimate`` with the apportioned frame estimate.

    Both are sum w * (published estimate), so they agree to floating-point error
    when the VRE files and the API carry the same published values.
    """
    out: Dict[str, Any] = {}
    for n in names:
        sub = reps[(reps["variable"] == n) & reps["Year"].astype(int).isin(list(years))]
        if sub.empty or n not in frame.columns:
            continue
        merged = sub[["GEOID", "Year", "estimate"]].merge(frame[["GEOID", "Year", n]], on=["GEOID", "Year"])
        diff = (pd.to_numeric(merged["estimate"]) - pd.to_numeric(merged[n])).abs()
        scale = pd.to_numeric(merged[n]).abs().clip(lower=1.0)
        out[n] = {"rows": int(len(merged)), "max_abs_diff": float(diff.max()) if len(diff) else None,
                  "max_rel_diff": float((diff / scale).max()) if len(diff) else None}
    return out


def methods_text(record: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not record:
        return None
    if record.get("error"):
        return (f"Tract harmonization to {record.get('target_vintage')} tracts was pre-registered but failed "
                f"({record['error']}); see deviations.")
    moved = ", ".join(str(y) for y in record.get("apportioned_releases") or []) or "none"
    weights = "; ".join(f"{k} weights for {', '.join(v.get('variables') or [])}"
                        for k, v in (record.get("weights") or {}).items())
    dropped = sum(len(v.get("dropped_targets") or []) for v in (record.get("weights") or {}).values())
    return (f"Tract harmonization (pre-registered): releases {moved} were apportioned to "
            f"{record['target_vintage']} Census tracts with the Census tract relationship file and block "
            f"weights ({weights}); target tracts covered below 99% by the input were dropped ({dropped}). "
            "Census VRE replicates of those releases were apportioned with the same weights, so replicate SEs are "
            "the exact sampling SEs of the apportioned estimates; published-MOE SEs of apportioned values assume "
            "independent source tracts. Interpolation error of the crosswalk is not in any SE.")

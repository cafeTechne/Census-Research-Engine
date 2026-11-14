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
    from .geo_crosswalk import check_additive, tract_vintage
    from .stats import parse_variable_code
    for r in manifest.get("releases") or []:
        try:
            tract_vintage(int(r))
        except (TypeError, ValueError) as exc:
            errs.append(f"geography.harmonize_tracts_to: release {r!r}: {exc}")
    for v in manifest.get("variables") or []:
        if not isinstance(v, Mapping):
            continue
        ref = str(v.get("ref", ""))
        if ":" not in ref:  # concept id: the code is only known after concordance resolution
            errs.append(f"geography.harmonize_tracts_to: variable {v.get('name')!r} uses a concept id ({ref}); "
                        "give a YEAR:CODE reference so its additivity can be checked before preregistration")
            continue
        code = ref.split(":", 1)[1]
        parsed = parse_variable_code(code)
        column = f"{parsed[0]}{parsed[1]}" if parsed else f"{code}E"
        ok, refused, unverified = check_additive([column])
        reason = next(iter(refused.values()), None) or (
            "no label in the offline metadata archive, so it cannot be verified as a count" if unverified else None)
        if reason or not ok:
            errs.append(f"geography.harmonize_tracts_to: variable {v.get('name')!r} ({code}) cannot be apportioned "
                        f"between tract vintages: {reason or 'not an additive count'}. Only additive counts can "
                        "be apportioned; derive rates, means and shares from apportioned counts (derivations)")
    return errs


def ct_coding_for(releases: Sequence[int]) -> str:
    from .geo_crosswalk import FIRST_RELEASE_CT_PLANNING_REGIONS
    return "2022" if any(int(y) >= FIRST_RELEASE_CT_PLANNING_REGIONS for y in releases) else "2020"


def crosswalks(target: int, states: Sequence[str], kinds: Sequence[str],
               releases: Sequence[int] = ()) -> Dict[str, pd.DataFrame]:
    """One tract crosswalk per weight kind, built for ``states`` only, with target codes in
    the output coding (:func:`census.geo_crosswalk.crosswalk_targets_to_output_codes`)."""
    from .geo_crosswalk import crosswalk_targets_to_output_codes, tract_crosswalk
    out = {}
    for k in sorted(set(kinds)):
        # No silent land-area fallback: the pre-registered method is block weights; a failure is a deviation.
        cw = tract_crosswalk(direction_for(target), weight=k, states=list(states) or None, block_fallback=False)
        attrs = dict(cw.attrs)
        cw = cw.copy()
        cw["target_geoid"] = crosswalk_targets_to_output_codes(cw["target_geoid"], target,
                                                               ct_coding_for(releases)).values
        cw.attrs = attrs
        out[k] = cw
    return out


def to_crosswalk_codes(geoids: Any, target: int) -> pd.Series:
    """Source-release tract GEOIDs in the relationship file's codes (ACS renumberings undone)."""
    from .geo_crosswalk import normalize_tract_geoids, source_tracts_to_crosswalk_codes
    return source_tracts_to_crosswalk_codes(pd.Series(normalize_tract_geoids(geoids).values), target)


def harmonize_wide(wide: pd.DataFrame, codes: Mapping[str, str], target: int,
                   crosswalk_by_kind: Mapping[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Put a code-keyed wide frame (GEOID, Year, ``<code>E``/``<code>M``) on ``target`` tracts.

    GEOIDs are recoded exactly as :func:`census.geo_crosswalk.harmonize_panel` does (shared
    helpers): source rows to the relationship file's codes, native rows to the output coding.
    ``codes``: manifest name -> ACS base code. Returns (frame, record); the record lists every
    source tract the crosswalk does not contain (``unmatched_source_tracts``; known ACS boundary
    changes separately) and every target with rows in a native release but none in an
    apportioned one (``targets_without_apportioned_rows``).
    """
    from .geo_crosswalk import ACS_2010_BOUNDARY_CHANGES, apportion, native_tracts_to_output_codes, \
        normalize_tract_geoids
    years = sorted(int(y) for y in pd.unique(wide["Year"]))
    moved = releases_to_apportion(years, target)
    ct = ct_coding_for(years)
    native = wide[~wide["Year"].astype(int).isin(moved)].copy()
    native["GEOID"] = native_tracts_to_output_codes(
        pd.Series(normalize_tract_geoids(native["GEOID"]).values, index=native.index), target, ct).values
    source = wide[wide["Year"].astype(int).isin(moved)].copy()
    raw_source_ids = normalize_tract_geoids(source["GEOID"]).values
    source["GEOID"] = to_crosswalk_codes(source["GEOID"], target).values
    by_kind: Dict[str, List[str]] = {}
    for name, code in codes.items():
        by_kind.setdefault(weight_kind(code), []).append(code)
    parts: List[pd.DataFrame] = []
    kinds: Dict[str, Any] = {}
    unmatched: set = set()
    for kind, kind_codes in sorted(by_kind.items()):
        if source.empty:
            continue
        est = [f"{c}E" for c in dict.fromkeys(kind_codes)]
        moe = {e: e[:-1] + "M" for e in est if e[:-1] + "M" in source.columns}
        cw = crosswalk_by_kind[kind]
        out = apportion(source[["GEOID", "Year"] + est + list(moe.values())], cw, estimate_cols=est,
                        moe_cols=moe, group_cols=("Year",))
        unmatched |= set(out.attrs.get("unmatched_geoids") or [])
        kinds[kind] = {"variables": est, "weight_type": out.attrs.get("weight_type"),
                       "notes": out.attrs.get("notes"), "source": cw.attrs.get("source"),
                       "fallbacks": cw.attrs.get("fallbacks"),
                       "dropped_targets": out.attrs.get("incomplete_targets") or []}
        parts.append(out)
    apportioned = None
    for p in parts:
        apportioned = p if apportioned is None else apportioned.merge(p, on=["GEOID", "Year"], how="outer")
    frames = [native] + ([apportioned] if apportioned is not None else [])
    result = pd.concat(frames, ignore_index=True, sort=False)
    acs_code = dict(zip(source["GEOID"], raw_source_ids))
    unmatched_acs = sorted(acs_code.get(g, g) for g in unmatched)
    boundary = [g for g in unmatched_acs if g in ACS_2010_BOUNDARY_CHANGES]
    missing_targets: List[str] = []
    if moved:
        have = set(result.loc[result["Year"].astype(int).isin(moved), "GEOID"])
        missing_targets = sorted(set(native["GEOID"]) - have)
    record = {"target_vintage": int(target), "direction": direction_for(target), "apportioned_releases": moved,
              "native_releases": [y for y in years if y not in moved], "weights": kinds,
              "geoid_recodes": int((source["GEOID"].values != raw_source_ids).sum()),
              "unmatched_source_tracts": [g for g in unmatched_acs if g not in boundary],
              "acs_boundary_change_tracts": {g: ACS_2010_BOUNDARY_CHANGES[g] for g in boundary},
              "targets_without_apportioned_rows": missing_targets,
              "rows": {str(y): int((result["Year"].astype(int) == y).sum()) for y in years},
              "uncertainty": "Apportioned MOEs (and _se) use the independence approximation sqrt(sum (w*MOE)^2); "
                             "replicate analyses use apportioned replicates (exact sampling SE of sum w*X). The "
                             "crosswalk's interpolation error is in neither."}
    if boundary:
        record["notes"] = [f"{len(boundary)} source tract(s) changed boundaries in the ACS after the 2010 Census "
                           "(no exact equivalent in the relationship file); their values could not be apportioned: "
                           + "; ".join(record["acs_boundary_change_tracts"].values())]
    return result, record


def apportion_replicates(reps: pd.DataFrame, code: str, crosswalk: pd.DataFrame, target: int = 2020) -> pd.DataFrame:
    """Apportion one variable's replicate rows (GEOID, estimate, rep_1..rep_80) with ``crosswalk``.

    Source GEOIDs are recoded as for the estimates first. Each replicate column is apportioned
    exactly like the estimate (sum w * X), so replicate variance of the result is the exact
    sampling variance of the apportioned estimate. Returns the same columns on target GEOIDs.
    """
    from .analysis import REPLICATE_COLUMNS
    from .geo_crosswalk import apportion
    cols = ["estimate"] + [c for c in REPLICATE_COLUMNS if c in reps.columns]
    src = reps[["GEOID"] + cols].copy()
    src["GEOID"] = to_crosswalk_codes(src["GEOID"], target).values
    out = apportion(src, crosswalk, estimate_cols=cols, assume_additive=True)
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

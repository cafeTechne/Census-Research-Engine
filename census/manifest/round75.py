# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest support for methods validated in Round 73 (PLAN_ROUND_75): composite indices built inside a manifest
(``"indices"`` block), person-years expected counts (``expected_count`` with ``person_years``), and the GEOID group
columns ``state_fips`` / ``county_fips`` used by the ``multilevel`` method.

No new statistics: index scores and their replicate values follow Round 36/73 (full-sample means, SDs and weights
fixed in every replicate); expected counts follow ``census.wonder_reference.expected_counts`` (Round 73).
"""
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

GEO_GROUP_COLUMNS = {"state_fips": 2, "county_fips": 5}
INDEX_METHODS = ("pca", "equal", "loadings")
INDEX_KEYS = {"name", "indicators", "method", "loadings", "reverse", "standardize"}


# ---- validation -------------------------------------------------------------------------------------------------

def index_names(manifest: Mapping[str, Any]) -> List[str]:
    return [str(e.get("name")) for e in manifest.get("indices") or [] if isinstance(e, Mapping)]


def acs_names(manifest: Mapping[str, Any]) -> List[str]:
    return ([str(v.get("name")) for v in manifest.get("variables") or [] if isinstance(v, Mapping)]
            + [str(d.get("name")) for d in manifest.get("derivations") or [] if isinstance(d, Mapping)])


def index_errors(manifest: Mapping[str, Any]) -> List[str]:
    entries = manifest.get("indices")
    if entries is None:
        return []
    if not isinstance(entries, list) or not entries:
        return ["indices must be a non-empty list of {name, indicators, method, ...}"]
    errs: List[str] = []
    acs = set(acs_names(manifest))
    for i, e in enumerate(entries):
        p = f"indices[{i}]"
        if not isinstance(e, Mapping):
            errs.append(f"{p} must be an object"); continue
        extra = set(e) - INDEX_KEYS
        if extra:
            errs.append(f"{p}: unknown keys {sorted(extra)}")
        ind = e.get("indicators")
        method = e.get("method", "pca")
        if method not in INDEX_METHODS:
            errs.append(f"{p}: method must be one of {INDEX_METHODS}")
        if not isinstance(ind, list) or not all(isinstance(x, str) for x in ind) or len(set(ind)) != len(ind):
            errs.append(f"{p}: indicators must be a list of distinct names"); continue
        if len(ind) < (2 if method == "loadings" else 3):
            errs.append(f"{p}: {method} needs at least {2 if method == 'loadings' else 3} indicators")
        bad = [x for x in ind if x not in acs]
        if bad:
            errs.append(f"{p}: indicators {bad} must be ACS manifest variables or derivations (they need replicates; "
                        "context and external variables cannot be indicators)")
        if method == "loadings":
            lw = e.get("loadings")
            if not isinstance(lw, Mapping) or set(lw) != set(ind) or not all(
                    type(v) in (int, float) and np.isfinite(v) for v in lw.values()) or all(v == 0 for v in lw.values()):
                errs.append(f"{p}: loadings must give a finite weight for every indicator (not all zero)")
        elif e.get("loadings") is not None:
            errs.append(f"{p}: loadings apply only to method 'loadings'")
        rev = e.get("reverse", [])
        if not isinstance(rev, list) or any(r not in ind for r in rev):
            errs.append(f"{p}: reverse must list indicators")
        if "standardize" in e and type(e["standardize"]) is not bool:
            errs.append(f"{p}: standardize must be boolean")
    names = index_names(manifest)
    if len(set(names)) != len(names) or set(names) & acs:
        errs.append("index names must be unique and differ from variable/derivation names")
    return errs


def index_circularity_errors(manifest: Mapping[str, Any]) -> List[str]:
    """An analysis may not use an index as a covariate when its outcome is one of that index's indicators."""
    from .schema import _formula_names
    from .validate import _normalize_analysis
    idx = {str(e["name"]): set(e.get("indicators") or []) for e in manifest.get("indices") or []
           if isinstance(e, Mapping) and isinstance(e.get("indicators"), list)}
    errs = []
    for a in manifest.get("analyses") or []:
        a = _normalize_analysis(a)
        f = str(a.get("formula", ""))
        if "~" not in f:
            continue
        lhs, rhs = f.split("~", 1)
        for out in _formula_names(lhs):
            for name in _formula_names(rhs):
                if name in idx and out in idx[name]:
                    errs.append(f"CIRCULARITY: analysis {a.get('id')!r} explains {out!r} with index {name!r}, which "
                                f"has {out!r} as an indicator")
    return errs


def person_years_errors(manifest: Mapping[str, Any], ext_names: Sequence[str]) -> List[str]:
    errs = []
    for d in manifest.get("derivations") or []:
        if isinstance(d, Mapping) and "person_years" in d:
            if d.get("op") != "expected_count":
                errs.append(f"derivation {d.get('name')!r}: person_years applies to op 'expected_count' only")
            elif d["person_years"] not in ext_names:
                errs.append(f"derivation {d.get('name')!r}: person_years must name an external variable "
                            f"(one of {sorted(ext_names)})")
    return errs


# ---- run stages -------------------------------------------------------------------------------------------------

def with_geo_groups(frame: pd.DataFrame, needed) -> pd.DataFrame:
    """Add state_fips / county_fips (GEOID prefixes) when an analysis names them."""
    want = [c for c in GEO_GROUP_COLUMNS if c in needed and c not in frame]
    if not want or "GEOID" not in frame:
        return frame
    f = frame.copy()
    for c in want:
        f[c] = f["GEOID"].astype(str).str[:GEO_GROUP_COLUMNS[c]]
    return f


def _replicate_matrix(reps: pd.DataFrame, name: str, keys: pd.DataFrame) -> Optional[np.ndarray]:
    from ..replicate import REPLICATE_COLUMNS
    r = reps[reps["variable"].astype(str) == name]
    if r.empty:
        return None
    on = [c for c in ("GEOID", "Year") if c in keys and c in r]
    r = r.assign(GEOID=r["GEOID"].astype(str))
    m = keys.merge(r[on+list(REPLICATE_COLUMNS)], on=on, how="left")
    out = m[list(REPLICATE_COLUMNS)].to_numpy(float)
    return None if not np.isfinite(out).all() else out


def build_indices(frame: pd.DataFrame, reps: Any, entries: Sequence[Mapping[str, Any]]
                  ) -> Tuple[pd.DataFrame, Any, List[Dict[str, Any]]]:
    """Add each index to the frame (score, _se, _method) and, with replicates, its replicate rows."""
    from .. import index_core as ic
    from ..replicate import REPLICATE_COLUMNS
    f = frame.copy()
    keys = f[[c for c in ("GEOID", "Year") if c in f]].assign(GEOID=lambda d: d["GEOID"].astype(str))
    reps_df = reps if isinstance(reps, pd.DataFrame) else (pd.DataFrame(reps) if reps is not None else None)
    added, info = [], []
    for e in entries:
        ind = list(e["indicators"]); method = e.get("method", "pca")
        X = f[ind].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        ok = np.isfinite(X).all(axis=1)
        sign = np.array([-1. if c in (e.get("reverse") or []) else 1. for c in ind])
        Xs = X[ok]*sign
        m, s = ic.standardize(Xs)
        if method == "loadings":
            lw = np.array([float(e["loadings"][c]) for c in ind])
        else:
            lw, _ = ic.loadings((Xs-m)/s, method)
        sc = ic.scores(Xs, m, s, lw)
        mu, sd = (float(np.mean(sc)), float(np.std(sc, ddof=1))) if e.get("standardize") else (0., 1.)
        score = np.full(len(f), np.nan); score[ok] = (sc-mu)/sd
        name = str(e["name"])
        f[name] = score
        rec = dict(name=name, method=method, indicators=ind, weights=dict(zip(ind, map(float, lw))),
                   means=dict(zip(ind, map(float, m*sign))), sds=dict(zip(ind, map(float, s))),
                   standardize=bool(e.get("standardize")), n=int(ok.sum()), replicates=False)
        if reps_df is not None and "variable" in reps_df:
            mats = [_replicate_matrix(reps_df, c, keys) for c in ind]
            if all(x is not None for x in mats):
                R = np.stack(mats, axis=1)[ok]*sign[None, :, None]           # n x k x 80
                rs = (np.einsum("nkr,k->nr", (R-m[None, :, None])/s[None, :, None], lw)-mu)/sd
                full = np.full((len(f), rs.shape[1]), np.nan); full[ok] = rs
                se = np.sqrt(4/80*((full-score[:, None])**2).sum(axis=1))
                f[name+"_se"] = se; f[name+"_method"] = np.where(ok, "replicate", "")
                rows = keys.copy(); rows["variable"] = name; rows["estimate"] = score
                rows[list(REPLICATE_COLUMNS)] = full
                added.append(rows[ok]); rec["replicates"] = True
            else:
                f[name+"_se"] = np.nan
        info.append(rec)
    if added and reps_df is not None:
        combined = pd.concat([reps_df]+added, ignore_index=True)
        combined.attrs = dict(getattr(reps_df, "attrs", {}) or {})
        reps = combined
    return f, reps, info


def apply_person_years(frame: pd.DataFrame, reps: Any, derivations: Sequence[Mapping[str, Any]]
                       ) -> Tuple[pd.DataFrame, Any, List[Dict[str, Any]]]:
    """expected_count with person_years: E = PY x sum_b rate_b x share_b (the ACS age x sex mix), after the join."""
    from ..replicate import REPLICATE_COLUMNS
    from ..wonder_reference import expected_count_weights
    f = frame.copy(); notes = []; records = []
    reps_df = reps if isinstance(reps, pd.DataFrame) else (pd.DataFrame(reps) if reps is not None else None)
    keys = f[[c for c in ("GEOID", "Year") if c in f]].assign(GEOID=lambda d: d["GEOID"].astype(str))
    for d in derivations:
        if d.get("op") != "expected_count" or "person_years" not in d:
            continue
        name, bands = str(d["name"]), list(d["population_bands"])
        w, _ = expected_count_weights(d)
        period = float(d.get("period_years", 1))
        pops = f[bands].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        py = pd.to_numeric(f[d["person_years"]], errors="coerce").to_numpy(float)
        rate = pops@(np.asarray(w, float)/period)
        old = pd.to_numeric(f[name], errors="coerce").to_numpy(float) if name in f else None
        with np.errstate(divide="ignore", invalid="ignore"):
            f[name] = py*rate/pops.sum(axis=1)
            if old is not None and name+"_se" in f:      # a propagated SE scales with the value
                f[name+"_se"] = pd.to_numeric(f[name+"_se"], errors="coerce")*(f[name].to_numpy(float)/old)
        rec = dict(name=name, person_years=d["person_years"], replicates="none")
        if reps_df is not None and "variable" in reps_df and (reps_df["variable"].astype(str) == name).any():
            mats = [_replicate_matrix(reps_df, b, keys) for b in bands]
            reps_df = reps_df[reps_df["variable"].astype(str) != name]
            if all(x is not None for x in mats):
                R = np.stack(mats, axis=1)                                     # n x bands x 80
                with np.errstate(divide="ignore", invalid="ignore"):
                    er = py[:, None]*np.einsum("nbr,b->nr", R, np.asarray(w, float)/period)/R.sum(axis=1)
                rows = keys.copy(); rows["variable"] = name; rows["estimate"] = f[name].to_numpy()
                rows[list(REPLICATE_COLUMNS)] = er
                reps_df = pd.concat([reps_df, rows], ignore_index=True)
                se = np.sqrt(4/80*((er-f[name].to_numpy()[:, None])**2).sum(axis=1))
                f[name+"_se"] = se
                rec["replicates"] = "rescaled per replicate (person-years fixed)"
            else:
                rec["replicates"] = "dropped: band replicates absent"
                notes.append(f"{name}: band replicates absent, so its replicate rows were dropped")
        rec["notes"] = notes
        notes = []
        records.append(rec)
    return f, reps_df if reps_df is not None else reps, records

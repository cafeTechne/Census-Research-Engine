# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest schema definitions."""

from census.data_integrity import integrity_errors, BundledDataIntegrityError
import copy
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from ..results import IncompleteReplicatesError, ModelResult, interval_description


SCHEMA_VERSION = 1
AUTHOR_RE = re.compile(r"^(human|agent):\S+$")
CONCEPT_RE = re.compile(r"^c_[0-9a-f]{12}$")
YEAR_CODE_RE = re.compile(r"^(\d{4}):([A-Z]+\d+[A-Z]*_\d+[A-Z]*)$")
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DIRECTIONS = ("two-sided", "greater", "less")
STATUS_CONFIRMATORY = "confirmatory"
STATUS_CONFIRMATORY_INCOMPLETE = "confirmatory_incomplete"
INCOMPLETE_STATUS_TEXT = "pre-registered analysis did not run as registered; results are not confirmatory"
# deviations meaning the pre-registered analysis did not run as registered
BLOCKING_DEVIATIONS = ("blocked_variable", "extraction_failed", "variable_missing_from_extraction",
                       "aggregation_failed", "analysis_frame_failed", "analysis_not_run",
                       "replicates_unavailable", "analysis_failed", "replicates_incomplete",
                       "hypothesis_not_tested", "failed_calls", "data_source_mismatch", "adjustment_failed",
                       "replicates_overlapping_releases", "harmonization_failed", "harmonization_incomplete",
                       "harmonization_mismatch", "external_unavailable", "external_join_failed")
DATA_SOURCE_KEYS = ("synthetic", "description", "generator")
STATUS_EXPLORATORY = "exploratory"

from .methods import METHODS, ANALYSIS_METHODS, STATISTICS, REPLICATE_METHODS

EXCLUSION_RULES = ("cv_screen", "geoid_exclude")
ADJUSTMENT_TYPES = ("rpp",)
RPP_ADJUSTMENT_KEYS = ("type", "variables", "rpp_year", "areas", "rpp_years", "dollar_year", "price_index")
REPLICATE_SOURCES = ("census_vre",)
REPLICATES_KEYS = ("source",)
REPLICATE_SCOPES = ("all", "covariates_only")
# frame identifier columns a formula may name (C(Year) for a change across releases, C(GEOID...) terms)
FORMULA_ID_COLUMNS = ("GEOID", "Year")
# geography levels whose GEOIDs start with the state FIPS (state RPP areas; usable with
# geography.states). ZCTA GEOIDs are not state-prefixed and ZCTAs can cross state lines.
_STATE_PREFIXED_LEVELS = ("state", "county", "tract", "block group", "place")
FIPS2_RE = re.compile(r"^\d{2}$")
FORMULA_FUNCTIONS = {"cr", "C", "I", "np", "log", "exp", "sqrt", "center", "standardize", "scale", "Q"}

REFERENCES = {
    "duncan": "Duncan, O.D. & Duncan, B. (1955). American Sociological Review 20:210–217.",
    "massey": "Massey, D.S. & Denton, N.A. (1988). Social Forces 67:281–315.",
    "reardon": "Reardon, S.F. & Firebaugh, G. (2002). Sociological Methodology 32:33–67.",
    "cluster_bch": "Bester, C.A., Conley, T.G. & Hansen, C.B. (2011). Inference with dependent data using cluster covariance estimators. Journal of Econometrics 165:137-151.",
    "cluster_im": "Ibragimov, R. & Müller, U.K. (2010). t-Statistic Based Correlation and Heterogeneity Robust Inference. JBES 28:453-468.",
    "cluster_wcr": "Kline, P. & Santos, A. (2012). A Score Based Approach to Wild Bootstrap Inference. Journal of Econometric Methods 1:23-41. https://eml.berkeley.edu/~pkline/papers/ScoreFinal_web.pdf",

    "pamuk": "Pamuk, E.R. (1985). Social class inequality in mortality from 1921 to 1972 in England and Wales. Population Studies 39:17-31.",
    "kakwani": "Kakwani, N., Wagstaff, A. & van Doorslaer, E. (1997). Socioeconomic inequalities in health: measurement, computation, and statistical inference. Journal of Econometrics 77:87-103.",
    "garwood": "Garwood, F. (1936). Fiducial limits for the Poisson distribution. Biometrika 28:437-442.",
    "breslow": "Breslow, N.E. & Day, N.E. (1987). Statistical Methods in Cancer Research, Vol. II. IARC Scientific Publications 82.",
    "acs": "U.S. Census Bureau (2020). Understanding and Using American Community Survey Data: "
           "What All Data Users Need to Know (ACS General Handbook), ch. 7-8.",
    "vre": "U.S. Census Bureau. Variance Replicate Estimate Tables Documentation. "
           "https://www.census.gov/programs-surveys/acs/data/variance-tables.html",
    "design": "U.S. Census Bureau (2014). American Community Survey Design and Methodology, ch. 12-13.",
    "testing": "U.S. Census Bureau (2025). Instructions for Applying Statistical Testing to ACS Data.",
    "carroll": "Carroll, R.J., Ruppert, D., Stefanski, L.A. & Crainiceanu, C.M. (2006). Measurement "
               "Error in Nonlinear Models: A Modern Perspective, 2nd ed. Chapman & Hall/CRC.",
    "simex": "Cook, J.R. & Stefanski, L.A. (1994). JASA 89, 1314-1328; Stefanski, L.A. & Cook, J.R. "
             "(1995). JASA 90, 1247-1256; Devanarayan, V. & Stefanski, L.A. (2002). Stat. Prob. "
             "Letters 59, 219-225.",
    "fuller": "Fuller, W.A. (1987). Measurement Error Models. Wiley, sections 2.2 and 3.1.",
    "kline_santos": "Kline, P. and Santos, A. (2012). A score based approach to wild bootstrap inference. Journal of Econometric Methods 1(1), 23-41.",
    "hotelling_im": "Ibragimov, R. and Mueller, U.K. (2010). t-Statistic based correlation and heterogeneity robust inference. Journal of Business and Economic Statistics 28(4), 453-468; Hotelling, H. (1931). The generalization of Student's ratio. Annals of Mathematical Statistics 2(3), 360-378.",
    "cluster": "Cameron, A.C. & Miller, D.L. (2015). A practitioner's guide to cluster-robust inference. "
               "J. Human Resources 50, 317-372.",
    "standard_pop": "Klein, R.J. & Schoenborn, C.A. (2001). Age adjustment using the 2000 projected U.S. "
                    "population. Healthy People 2010 Statistical Notes 20. National Center for Health Statistics.",
    "fisher": "Fisher, R.A. (1921). On the probable error of a coefficient of correlation. Metron 1, 3-32.",
    "holm": "Holm, S. (1979). Scand. J. Statist. 6, 65-70.",
    "bh": "Benjamini, Y. & Hochberg, Y. (1995). JRSS-B 57, 289-300.",
    "by": "Benjamini, Y. & Yekutieli, D. (2001). Ann. Statist. 29, 1165-1188.",
    "bonferroni": "Dunn, O.J. (1961). JASA 56, 52-64.",
    "statsmodels": "Seabold, S. & Perktold, J. (2010). statsmodels: Econometric and statistical "
                   "modeling with Python. Proc. 9th Python in Science Conf.",
}


# ---------------------------------------------------------------------------
# Hashing, loading
# ---------------------------------------------------------------------------


def canonical_json(manifest: Mapping[str, Any]) -> str:
    """Canonical serialization: sorted keys, no whitespace, UTF-8 text."""
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# Manifests registered with scale 'X2' for an external count outcome before the robust-SE rule
# (Round 22: main study, X1, X2). They stay valid so the registered runs reproduce; new ones are refused.
LEGACY_X2_MANIFESTS = frozenset({
    "10c46acedc6eff827d8a41df34d272f839ed0d75804666e81b77ca75eab83ea6",
    "0d5e657b1bd86658ed950fd32eda96832614ae0e2ad1932cf1eddd6daeeaeba9",
    "9e83d6a0f361496ded30a95c8373f61fa924875ca62bd2252242312c8e8f6a79",
})


def manifest_hash(manifest: Mapping[str, Any]) -> str:
    """SHA-256 (hex) of :func:`canonical_json`."""
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def load_manifest(path_or_dict: Union[str, Path, Mapping[str, Any]]) -> Dict[str, Any]:
    if isinstance(path_or_dict, Mapping):
        return copy.deepcopy(dict(path_or_dict))
    with open(path_or_dict, encoding="utf-8") as f:
        return json.load(f)


def _table_of(var: Mapping[str, Any]) -> Optional[str]:
    if var.get("table"):
        return str(var["table"]).upper()
    m = YEAR_CODE_RE.match(str(var.get("ref", "")))
    return m.group(2).split("_")[0] if m else None


def _dataset_for(table: str) -> str:
    from ..api import infer_dataset
    return infer_dataset(table)


def manifest_states(geography: Mapping[str, Any]) -> List[Optional[str]]:
    """The geography's state selections: ``states`` as given, else ``[state]``
    (``[None]`` for levels that need no state)."""
    if geography.get("states") is not None:
        return [str(s) for s in geography["states"]]
    return [geography.get("state")]


def manifest_entities(geography: Mapping[str, Any], years: Optional[List[int]] = None) -> List[Any]:
    """Request entities for a manifest geography: one state's entities, or each
    listed state's entities in order (extracted per state and stacked)."""
    from ..pipeline import build_entities
    entities: List[Any] = []
    for st in manifest_states(geography):
        entities.extend(build_entities(geography["level"], st, geography.get("codes"), years=years))
    return entities


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def manifest_releases(manifest: Mapping[str, Any]) -> List[int]:
    """The manifest's integer releases, in order (anything else is reported by validate_manifest)."""
    releases = manifest.get("releases")
    return [r for r in releases if _is_int(r)] if isinstance(releases, list) else []


def release_overlap_message(releases: List[int], subject: str) -> Optional[str]:
    """None when the ACS 5-year periods of ``releases`` share no sample years, else why replicate
    SEs across them are refused (the trend module's overlap rule, census.trends.overlap_design_check)."""
    if len(set(releases)) < 2:
        return None
    from ..trends import overlap_design_check
    design = overlap_design_check(releases)
    if not design["overlapping"]:
        return None
    return (f"{subject} with overlapping 5-year periods: releases "
            f"{[(p['year1'], p['year2']) for p in design['overlapping_pairs']]} share sample years, and their "
            "replicates do not carry that covariance, so replicate SEs of analyses that combine or contrast them "
            f"would be wrong; use non-overlapping releases {design['suggested_nonoverlapping']}")


def _derivation_refs(d: Mapping[str, Any]) -> List[str]:
    """Every input name of a derivation (num/den and age_standardized groups;
    census.derived._spec_codes, the one shared walk)."""
    from ..derived import _spec_codes
    return _spec_codes(d)


def _variable_tables(manifest: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Manifest variable or derivation name -> the tables it is built from."""
    out: Dict[str, List[str]] = {}
    variables = manifest.get("variables")
    for v in variables if isinstance(variables, list) else []:
        if isinstance(v, Mapping) and v.get("name") is not None and _table_of(v):  # invalid entries: reported
            out[str(v["name"])] = [str(_table_of(v))]
    derivations = manifest.get("derivations")
    for d in derivations if isinstance(derivations, list) else []:
        if not isinstance(d, Mapping):  # reported by validate_manifest
            continue
        refs = _derivation_refs(d)
        out[str(d.get("name"))] = sorted({t for r in refs for t in out.get(str(r), [])})
    return out


def tables_and_refs(manifest: Mapping[str, Any]) -> Dict[str, List[str]]:
    """table code -> variable refs (in manifest order)."""
    out: Dict[str, List[str]] = {}
    for v in manifest.get("variables", []):
        t = _table_of(v)
        if t:
            out.setdefault(t, []).append(str(v["ref"]))
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


_SPEC_KEYS = ("formula", "error_covariates", "variables", "variable", "geoid", "variable_1", "variable_2")


def _spec_keys(a):
    spec = METHODS.get(a.get("method"))
    return tuple(dict.fromkeys(_SPEC_KEYS + (spec.required + spec.optional if spec else ())))


def _normalize_analysis(a: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the analysis with spec keys (formula, variables, ...) lifted from
    ``args`` to the top level, so either placement works the same way.
    Duplicates (a key both top-level and in args) are a validation error."""
    out = dict(a)
    args = dict(a.get("args") or {})
    for k in _spec_keys(a):
        if k in args and k not in out:
            out[k] = args.pop(k)
        elif k in args:
            args.pop(k)
    out["args"] = args
    return out


def _duplicate_spec_keys(a: Mapping[str, Any]) -> List[str]:
    args = a.get("args") or {}
    return [k for k in _spec_keys(a) if k in a and k in args]


def _formula_names(formula: str) -> List[str]:
    """Identifiers in a patsy formula that are not function calls or frame identifiers
    (GEOID, Year: e.g. ``C(Year)`` for a change between releases)."""
    names = []
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_.]*", str(formula)):
        tail = str(formula)[m.end():].lstrip()
        if (tail.startswith("(") or tail.startswith("=")) or m.group(0) in FORMULA_FUNCTIONS or "." in m.group(0) \
                or m.group(0) in FORMULA_ID_COLUMNS:
            continue
        names.append(m.group(0))
    return names


CONFIRMATORY_REPLICATE_POLICY = "strict"
# Manifest methods that use replicates; each runs with replicate_policy="strict".
# (Spatial, multilevel, DiD and PUMS analyses are not manifest methods; if added
# they must join this set so confirmatory runs refuse incomplete replicates.)

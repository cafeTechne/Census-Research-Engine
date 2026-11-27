# SPDX-License-Identifier: AGPL-3.0-or-later
"""External health-outcome data sources (PLAN_ROUND_21 B2).

A registry of public, keyless bulk sources whose estimates a manifest can join to
an ACS analysis frame (manifest ``external`` variables). Each source records what
it is, where it comes from, its licence, its geography vintage, the kind of
uncertainty its estimates carry, and the covariates of the model that produced
it, so that analyses can be checked for circularity (regressing a model-based
outcome on the model's own inputs partly recovers the model, not the world).

The first connector is CDC PLACES (model-based adult crude prevalences for
tracts and counties). Downloads are plain HTTPS CSV exports from the
data.cdc.gov Socrata portal, filtered to the requested states and measures; no
key and no app token. Every page is cached with a sidecar recording its URL,
SHA-256 and retrieval time (the same convention as the Census VRE files), and
the dataset's ``rowsUpdatedAt`` is recorded because Socrata datasets can be
revised in place. ``CENSUS_HEALTH_OFFLINE`` refuses downloads (cache only).
"""

import io
import json
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlencode

import numpy as np
import pandas as pd

from .block_weights import STATE_ABBR
from .geo import get_resource_path
from .replicate import _read_cached, _sha256, _sidecar_path, _write_cached

USER_AGENT = "census-research-engine/health-sources (research toolkit; python-requests)"
Z95 = 1.959963984540054
PAGE_SIZE = 50000
EXTERNAL_KEYS = ("name", "source", "release", "measure")
# optional keys per connector (validated in validate_external)
OPTIONAL_KEYS = {"usaleep": ("include_predicted", "apportion_to", "min_coverage", "split"),
                 "wonder": ("file", "sha256")}
# where an external variable may appear: only as the outcome of these methods (its error is independent
# of the ACS sampling error, so it enters the residual; as a covariate it would go uncorrected)
from .manifest.methods import EXTERNAL_OUTCOME_METHODS
JOIN_MISSING_LIMIT = 0.05
KINDS = ("direct", "model_based", "partly_model_based")

# The circularity rule (PLAN_ROUND_21 Part 2, C1), quoted by validation errors, the MCP instructions,
# docs/agent_protocol.md section 16 and list_health_sources.
CIRCULARITY_RULE = (
    "Determinant studies keep using the ACS's own measure (for disability: B18101) as the outcome, and use "
    "external sources such as CDC PLACES for measures the ACS lacks, such as diabetes. A model-based external "
    "outcome (PLACES, the PLACES-based County Health Rankings measures, USALEEP's predicted death rates) must not "
    "be tested against the inputs of the model that produced it: within a county, PLACES varies only with age, "
    "sex, race/ethnicity and education composition, so regressing it on those recovers CDC's model, not the "
    "world. Direct vital-records outcomes (County Health Rankings mortality, WONDER exports) have no such inputs.")

# ACS table families measuring the PLACES model's covariates (age-sex, race/ethnicity, education; poverty
# enters at county level). A table-level heuristic: a composition share built from another table's age
# cells (e.g. B18101) is not caught, so reports still state the caveat.
_PLACES_COVARIATES = {
    "age and sex": ("B01001", "B01002"),
    "race/ethnicity": ("B02001", "B03002", "B01001A", "B01001B", "B01001D", "B01001H", "B01001I"),
    "education": ("B15002", "B15003", "C15002", "B15001"),
    "poverty (county level in the model)": ("B17001", "C17002", "B17024", "B17020", "S1701"),
}
# USALEEP's predicted age-specific death rates (Arias et al. 2018, Vital Health Stat 2(181)): tract
# quartiles of median family income, population density, % non-Hispanic Black, % Hispanic, % with a
# bachelor's degree or higher (2010 census, ACS 2011-2015), a PRCSDA indicator and region.
_USALEEP_COVARIATES = {
    "income (median family income in the model)": ("B19113", "B19119", "B19101", "B19013", "B19001", "B19125",
                                                   "B19126"),
    "race/ethnicity": ("B03002", "B02001", "B03003", "B01001B", "B01001H", "B01001I"),
    "education": ("B15002", "B15003", "C15002", "B15001"),
    "population density": ("B01003",),
}
# ACS tables measuring the same construct directly ("*" = table-id prefix)
_DISABILITY_ANY = ("B18101", "B18135", "B18120", "B18130", "B18140", "C18108", "C18120", "C18121", "C18130",
                   "C18131", "S1810")
_PLACES_ACS_EQUIVALENT = {
    "DISABILITY": _DISABILITY_ANY,
    "HEARING": ("B18102", "S1810"), "VISION": ("B18103", "S1810"), "COGNITION": ("B18104", "S1810"),
    "MOBILITY": ("B18105", "S1810"), "SELFCARE": ("B18106", "S1810"), "INDEPLIVE": ("B18107", "S1810"),
    "ACCESS2": ("B27*", "C27*", "S2701", "S2702", "S2703", "S2704"),
    "FOODSTAMP": ("B22*", "S2201"),
}
_PLACES_MEASURES = (
    "ACCESS2", "ARTHRITIS", "BINGE", "BPHIGH", "BPMED", "CANCER", "CASTHMA", "CHD", "CHECKUP", "CHOLSCREEN",
    "COGNITION", "COLON_SCREEN", "COPD", "CSMOKING", "DENTAL", "DEPRESSION", "DIABETES", "DISABILITY",
    "EMOTIONSPT", "FOODINSECU", "FOODSTAMP", "GHLTH", "HEARING", "HIGHCHOL", "HOUSINSECU", "INDEPLIVE",
    "LACKTRPT", "LONELINESS", "LPA", "MAMMOUSE", "MHLTH", "MOBILITY", "OBESITY", "PHLTH", "SELFCARE",
    "SHUTUTILITY", "SLEEP", "STROKE", "TEETHLOST", "VISION",
)
_PLACES_MODEL_TEXT = (
    "multilevel logistic regression and post-stratification (MRP) of BRFSS responses: individual age, sex, "
    "race/ethnicity and education; county share of adults below 150% of the poverty line (ACS 5-year); state "
    "and county random effects; applied to census block population counts and aggregated to tracts. Within a "
    "county a tract's estimate varies only with its age, sex, race/ethnicity and education composition: the "
    "model has no tract-level health information")

# County Health Rankings & Roadmaps measures (analytic data column codes). Mortality measures are direct
# NCHS vital records with Census Population Estimates denominators; the BRFSS measures are CDC PLACES
# model estimates. Columns CHR&R takes from the ACS are not registered (use the ACS table).
_CHR_MEASURES = {
    "v037": {"label": "Low birth weight: share of live births under 2,500 grams", "kind": "direct",
             "unit": "proportion of live births (0-1)", "count": {"numerator": "low birth weight births",
             "denominator": "live births"},
             "data_source": "National Center for Health Statistics, Natality files (NVSS), 2017–2023"},
    "v001": {"label": "Premature death: years of potential life lost before age 75 per 100,000 (age-adjusted)",
             "kind": "direct", "unit": "YPLL per 100,000 population"},
    "v127": {"label": "Premature age-adjusted mortality: deaths under age 75 per 100,000 (age-adjusted)",
             "kind": "direct", "unit": "deaths per 100,000 population under 75"},
    "v147": {"label": "Life expectancy at birth", "kind": "direct", "unit": "years"},
    "v128": {"label": "Child mortality: deaths under age 20 per 100,000", "kind": "direct",
             "unit": "deaths per 100,000 population under 20"},
    "v129": {"label": "Infant mortality: deaths under age 1 per 1,000 live births", "kind": "direct",
             "unit": "deaths per 1,000 live births"},
    "v138": {"label": "Drug overdose deaths per 100,000", "kind": "direct", "unit": "deaths per 100,000"},
    "v135": {"label": "Injury deaths per 100,000", "kind": "direct", "unit": "deaths per 100,000"},
    "v060": {"label": "Diabetes prevalence (adults)", "kind": "model_based", "unit": "percent of adults",
             "model_source": "places"},
    "v144": {"label": "Frequent physical distress (adults)", "kind": "model_based", "unit": "percent of adults",
             "model_source": "places"},
    "v145": {"label": "Frequent mental distress (adults)", "kind": "model_based", "unit": "percent of adults",
             "model_source": "places"},
    "v036": {"label": "Poor physical health days (adults, average)", "kind": "model_based", "unit": "days",
             "model_source": "places"},
    "v042": {"label": "Poor mental health days (adults, average)", "kind": "model_based", "unit": "days",
             "model_source": "places"},
    "v009": {"label": "Adult smoking", "kind": "model_based", "unit": "percent of adults", "model_source": "places"},
    "v011": {"label": "Adult obesity", "kind": "model_based", "unit": "percent of adults", "model_source": "places"},
    "v070": {"label": "Physical inactivity", "kind": "model_based", "unit": "percent of adults",
             "model_source": "places"},
    "v180": {"label": "% Disability: functional limitations (adults)", "kind": "model_based",
             "unit": "percent of adults", "model_source": "places", "acs_equivalent": _DISABILITY_ANY},
}
# CHR&R columns built from ACS tables: refused with the table to use instead
CHR_ACS_DERIVED = {
    "v069": "B15003 (some college)", "v044": "B19080/B19081 (income inequality)", "v153": "B25003 (homeownership)",
    "v154": "B25070/B25091 (severe housing cost burden)", "v166": "B28002 (broadband access)",
    "v067": "B08301/B08101 (driving alone to work)", "v137": "B08303 (long commute)",
    "v059": "B16004/S1601 (not proficient in English)", "v082": "B23008 (children in single-parent households)",
}

SOURCES: Dict[str, Dict[str, Any]] = {
    "places": {
        "title": "CDC PLACES: Local Data for Better Health",
        "connector": "places",
        "publisher": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention "
                     "and Health Promotion, Division of Population Health",
        "licence": "Public Domain",
        "portal": "https://data.cdc.gov",
        "methodology_url": "https://www.cdc.gov/places/methodology/index.html",
        "releases": {
            2025: {
                "datasets": {"tract": "cwsq-ngmh", "county": "swc5-untb"},
                "data_years": "BRFSS 2023 (2022 for DENTAL, TEETHLOST, MAMMOUSE, COLON_SCREEN, SLEEP)",
                "tract_vintage": 2020,
                "poststratification": "decennial 2020 census block population counts",
            },
        },
        "measures": {m: {"kind": "model_based", "unit": "percent of adults aged 18 and over",
                         **({"acs_equivalent": _PLACES_ACS_EQUIVALENT[m]} if m in _PLACES_ACS_EQUIVALENT else {})}
                     for m in _PLACES_MEASURES},
        "kind": "model_based",
        "value_type": {"tract": "Crude prevalence", "county": "Crude prevalence"},
        "unit": "percent of adults aged 18 and over",
        "uncertainty": "model_based",
        "uncertainty_text": "model-based 95% interval (2.5th and 97.5th percentiles of 1,000 Monte Carlo draws); the "
                            "SE used here is (upper - lower) / (2 x 1.96), an approximation since percentile "
                            "intervals need not be symmetric",
        "model_text": _PLACES_MODEL_TEXT,
        "model_covariate_tables": _PLACES_COVARIATES,
        "join_missing_limit": JOIN_MISSING_LIMIT,
        "citation": "Centers for Disease Control and Prevention. PLACES: Local Data for Better Health, {release} "
                    "release. https://www.cdc.gov/places (data: data.cdc.gov dataset {dataset}).",
    },
    "usaleep": {
        "title": "U.S. Small-Area Life Expectancy Estimates Project (USALEEP)",
        "connector": "usaleep",
        "publisher": "National Center for Health Statistics, with NAPHSIS and the Robert Wood Johnson Foundation",
        "licence": "Public Domain (U.S. Government work)",
        "portal": "https://www.cdc.gov/nchs/nvss/usaleep/usaleep.html",
        "methodology_url": "https://www.cdc.gov/nchs/data/series/sr_02/sr02_181.pdf",
        "url_template": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/{st}_A.CSV",
        "releases": {
            2018: {"datasets": {"tract": "USALEEP A files"}, "data_years": "deaths 2010-2015",
                   "tract_vintage": 2010,
                   # New York City is a separate registration area with its own file; the NY file
                   # holds the other 57 counties
                   "extra_files": {"36": ("NYC",)}},
        },
        "measures": {"E0": {"kind": "partly_model_based", "unit": "years (life expectancy at birth)"}},
        "kind": "partly_model_based",
        "unit": "years (life expectancy at birth)",
        "uncertainty": "life_table_se",
        "uncertainty_text": "the published standard error of e(0) (Chiang's method, adjusted for small populations "
                            "and predicted rates)",
        "model_text": "abridged period life tables from 2010-2015 deaths; age groups with missing deaths take "
                      "PREDICTED death rates from a zero-truncated Poisson/negative-binomial model of tract "
                      "quartiles of median family income, population density, % non-Hispanic Black, % Hispanic "
                      "and % with a bachelor's degree or higher (2010 census, ACS 2011-2015), a "
                      "Purchased/Referred Care Service Delivery Area indicator and region (flag 2: predicted "
                      "for all ages; flag 3: observed and predicted; flag 1: observed only). Tracts under 5,000 "
                      "people over the period have no estimate; Maine and Wisconsin were added in a second "
                      "phase",
        "model_covariate_tables": _USALEEP_COVARIATES,
        # 11.2% of tracts unpublished nationally, plus flag-2 tracts when dropped (7% of published)
        "join_missing_limit": 0.25,
        "citation": "Arias E, Escobedo LA, Kennedy J, Fu C, Cisewski J. U.S. Small-area Life Expectancy Estimates "
                    "Project: Methodology and Results Summary. National Center for Health Statistics. Vital "
                    "Health Stat 2(181). 2018 (data: USALEEP census tract life expectancy files, {dataset}).",
    },
    "chr": {
        "title": "County Health Rankings & Roadmaps analytic data",
        "connector": "chr",
        "publisher": "University of Wisconsin Population Health Institute",
        "licence": "CHR&R terms of use: personal or non-profit (educational, research, public health) use; "
                   "not for commercial use; cite the source; no affiliation or endorsement implied. The engine "
                   "caches the file and does not redistribute it",
        "portal": "https://www.countyhealthrankings.org",
        "methodology_url": "https://www.countyhealthrankings.org/health-data/methodology-and-sources",
        "releases": {
            2025: {"datasets": {"county": "analytic_data2025_v2.csv"},
                   "url": "https://www.countyhealthrankings.org/sites/default/files/media/document/"
                          "analytic_data2025_v2.csv",
                   "data_years": "per measure; premature death and premature age-adjusted mortality: NCHS "
                                 "mortality 2020-2022"},
        },
        "measures": _CHR_MEASURES,
        "kind": "direct",
        "unit": "per measure",
        "uncertainty": "published_ci",
        "uncertainty_text": "published 95% interval; SE = (upper - lower) / (2 x 1.96)",
        "model_text": "mortality measures: NCHS death records by county of residence, Census Population Estimates "
                      "denominators, missing for fewer than 20 deaths; BRFSS measures: CDC PLACES model "
                      "estimates (" + _PLACES_MODEL_TEXT + ")",
        "model_covariate_tables": _PLACES_COVARIATES,  # applies to model_based measures only
        "join_missing_limit": JOIN_MISSING_LIMIT,
        "citation": "University of Wisconsin Population Health Institute. County Health Rankings & Roadmaps "
                    "{release}. www.countyhealthrankings.org (data: {dataset}).",
    },
    "wonder": {
        "title": "CDC WONDER export (user-supplied)",
        "connector": "wonder",
        "publisher": "Centers for Disease Control and Prevention, National Center for Health Statistics",
        "licence": "CDC WONDER data use restrictions (no identification of individuals; suppression of counts "
                   "under 10 respected)",
        "portal": "https://wonder.cdc.gov",
        "methodology_url": "https://wonder.cdc.gov/wonder/help/ucd.html",
        "releases": {None: {"datasets": {"county": "export", "state": "export"}}},
        "measures": {"deaths": {"kind": "direct", "unit": "deaths"},
                     "crude_rate": {"kind": "direct", "unit": "deaths per 100,000"},
                     "age_adjusted_rate": {"kind": "direct", "unit": "deaths per 100,000 (age-adjusted)"}},
        "kind": "direct",
        "unit": "per measure",
        "uncertainty": "poisson",
        "uncertainty_text": "crude rates: exact Poisson (Garwood) intervals; age-adjusted rates: WONDER's "
                            "exported standard error; suppressed counts (1-9) are censored, never zero",
        "model_text": "death certificate counts by county of residence (no model)",
        "model_covariate_tables": {},
        "join_missing_limit": JOIN_MISSING_LIMIT,
        "citation": "Centers for Disease Control and Prevention, National Center for Health Statistics. CDC "
                    "WONDER ({dataset}).",
    },
}


def measure_info(source: str, measure: Any) -> Dict[str, Any]:
    """Registry record of one measure (``kind``, ``unit``, optional ``acs_equivalent``, ``model_source``)."""
    info = source_info(source)
    key = _measure_key(source, measure)
    if key not in info["measures"]:
        raise ValueError(f"measure {measure!r} is not a {source} measure")
    return info["measures"][key]


def _measure_key(source: str, measure: Any) -> str:
    m = str(measure)
    return m.lower() if source in ("chr", "wonder") else m.upper()


def measure_kind(source: str, measure: Any) -> str:
    return measure_info(source, measure).get("kind", source_info(source).get("kind", "direct"))


def model_covariates(source: str, measure: Any) -> Dict[str, tuple]:
    """ACS table families of the model that produced ``measure`` (empty for direct measures)."""
    if measure_kind(source, measure) == "direct":
        return {}
    return dict(source_info(source).get("model_covariate_tables") or {})


def _table_matches(table: str, patterns: Iterable[str]) -> bool:
    t = str(table).upper()
    for p in patterns:
        p = p.upper()
        if p.endswith("*"):
            if t.startswith(p[:-1]):
                return True
        elif t == p or t.startswith(p + "_"):
            return True
    return False


def acs_equivalent(source: str, measure: Any) -> tuple:
    """ACS tables that measure the same construct directly (empty when the ACS lacks it)."""
    return tuple(measure_info(source, measure).get("acs_equivalent") or ())


def equivalent_tables(source: str, measure: Any, tables: Iterable[str]) -> List[str]:
    """``tables`` that measure ``measure``'s construct directly in the ACS."""
    eq = acs_equivalent(source, measure)
    return sorted({str(t) for t in tables if eq and _table_matches(t, eq)})


_CHR_DIRECT_TEXT = ("NCHS death (and birth) records by county of residence, Census Population Estimates "
                    "denominators; missing for fewer than 20 deaths")


def source_text(source: str, measure: Any) -> str:
    """How ``measure`` was produced: the measure's own text when the source mixes kinds (CHR&R), else the
    source's model text."""
    info = source_info(source)
    if source == "chr":
        if measure == "v037":
            return _CHR_MEASURES["v037"]["data_source"]
        try:
            kind = measure_kind(source, measure)
        except ValueError:
            return info["model_text"]
        return _CHR_DIRECT_TEXT if kind == "direct" else "CDC PLACES model estimate (" + _PLACES_MODEL_TEXT + ")"
    return info["model_text"]


def kind_phrase(source: str, measure: Any) -> str:
    k = measure_kind(source, measure)
    return {"direct": "an external direct estimate (vital records, no model inputs)",
            "model_based": "an external model-based estimate",
            "partly_model_based": "an external, partly model-based estimate"}[k]


class HealthSourceError(RuntimeError):
    """An external health source could not be fetched, parsed or joined."""


def health_cache_dir() -> str:
    """$CENSUS_HEALTH_DIR or <repo>/.cache/health."""
    return os.getenv("CENSUS_HEALTH_DIR") or get_resource_path(os.path.join(".cache", "health"))


def _offline() -> bool:
    return os.getenv("CENSUS_HEALTH_OFFLINE", "").strip() not in ("", "0", "false", "False")


def source_info(source: str) -> Dict[str, Any]:
    if source not in SOURCES:
        raise ValueError(f"unknown external source {source!r}; known: {sorted(SOURCES)}")
    return SOURCES[source]


def dataset_id(source: str, release: int, level: str) -> str:
    info = source_info(source)
    rel = info["releases"].get(int(release))
    if rel is None:
        raise ValueError(f"{source}: release {release} not registered (known: {sorted(info['releases'])})")
    ds = rel["datasets"].get(level)
    if ds is None:
        raise ValueError(f"{source} {release}: no dataset for geography level {level!r} "
                         f"(available: {sorted(rel['datasets'])})")
    return ds


def _required_keys(source: str) -> tuple:
    return ("name", "source", "measure", "file", "sha256") if source == "wonder" else EXTERNAL_KEYS


def external_vintage(entry: Mapping[str, Any]) -> Optional[int]:
    """Tract vintage of an external entry's values after any apportionment (None when undefined)."""
    info = source_info(str(entry["source"]))
    rel = info["releases"].get(entry.get("release"))
    if entry.get("apportion_to") is not None:
        a = entry["apportion_to"]
        return a if isinstance(a, int) and not isinstance(a, bool) else None
    return (rel or {}).get("tract_vintage")


def resolve_external_file(path: str) -> str:
    """A WONDER export path: absolute, or relative to the repository root (not the process cwd), so the
    hashed manifest means the same file wherever the server runs."""
    return path if os.path.isabs(path) else get_resource_path(path)


def _wonder_file_errors(e: Mapping[str, Any]) -> List[str]:
    """Pre-registration check of a WONDER entry: the export exists and matches its pinned SHA-256."""
    path = resolve_external_file(str(e["file"]))
    if not os.path.exists(path):
        return [f"WONDER export {e['file']!r} not found (relative paths resolve against the repository root: "
                f"{path}); export it before pre-registering, so the hash pins the data"]
    from .pipeline import file_sha256
    got = file_sha256(path)
    if got != str(e["sha256"]).lower():
        return [f"WONDER export {e['file']!r} has SHA-256 {got}, not the pinned {e['sha256']}"]
    return []


def validate_external(entries: Any, geography: Mapping[str, Any], releases: Sequence[int],
                      taken_names: Iterable[str]) -> List[str]:
    """Errors for a manifest's ``external`` list (empty when valid). Offline: checks the registry only."""
    errors: List[str] = []
    if not isinstance(entries, list) or not entries:
        return ["external must be a non-empty list of {name, source, release, measure} objects"]
    taken = set(taken_names)
    seen: Dict[tuple, str] = {}
    level = str(geography.get("level", ""))
    if len(list(releases)) > 1:
        errors.append("external variables need a single ACS release (one row per unit to join on GEOID; external "
                      "values are not release-specific)")
    for i, e in enumerate(entries):
        if not isinstance(e, Mapping):
            errors.append(f"external[{i}]: must be an object")
            continue
        source = str(e.get("source"))
        if source not in SOURCES:
            errors.append(f"external[{i}]: unknown external source {e.get('source')!r}; known: {sorted(SOURCES)}")
            continue
        required = _required_keys(source)
        allowed = set(required) | set(OPTIONAL_KEYS.get(source, ())) | ({"release"} if source == "wonder" else set())
        extra = sorted(set(e) - allowed)
        missing = [k for k in required if k not in e]
        if extra:
            errors.append(f"external[{i}]: unknown keys {extra} for source {source!r} (allowed: {sorted(allowed)})")
        if missing:
            errors.append(f"external[{i}]: needs {missing}")
            continue
        name = str(e["name"])
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            errors.append(f"external[{i}]: name {name!r} must be an identifier")
        if name in taken:
            errors.append(f"external[{i}]: name {name!r} is already a variable, derivation or external name")
        taken.add(name)
        info = source_info(source)
        release = e.get("release")
        if source == "wonder":
            if level not in info["releases"][None]["datasets"]:
                errors.append(f"external[{i}]: wonder exports are joined at county or state level, not {level!r}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(e["sha256"])):
                errors.append(f"external[{i}]: sha256 must be the export file's 64-hex SHA-256 (pins the file)")
        else:
            try:
                if not isinstance(release, int) or isinstance(release, bool):
                    raise ValueError(f"release must be an integer year, got {release!r}")
                dataset_id(source, release, level)
            except ValueError as exc:
                errors.append(f"external[{i}]: {exc}")
                continue
        mkey = _measure_key(source, e["measure"])
        if mkey not in info["measures"]:
            hint = (f"; {mkey} is an ACS-derived CHR&R column: use the ACS table {CHR_ACS_DERIVED[mkey]} directly"
                    if source == "chr" and mkey in CHR_ACS_DERIVED else "")
            errors.append(f"external[{i}]: measure {e['measure']!r} is not a {source} measure{hint}")
        key = (source, release, mkey) if source != "wonder" else (source, str(e.get("sha256")).lower(), mkey)
        if key in seen:
            errors.append(f"external[{i}]: {key[0]} {key[1]} {key[2]} is already external {seen[key]!r}; name each "
                          "measure once")
        seen.setdefault(key, name)
        if source == "usaleep":
            if "include_predicted" in e and not isinstance(e["include_predicted"], bool):
                errors.append(f"external[{i}]: include_predicted must be true or false")
            if "apportion_to" in e and e["apportion_to"] != 2020:
                errors.append(f"external[{i}]: apportion_to must be 2020 (USALEEP is on 2010 tracts)")
            if "split" in e and (e["split"] not in SPLIT_POLICIES or "apportion_to" not in e):
                errors.append(f"external[{i}]: split must be one of {SPLIT_POLICIES} and needs apportion_to "
                              "('inherit' failed validation: docs/audits/rate_apportionment_validation.md)")
            if "min_coverage" in e:
                mc = e["min_coverage"]
                if isinstance(mc, bool) or not isinstance(mc, (int, float)) or not 0.5 <= mc <= 1:
                    errors.append(f"external[{i}]: min_coverage must be a number in [0.5, 1]")
                elif "apportion_to" not in e:
                    errors.append(f"external[{i}]: min_coverage applies only with apportion_to")
        if source == "wonder":
            errors.extend(f"external[{i}]: {m}" for m in _wonder_file_errors(e))
        if level == "tract" and external_vintage(e) is not None:
            from .geo_crosswalk import tract_vintage
            vintage = external_vintage(e)
            target = geography.get("harmonize_tracts_to")
            if target is not None:
                if target != vintage:
                    errors.append(f"external[{i}]: {source} {release} values are on {vintage} tracts; "
                                  f"harmonize_tracts_to is {target}")
            else:
                other = []
                try:
                    other = [r for r in releases if tract_vintage(int(r)) != vintage]
                except ValueError as exc:  # pre-2010 tracts
                    errors.append(f"external[{i}]: {exc}")
                if other:
                    fix = (" or apportion_to 2020" if source == "usaleep" and vintage == 2010 else "")
                    errors.append(f"external[{i}]: {source} {release} values are on {vintage} tracts; ACS releases "
                                  f"{other} use the other tract vintage (set geography.harmonize_tracts_to to "
                                  f"{vintage}{fix})")
    if geography.get("states") is None and geography.get("state") in (None, "all"):
        errors.append("external: needs geography.state or geography.states (downloads are filtered by state)")
    return errors


def circularity_overlap(source: str, tables: Iterable[str], measure: Any = None) -> Dict[str, List[str]]:
    """Model-covariate families of ``source`` (of ``measure``'s model, when given; none for a direct
    measure) that ``tables`` (ACS table ids) belong to."""
    fam = model_covariates(source, measure) if measure is not None else (
        source_info(source).get("model_covariate_tables") or {})
    tables = {str(t).upper() for t in tables}
    out: Dict[str, List[str]] = {}
    for label, ids in fam.items():
        hit = sorted(t for t in tables if _table_matches(t, ids))
        if hit:
            out[label] = hit
    return out


def join_limit(entries: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    """The external_join_failed limit of each external variable (its source's ``join_missing_limit``)."""
    return {str(e["name"]): float(source_info(str(e["source"])).get("join_missing_limit", JOIN_MISSING_LIMIT))
            for e in entries if str(e.get("source")) in SOURCES}


def registry_summary(source: Optional[str] = None) -> Dict[str, Any]:
    """JSON-ready registry (for the MCP tool list_health_sources), with the circularity rule."""
    out = {"rule": CIRCULARITY_RULE, "use_limits": (
        "External variables may only be the outcome of " + ", ".join(EXTERNAL_OUTCOME_METHODS) + " (alone). "
        "create_manifest refuses (R1) an outcome whose construct the ACS measures directly unless the analysis "
        "compares it with that ACS measure and only such terms are tested, and (R2) a tested term built from "
        "the outcome model's own inputs unless the hypothesis has a written circularity_justification."),
        "sources": {}}
    for name, info in SOURCES.items():
        if source is not None and name != source:
            continue
        out["sources"][name] = {
            "title": info["title"], "kind": info.get("kind"), "licence": info["licence"],
            "releases": {str(r): {"levels": sorted(v["datasets"]), **{k: v[k] for k in ("data_years", "tract_vintage")
                                                                       if k in v}}
                         for r, v in info["releases"].items()},
            "model": info["model_text"], "uncertainty": info["uncertainty_text"],
            "model_covariate_tables": {k: list(v) for k, v in (info.get("model_covariate_tables") or {}).items()},
            "measures": {m: {k: (list(v) if isinstance(v, tuple) else v) for k, v in rec.items()}
                         for m, rec in info["measures"].items()},
            "optional_keys": list(OPTIONAL_KEYS.get(name, ())),
            "methodology_url": info.get("methodology_url"),
        }
        if name == "chr":
            out["sources"][name]["refused_acs_derived"] = CHR_ACS_DERIVED
    if source is not None and source not in SOURCES:
        raise ValueError(f"unknown external source {source!r}; known: {sorted(SOURCES)}")
    return out


# ---------------------------------------------------------------------------
# Download and cache
# ---------------------------------------------------------------------------


def _http_get(url: str, session: Any = None, timeout: float = 300.0) -> bytes:
    from .http import polite_get
    resp = polite_get(url, user_agent=USER_AGENT, error=HealthSourceError, session=session, timeout=timeout)
    if resp.status_code != 200:
        raise HealthSourceError(f"HTTP {resp.status_code} for {url}")
    return resp.content or b""


def _side(path: str) -> Dict[str, Any]:
    with open(_sidecar_path(path), encoding="utf-8") as f:
        return json.load(f)


def _states_abbr(states: Sequence[str]) -> List[str]:
    out = []
    for s in states:
        code = str(s).zfill(2)
        if code not in STATE_ABBR:
            raise ValueError(f"unknown state FIPS {s!r}")
        out.append(STATE_ABBR[code])
    return out


def places_query_url(ds: str, states: Sequence[str], measures: Sequence[str], offset: int, limit: int) -> str:
    """Socrata CSV export of crude prevalences (datavaluetypeid CrdPrv) for ``states`` and ``measures``;
    (locationid, measureid) is unique among them, so offset paging is deterministic."""
    sts = ",".join(f"'{a}'" for a in _states_abbr(states))
    ms = ",".join(f"'{m}'" for m in measures)
    params = {"$where": f"stateabbr in({sts}) AND measureid in({ms}) AND datavaluetypeid='CrdPrv'",
              "$order": "locationid,measureid",
              "$limit": str(limit), "$offset": str(offset)}
    return f"https://data.cdc.gov/resource/{ds}.csv?" + urlencode(params)


def fetch_places(
    release: int,
    level: str,
    states: Sequence[str],
    measures: Sequence[str],
    fetch: Optional[Callable[[str], bytes]] = None,
    cache_dir: Optional[str] = None,
    session: Any = None,
) -> Dict[str, Any]:
    """Raw PLACES rows for ``states`` and ``measures`` (cached), with provenance.

    Returns {"rows": DataFrame (the CSV columns), "files": [{url, path, sha256, size_bytes,
    downloaded_at}], "rows_updated_at": int or None, "dataset": id}. ``fetch(url) -> bytes`` replaces the
    HTTP client (tests). Pages of PAGE_SIZE rows are requested until a short page.
    """
    ds = dataset_id("places", release, level)
    measures = sorted({str(m).upper() for m in measures})
    unknown = [m for m in measures if m not in SOURCES["places"]["measures"]]
    if unknown:
        raise ValueError(f"unknown PLACES measures {unknown}")
    states = sorted({str(s).zfill(2) for s in states})
    get = fetch or (lambda u: _http_get(u, session=session))
    key = _sha256(json.dumps([states, measures]).encode())[:12]
    folder = os.path.join(cache_dir or health_cache_dir(), "places", str(release), level)
    meta_url = f"https://data.cdc.gov/api/views/{ds}.json"
    meta_path = os.path.join(folder, f"{ds}_{key}_metadata.json")
    files: List[Dict[str, Any]] = []
    frames: List[pd.DataFrame] = []
    fresh = False
    offset = 0
    while True:
        url = places_query_url(ds, states, measures, offset, PAGE_SIZE)
        path = os.path.join(folder, f"{ds}_{key}_{offset}.csv")
        # None from the cache when absent or not matching its sidecar SHA-256: then fetched again
        raw, rec, got_fresh = _cached_file(path, url, get, "text/csv")
        fresh = fresh or got_fresh
        files.append(rec)
        try:
            page = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception as exc:  # noqa: BLE001
            raise HealthSourceError(f"{url}: not a CSV ({exc})") from exc
        frames.append(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # the revision stamp belongs to this download: fetched with fresh pages, read from the cache only
    # when every page came from it (a stamp that cannot be fetched is recorded as unknown)
    raw_meta = None if fresh else _read_cached(meta_path)
    if raw_meta is None:
        for p in (meta_path, _sidecar_path(meta_path)):
            if os.path.exists(p):
                os.remove(p)
        if not _offline():
            try:
                raw_meta = get(meta_url)
                json.loads(raw_meta)
                _write_cached(meta_path, raw_meta, meta_url, "application/json")
            except Exception:  # noqa: BLE001 - the revision stamp is provenance only
                raw_meta = None
    updated = None
    if raw_meta is not None:
        try:
            updated = json.loads(raw_meta).get("rowsUpdatedAt")
        except ValueError:
            updated = None
    return {"rows": rows, "files": files, "rows_updated_at": updated, "dataset": ds}


def parse_places(rows: pd.DataFrame, level: str, measure_names: Mapping[str, str]) -> pd.DataFrame:
    """Wide frame GEOID, <name>, <name>_se, <name>_ci_lower, <name>_ci_upper for ``measure_names``
    ({measure id: frame name}). Raises on malformed or duplicated rows."""
    need = ("locationid", "measureid", "data_value", "low_confidence_limit", "high_confidence_limit",
            "data_value_type")
    missing = [c for c in need if c not in rows.columns]
    if missing:
        raise HealthSourceError(f"PLACES rows lack columns {missing}")
    width = {"tract": 11, "county": 5}[level]
    want = SOURCES["places"]["value_type"][level]
    sub = rows[rows["measureid"].str.upper().isin(list(measure_names))].copy()
    sub = sub[sub["data_value_type"] == want]
    geo = sub["locationid"].astype(str).str.strip()
    bad = ~geo.str.fullmatch(rf"\d{{{width}}}")
    if bad.any():
        raise HealthSourceError(f"PLACES rows with malformed {level} ids: {sorted(geo[bad].unique())[:5]}")
    sub["GEOID"] = geo
    dup = sub.duplicated(["GEOID", "measureid"])
    if dup.any():
        raise HealthSourceError(f"duplicated PLACES rows for {int(dup.sum())} GEOID-measure pairs")
    out = pd.DataFrame({"GEOID": sorted(sub["GEOID"].unique())})
    for mid, name in measure_names.items():
        part = sub[sub["measureid"].str.upper() == mid].set_index("GEOID")
        vals = {}
        for col, src in (("", "data_value"), ("_ci_lower", "low_confidence_limit"),
                         ("_ci_upper", "high_confidence_limit")):
            raw = part[src]
            num = pd.to_numeric(raw, errors="coerce")
            nonnum = raw.notna() & raw.astype(str).str.strip().ne("") & num.isna()
            if nonnum.any():
                raise HealthSourceError(f"PLACES {mid}: non-numeric {src} values")
            vals[col] = num
        df = pd.DataFrame({name: vals[""], f"{name}_ci_lower": vals["_ci_lower"],
                           f"{name}_ci_upper": vals["_ci_upper"]})
        df[f"{name}_se"] = (df[f"{name}_ci_upper"] - df[f"{name}_ci_lower"]) / (2 * Z95)
        out = out.merge(df.reset_index(), on="GEOID", how="left")
    return out


def _cached_file(path: str, url: str, get: Callable[[str], bytes], content_type: str,
                 html_check: bool = True) -> "tuple[bytes, Dict[str, Any], bool]":
    """Bytes of ``url`` from the SHA-256-checked cache, else downloaded and cached; with the sidecar record
    and whether it was downloaded now."""
    raw = _read_cached(path)
    fresh = raw is None
    if raw is None:
        if _offline():
            raise HealthSourceError(f"{path} not cached and CENSUS_HEALTH_OFFLINE is set")
        raw = get(url)
        if html_check and raw[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
            raise HealthSourceError(f"{url} returned an HTML page, not data; nothing cached")
        _write_cached(path, raw, url, content_type)
    side = _side(path)
    return raw, {k: side.get(k) for k in ("source_url", "sha256", "size_bytes", "downloaded_at")} | {"path": path}, fresh


# ---------------------------------------------------------------------------
# USALEEP (tract life expectancy 2010-2015, 2010 tracts)
# ---------------------------------------------------------------------------


def fetch_usaleep(states: Sequence[str], fetch: Optional[Callable[[str], bytes]] = None,
                  cache_dir: Optional[str] = None, session: Any = None) -> Dict[str, Any]:
    """Raw USALEEP A-file rows for ``states`` (cached per state), with provenance."""
    info = SOURCES["usaleep"]
    get = fetch or (lambda u: _http_get(u, session=session))
    folder = os.path.join(cache_dir or health_cache_dir(), "usaleep", "2018")
    frames, files, names = [], [], []
    extra = info["releases"][2018]["extra_files"]
    for st in sorted({str(s).zfill(2) for s in states}):
        for abbr in (_states_abbr([st])[0],) + tuple(extra.get(st, ())):
            url = info["url_template"].format(st=abbr)
            raw, rec, _ = _cached_file(os.path.join(folder, f"{abbr}_A.CSV"), url, get, "text/csv")
            files.append(rec)
            names.append(abbr)
            try:
                part = pd.read_csv(io.BytesIO(raw), dtype=str)
            except Exception as exc:  # noqa: BLE001
                raise HealthSourceError(f"{url}: not a CSV ({exc})") from exc
            if "Tract ID" in part.columns and not part["Tract ID"].astype(str).str.startswith(st).all():
                raise HealthSourceError(f"{url}: rows outside state {st}")
            frames.append(part)
    rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return {"rows": rows, "files": files, "dataset": "USALEEP A files (" + ", ".join(names) + ")",
            "rows_updated_at": None}


def parse_usaleep(rows: pd.DataFrame, name: str, include_predicted: bool = False) -> "tuple[pd.DataFrame, Dict]":
    """Frame GEOID (Census 2010 tract code), <name>, <name>_se, <name>_flag; flag-2 (fully predicted)
    tracts dropped unless ``include_predicted``. Returns (frame, record of the drop)."""
    need = ("Tract ID", "e(0)", "se(e(0))", "Abridged life table flag")
    miss = [c for c in need if c not in rows.columns]
    if miss:
        raise HealthSourceError(f"USALEEP rows lack columns {miss}")
    geo = rows["Tract ID"].astype(str).str.strip()
    bad = ~geo.str.fullmatch(r"\d{11}")
    if bad.any():
        raise HealthSourceError(f"USALEEP rows with malformed tract ids: {sorted(geo[bad].unique())[:5]}")
    if geo.duplicated().any():
        raise HealthSourceError(f"duplicated USALEEP tracts: {sorted(geo[geo.duplicated()].unique())[:5]}")
    vals = {}
    for col, src in ((name, "e(0)"), (f"{name}_se", "se(e(0))"), (f"{name}_flag", "Abridged life table flag")):
        raw = rows[src]
        num = pd.to_numeric(raw, errors="coerce")
        if (raw.notna() & raw.astype(str).str.strip().ne("") & num.isna()).any():
            raise HealthSourceError(f"USALEEP: non-numeric {src} values")
        vals[col] = num.to_numpy()
    out = pd.DataFrame({"GEOID": geo.to_numpy(), **vals})
    if not out[f"{name}_flag"].dropna().isin([1, 2, 3]).all():
        raise HealthSourceError("USALEEP: abridged life table flag outside 1-3")
    counts = {int(k): int(v) for k, v in out[f"{name}_flag"].value_counts().items()}
    predicted = out[f"{name}_flag"] == 2
    record = {"flag_counts": counts, "include_predicted": bool(include_predicted),
              "dropped_fully_predicted": 0 if include_predicted else int(predicted.sum())}
    if not include_predicted:
        out = out[~predicted].reset_index(drop=True)
    return out, record


SPLIT_POLICIES = ("missing", "inherit", "dominant")


def apportion_rates(values: pd.DataFrame, name: str, crosswalk: pd.DataFrame,
                    min_coverage: float = 0.9, split: str = "missing") -> "tuple[pd.DataFrame, Dict[str, Any]]":
    """Population-mass-weighted means of ``name`` from source to target tracts.

    ``split``: a target whose only source tract is split across several targets would inherit its
    parent's value. That failed validation (docs/audits/rate_apportionment_validation.md: median
    |z| 1.33 x the 1:1 targets' against a 1.25 limit), so by default (``"missing"``) such targets
    are left missing; ``"inherit"`` keeps the parent's value (not validated).

    ``crosswalk``: source_geoid, target_geoid, mass (population of the intersection, e.g.
    census.block_weights.tract_weights(..., weight="population")). value_t = sum_s m_st v_s / sum_s m_st over
    sources with a value; SE = sqrt(sum_s a_st^2 se_s^2), a_st = m_st / sum m_st (independent sources).
    A target whose covered mass is below ``min_coverage`` of its total mass is left missing.
    """
    if "mass" not in crosswalk.columns:
        raise HealthSourceError("rate apportionment needs crosswalk masses (block population weights)")
    if split not in SPLIT_POLICIES:
        raise ValueError(f"split must be one of {SPLIT_POLICIES}")
    cw = crosswalk[["source_geoid", "target_geoid", "mass"]].astype({"source_geoid": str, "target_geoid": str})
    v = values[["GEOID", name, f"{name}_se"]].rename(columns={"GEOID": "source_geoid"})
    m = cw.merge(v, on="source_geoid", how="left")
    total = m.groupby("target_geoid")["mass"].sum()
    ok = m[np.isfinite(m[name].to_numpy(float)) & np.isfinite(m[f"{name}_se"].to_numpy(float))].copy()
    covered = ok.groupby("target_geoid")["mass"].sum()
    ok["mv"] = ok["mass"] * ok[name]
    ok["m2s2"] = ok["mass"] ** 2 * ok[f"{name}_se"] ** 2
    agg = ok.groupby("target_geoid")[["mv", "m2s2"]].sum()
    cov = (covered / total.reindex(covered.index)).fillna(0.0)
    out = pd.DataFrame({"GEOID": agg.index.astype(str),
                        name: (agg["mv"] / covered).to_numpy(),
                        f"{name}_se": (np.sqrt(agg["m2s2"]) / covered).to_numpy(),
                        f"{name}_coverage": cov.reindex(agg.index).to_numpy()})
    low = out[f"{name}_coverage"] < min_coverage
    out.loc[low, [name, f"{name}_se"]] = np.nan
    nsrc = cw.groupby("target_geoid")["source_geoid"].nunique()
    ntgt = cw.groupby("source_geoid")["target_geoid"].nunique()
    kinds = target_relationships(cw)
    split_targets = set(kinds.index[kinds == "split"])
    is_split = out["GEOID"].isin(split_targets).to_numpy()
    if split == "missing":
        out.loc[is_split, [name, f"{name}_se"]] = np.nan
    dominant_missing = np.zeros(len(out), dtype=bool)
    if split == "dominant":
        parent_mass = cw.groupby("source_geoid")["mass"].transform("sum")
        pieces = cw.assign(parent_share=cw["mass"] / parent_mass)
        share = pieces.groupby(["source_geoid", "target_geoid"])["parent_share"].sum().groupby("target_geoid").max()
        dominant_missing = is_split & (out["GEOID"].map(share).fillna(0).to_numpy() < .95)
        out.loc[dominant_missing, [name, f"{name}_se"]] = np.nan

    record = {"method": "population-mass-weighted mean of source tract values (2010 block population), SE from "
                        "independent source SEs; life expectancy is not additive, so this is an approximation"
                        + (" (a split tract inherits its parent's value, NOT validated)" if split == "inherit" else
                           " (a target whose only source is split across several targets is left missing)"),
              "min_coverage": float(min_coverage), "targets": int(len(out)), "split_policy": split,
              "split_targets": int(is_split.sum()),
              "split_targets_left_missing": int(is_split.sum()) if split == "missing" else int(dominant_missing.sum()),
              "targets_below_coverage": int(low.sum()),
              "targets_from_several_sources": int((nsrc > 1).sum()),
              "sources_split_across_targets": int((ntgt > 1).sum())}
    if split == "dominant":
        record["method"] = ("population-mass-weighted mean; split children inherit their parent only at parent "
                            "population share >=0.95, otherwise missing; validated on held-out OH/PA, "
                            "docs/audits/rate_apportionment_retest.md; life expectancy remains an approximation")
        record["parent_share_min"] = .95
    return out.reset_index(drop=True), record


def target_relationships(crosswalk: pd.DataFrame) -> pd.Series:
    """Per target tract: "1:1" (one source tract mapping only to it), "split" (one source tract that
    also maps to other targets) or "merged/complex" (several sources)."""
    cw = crosswalk.astype({"source_geoid": str, "target_geoid": str})
    nsrc = cw.groupby("target_geoid")["source_geoid"].nunique()
    ntgt = cw.groupby("source_geoid")["target_geoid"].nunique()
    first = cw.groupby("target_geoid")["source_geoid"].first()
    kind = pd.Series("merged/complex", index=nsrc.index)
    single = nsrc == 1
    kind[single] = np.where(ntgt.reindex(first[single]).to_numpy() == 1, "1:1", "split")
    return kind

from census.health_sources_io import (  # noqa: E402, F401
    _provenance,
    fetch_chr,
    join_external,
    load_external,
    parse_chr,
)

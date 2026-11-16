# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pre-registered analysis manifests (PLAN_ROUND_8 workstream D).

A manifest is a JSON document that fixes an analysis before any data are
pulled. Schema (``schema_version`` 1)::

    {
      "schema_version": 1,
      "title": "Income and poverty in NY tracts",
      "authors": ["human:jdoe", "agent:claude"],           # identity convention of overrides
      "created": "2026-11-02T12:00:00Z",                    # ISO 8601
      "releases": [2019],                                   # ACS 5-year end years
      "geography": {"level": "tract", "state": "36", "codes": ["061"]},
                   # or several states, stacked: {"level": "county", "states": ["26", "36"]}
                   # tracts across the 2010/2020 redraw: add "harmonize_tracts_to": 2020
      "variables": [                                        # YEAR:CODE or concept IDs
        {"name": "income", "ref": "2019:B19013_001"},
        {"name": "pop", "ref": "c_0123456789ab", "table": "B01003"}
      ],
      "aggregation": {"mapping": {"<GEOID>": "<group>"}},    # optional
      "derivations": [{"name": "rate", "op": "proportion", "num": "a", "den": "b"}],
      "adjustments": [{"type": "rpp", "variables": ["income"],   # optional; after exclusions
                       "rpp_year": 2019, "areas": "county_metro" | "state"}],
                   # several releases: {"type": "rpp", "variables": [...], "dollar_year": 2024,
                   #   "price_index": "r-cpi-u-rs", "rpp_years": {"2019": 2019, "2024": 2024}}
      "replicates": {"source": "census_vre"},               # optional; run_manifest fetches VRE files
      "exclusions": [{"rule": "cv_screen", "threshold": 30, "variables": ["income"],
                      "action": "flag" | "exclude"},
                     {"rule": "geoid_exclude", "geoids": ["..."]}],
      "missing": "complete_case",
      "confidence_level": 0.90,
      "correction": {"method": "holm", "family": "all" | "by_family"},
      "analyses": [{"id": "m1", "method": "fit_replicate", "formula": "income ~ pop",
                    "args": {"model": "ols"},
                    "replicate_scope": "all" | "covariates_only"}],   # optional, default "all"
      "hypotheses": [{"id": "H1", "statement": "...", "analysis": "m1",
                      "statistic": "coefficient", "term": "pop",
                      "direction": "two-sided" | "greater" | "less", "family": "primary"}],
      "data_source": {"synthetic": true,                    # optional; default: real Census API data
                      "description": "...", "generator": "..."},
      "external": [{"name": "places_dis", "source": "places",  # optional; external health outcomes
                    "release": 2025, "measure": "DISABILITY"}]
    }

``external`` (optional, PLAN_ROUND_21 B3 and Part 2): variables from a registered external source
(:mod:`census.health_sources`: CDC PLACES, USALEEP, County Health Rankings, or a pinned CDC WONDER
export read by :mod:`census.vital_records`), downloaded after the ACS analysis frame is built and
joined on GEOID, with each file's URL and SHA-256 and the dataset's revision stamp in ``run.json``
(``external``). An external variable may only be the outcome of ``fit_eiv``, ``fit_replicate`` or
``fh_regression``: its error is independent of the ACS sampling error, so it is held fixed in
replicate refits and its error enters the residual (as a covariate it would go uncorrected).
Derivations cannot use external variables; aggregation is refused; the values' tract vintage must
match every release (``harmonize_tracts_to``, or ``apportion_to`` for USALEEP). A failed download
is a blocking ``external_unavailable`` deviation; more than the source's limit (5%; 25% for
USALEEP, whose small tracts are unpublished) of the units with complete ACS data lacking an
external value is a blocking ``external_join_failed``.

The circularity rule is enforced (:func:`circularity_errors`): R1, an outcome whose construct the
ACS measures directly (PLACES DISABILITY: B18101) is allowed only in a comparison with that ACS
measure, testing only it (determinant studies use the ACS measure); R2, a tested term built from
the outcome model's own inputs (PLACES: age, sex, race/ethnicity, education, poverty; USALEEP:
income, race/ethnicity, education, density) needs a written ``circularity_justification`` on the
hypothesis. Overlapping controls are noted by :func:`create_manifest`; direct outcomes (vital
records) have no model inputs. The methods text states each source's model.

``geography`` takes ``state`` (one state, or ``"all"``) or ``states`` (a list
of 2-digit FIPS codes), never both. With ``states`` each table is extracted
per state and the states are stacked into one frame; ``codes`` are then not
allowed (county codes are per state). Pooled models get no automatic state
term: a cross-state formula states it explicitly, e.g. ``C(GEOID.str[:2])``.

``geography.harmonize_tracts_to`` (optional, ``2020`` or ``2010``; tract level only,
PLAN_ROUND_19): releases on the other tract vintage are apportioned to that vintage with
block housing-unit or population weights before the analysis frame is built, and their
Census VRE replicates go through the same crosswalk, so replicate SEs are exact for the
apportioned estimates (:mod:`census.tract_harmonization`). Only additive counts can be
apportioned (derive means and shares from them); Connecticut and ``aggregation`` are
refused; a crosswalk failure is a blocking ``harmonization_failed`` deviation. An RPP
adjustment at tract level may use ``areas: "county_metro"`` (each tract's county).

``adjustments`` (optional) are pre-registered transformations applied to the
analysis frame after derivations and exclusions (so a pre-registered exclusion
can remove a unit without an RPP area; a remaining unit without one is a
blocking ``adjustment_failed``). ``"rpp"`` divides
dollar variables (``variables``: manifest variable or derivation names), their
SEs and any supplied replicates by the BEA Regional Price Parity / 100 of each
row's area (``areas``: ``"county_metro"``, the default for county geographies,
or ``"state"``), with the same code as the ``place_adjust_frame`` tool
(:func:`census.workflows_microdata.place_adjust`). ``rpp_year`` is required so the
manifest hash fixes the price year (:func:`create_manifest` fills in the latest
year in the RPP table when it is omitted, before hashing); the year used, every
RPP area and the RPP table's SHA-256 (bundled checksum, or the custom table's path and hash) are
recorded in ``run.json`` and ``bundle.json`` (``adjustments``). An RPP year
other than the release end year is a note, not a deviation.

Several releases (PLAN_ROUND_15 A1, decision D15-2): an RPP adjustment then also
requires ``dollar_year``, ``price_index`` (one of census.inflation.PRICE_INDEXES;
``"r-cpi-u-rs"``, the index the Census Bureau uses for ACS dollars, is the default
create_manifest fills in) and ``rpp_years`` (``{"<release>": RPP year}`` for every
release, instead of ``rpp_year``; filled with each release's own year). Each
release's dollars are first converted to ``dollar_year`` dollars with the price
index (CPI(dollar_year) / CPI(release)), then divided by the RPP of the release's
``rpp_years`` entry; estimates, SEs and replicates of that release alike. With one
release a ``dollar_year`` (plus ``price_index``) is optional. Not combinable with
``aggregation``. The run records the CPI values and factors, the price-index
table's SHA-256 and every release's RPP areas.

``replicates`` (optional, PLAN_ROUND_15 A2): ``{"source": "census_vre"}`` makes
run_manifest fetch the Census VRE files for the manifest's tables, geography and
releases (:func:`census.replicate.fetch_vre` and its cache), as the replicate
frame of every replicate analysis; ``run.json`` and ``bundle.json`` record each
file's URL and SHA-256, and ``replicates.unavailable`` lists variables without
published replicates (e.g. B19013 medians). Under the strict confirmatory policy a
replicate analysis that uses such a variable blocks (``replicates_incomplete``)
unless the analysis declares ``"replicate_scope": "covariates_only"``
(fit_replicate only; target ``population`` or ``conservative``): its outcome is
then held at its estimate in every refit, and the declaration is in the hash and
the methods text. The declaration is allowed whenever it is well-formed: an
outcome the VRE registry lists can still lack replicates for the analysed units,
so create_manifest only notes such an outcome, and a run that finds replicates
for it still holds it fixed as declared (the hashed declaration governs) and
records that (``replicates.covariates_only_outcome_had_replicates``). Census VRE
files of tract and block-group geographies are per state, so those levels need
``geography.state`` or ``states``. Caller-supplied ``replicates`` are an error
with census_vre.

Releases whose ACS 5-year periods overlap (shared sample years) are never
combined through replicates (the trend module's overlap rule: published
replicates do not carry the covariance of overlapping periods): validation
refuses census_vre or an analysis declaring ``"replicates": "required"`` with
overlapping releases, and caller-supplied replicates spanning overlapping
releases stop every replicate analysis with a blocking
``replicates_overlapping_releases`` deviation.

When replicates are supplied and the manifest has derivations, each
derivation absent from the replicate frame is evaluated on the replicates of
its inputs (replicate rows named by manifest variable name or ACS code), and
its SE becomes the exact replicate SE where its inputs have replicates.
``replicates.derived_on_replicates`` lists only derivations that received a
replicate SE, with per-derivation counts (``derived_on_replicates_rows``:
rows_replicate of rows in the analysed frame); a failure of that step is a
blocking ``replicates_incomplete`` deviation.

``data_source`` (optional) *declares* where the input data come from. The
labels follow where the data actually came from (:func:`observed_data_source`):
data are synthetic when the client that served them carries a true
``synthetic`` attribute or its cache was marked with
``QueryCache.mark_synthetic``; otherwise they are real Census Data API data.
A declaration that disagrees with the observed source records a blocking
``data_source_mismatch`` deviation, and the citation and methods text follow
the observed source (real Census data are never called synthetic; synthetic
data never claim retrieval from the Census Data API).

Run status (``analysis_status`` in results, ``results/run.json``,
``bundle.json`` provenance and ``methods.md``):

- ``"confirmatory"`` (:data:`STATUS_CONFIRMATORY`): the pre-registered
  analysis ran as registered, with no blocking deviation.
- ``"confirmatory_incomplete"`` (:data:`STATUS_CONFIRMATORY_INCOMPLETE`): at
  least one blocking deviation (:data:`BLOCKING_DEVIATIONS`, e.g. a hypothesis
  not tested, an analysis failed, replicates incomplete, an extraction
  failure); the pre-registered analysis did not run as registered and its
  results are not confirmatory.
- ``"exploratory"``: anything run outside a manifest (:func:`label_exploratory`).

Supported analysis methods are :data:`ANALYSIS_METHODS`; hypothesis
statistics are :data:`STATISTICS`. :func:`create_manifest` validates (every
variable resolves in the offline metadata archive through the concordance,
every method is supported) and returns the SHA-256 of the canonical JSON
(:func:`manifest_hash`). :func:`run_manifest` executes it exactly and writes
the hash into every output; deviations are recorded, never substituted
silently. Anything run outside a manifest should be tagged with
:func:`label_exploratory`.
"""


from .schema import (
    ADJUSTMENT_TYPES,
    ANALYSIS_METHODS,
    AUTHOR_RE,
    Any,
    BLOCKING_DEVIATIONS,
    BundledDataIntegrityError,
    CONCEPT_RE,
    CONFIRMATORY_REPLICATE_POLICY,
    Callable,
    DATA_SOURCE_KEYS,
    DIRECTIONS,
    Dict,
    EXCLUSION_RULES,
    FIPS2_RE,
    FORMULA_FUNCTIONS,
    FORMULA_ID_COLUMNS,
    INCOMPLETE_STATUS_TEXT,
    IncompleteReplicatesError,
    LEGACY_X2_MANIFESTS,
    List,
    Mapping,
    ModelResult,
    NAME_RE,
    Optional,
    Path,
    REFERENCES,
    REPLICATES_KEYS,
    REPLICATE_METHODS,
    REPLICATE_SCOPES,
    REPLICATE_SOURCES,
    RPP_ADJUSTMENT_KEYS,
    SCHEMA_VERSION,
    STATISTICS,
    STATUS_CONFIRMATORY,
    STATUS_CONFIRMATORY_INCOMPLETE,
    STATUS_EXPLORATORY,
    Sequence,
    Tuple,
    Union,
    YEAR_CODE_RE,
    _SPEC_KEYS,
    _STATE_PREFIXED_LEVELS,
    _dataset_for,
    _derivation_refs,
    _duplicate_spec_keys,
    _formula_names,
    _is_int,
    _normalize_analysis,
    _table_of,
    _variable_tables,
    canonical_json,
    copy,
    datetime,
    hashlib,
    integrity_errors,
    interval_description,
    json,
    load_manifest,
    manifest_entities,
    manifest_hash,
    manifest_releases,
    manifest_states,
    math,
    np,
    pd,
    re,
    release_overlap_message,
    tables_and_refs,
)
from .external import (
    _ext_source_text,
    _has_equivalent,
    circularity_errors,
    external_circularity,
    external_names,
)
from .adjustments import (
    _FILL_REASONS,
    _apply_adjustments,
    _check_adjustments,
    _check_dollar_year,
    _check_rpp_years,
    _fill_adjustment_defaults,
    _scale_rows,
    default_rpp_areas,
    latest_rpp_year,
)
from .derivations import (
    _age_standardized_errors,
    _fill_derivation_defaults,
)
from .replicates import (
    _canonical_column,
    _census_vre_replicates,
    _check_replicates,
    _declared_covariates_only,
    _derive_replicates,
    _has_replicate_rows,
    _replicate_overlap,
    _replicate_rows,
    _vre_level,
    census_vre_source,
    read_replicates,
    replicates_digest,
    replicates_sha256,
    vre_unavailable,
)
from .datasource import (
    data_source_record,
    effective_data_source,
    observed_data_source,
    resolve_data_source,
)
from .validate import (
    _check_geography,
    _check_variables,
    validate_manifest,
)
from .create import (
    create_manifest,
)
from .methods_text import (
    _METHOD_TEXT,
    _age_standardized_text,
    _multi_release_adjustment_text,
    methods_section,
)
from .run import (
    _codebook_columns,
    _one_sided,
    _run_analysis,
    _statistic,
    _tag,
    _wide_from_panel,
    _write_analysed_data,
    _write_bundle,
    analysis_status,
    label_exploratory,
    run_manifest,
    run_variant,
)

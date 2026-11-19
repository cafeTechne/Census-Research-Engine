# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validated joint (omnibus) tests: the Round 31 selection.

Set from the fixed experiment in ``docs/audits/omnibus_validation.md``
(criterion 3e3094a), never inferred at runtime:

- F references (W1, HTZ W2) failed everywhere and are not used.
- **Non-spatial:** the restricted score statistic with a Rademacher wild score
  bootstrap (W3, 399 draws) passed for OLS factor tests (one-way, ANCOVA,
  interactions) and for binomial and Poisson spline tests. Elsewhere it is the
  best available test but exploratory (sizes up to .168 at nominal .10).
- **Spatial (IM-8):** Hotelling T² on the eight fixed cluster estimates (W4)
  passed for OLS and Poisson factor tests; it targets the coefficients on the ACS
  estimates as observed (Round 30 C1).
- Validated at n = 145 MI/NY counties; with fewer analysed units the tests are
  exploratory only. Validated for the conservative target (or no replicates).

The Round 27 chi-squared ``census.splines.joint_wald`` is unchanged and stays
exploratory.
"""
import zlib

import numpy as np

from . import omnibus

AUDIT = "docs/audits/omnibus_validation.md"
VALIDATED = frozenset({("ols", "factor"), ("binomial", "spline"), ("poisson", "spline")})
SPATIAL_VALIDATED = frozenset({("ols", "factor"), ("poisson", "factor")})
PAIRWISE_VALIDATED = {"holm": frozenset({"ols", "binomial", "poisson"}), "simultaneous": frozenset({"ols"})}
VALIDATED_MIN_N = 145
BOOTSTRAP_SEED = 20261218
_ENGINE_MODEL = {"ols": "linear", "binomial": "binomial", "poisson": "poisson"}


def family(columns):
    """'spline' when every tested column comes from cr(...), else 'factor'."""
    return "spline" if columns and all(str(c).startswith("cr(") for c in columns) else "factor"


def tested_columns(result, variable=None, term=None):
    """Design columns of a manifest variable (all its standalone terms) or of one formula term."""
    if (variable is None) == (term is None):
        raise ValueError("give exactly one of variable or term")
    inputs = getattr(result, "joint_inputs", None)
    if variable is not None:
        columns = (result.diagnostics.get("joint_columns") or {}).get(variable, [])
        if not columns:
            raise ValueError(f"no standalone design columns for variable {variable!r}")
        return list(columns)
    terms = (inputs or {}).get("term_columns") or (result.diagnostics.get("spatial_clusters") or {}).get("term_columns") or {}
    if term not in terms:
        raise ValueError(f"term {term!r} not in the model (terms: {sorted(terms)})")
    return list(terms[term])


def _refusal(model, fam, n, target, has_replicates, spatial):
    validated = (SPATIAL_VALIDATED if spatial else VALIDATED)
    if (model, fam) not in validated:
        kind = "IM-8 Hotelling" if spatial else "wild score bootstrap"
        return f"{kind} joint test was not validated for {model} {fam} tests ({AUDIT}); exploratory only"
    if n < VALIDATED_MIN_N:
        return f"joint tests were validated at n = {VALIDATED_MIN_N} areas; this fit has {n}: exploratory only"
    if not spatial and has_replicates and target != "conservative":
        return "joint tests with ACS replicates were validated for the conservative target only; exploratory only"
    return None


def joint_test(result, variable=None, term=None):
    """Test that every tested coefficient is 0.

    Returns estimate (the statistic), p_two_sided, df, reference, columns,
    validated and confirmatory_refusal (None when confirmatory use is allowed).
    """
    columns = tested_columns(result, variable, term)
    model = result.model_type
    fam = family(columns)
    spatial = result.diagnostics.get("spatial_clusters")
    if spatial is not None:
        if spatial.get("method") != "im" or not spatial.get("validation_audit"):
            raise ValueError("spatial joint tests need IM-8 spatial clusters (Round 30 C1)")
        missing = [c for c in columns if c not in spatial.get("cluster_terms", [])]
        if missing:
            raise ValueError(f"tested columns not estimable within clusters under IM: {missing}")
        idx = [spatial["cluster_terms"].index(c) for c in columns]
        out = omnibus.w4(np.asarray(spatial["cluster_estimates"], float), idx)
        refusal = _refusal(model, fam, result.n_obs, "population", False, True)
        return dict(estimate=out["statistic"], se=None, p_two_sided=out["p"], ci_lower=None, ci_upper=None,
                    df=out["df"], df_denominator=out["df_denominator"],
                    reference="Hotelling T2 on eight fixed cluster estimates, F(q, 8-q)", columns=columns,
                    family=fam, validated=refusal is None, confirmatory_refusal=refusal)
    inputs = getattr(result, "joint_inputs", None)
    if inputs is None:
        raise ValueError("this fit does not carry joint-test inputs (fit with census.models.fit_replicate)")
    if model not in _ENGINE_MODEL:
        raise ValueError(f"joint tests support OLS, binomial and Poisson fits, not {model!r}")
    if not inputs["full_rank"]:
        raise ValueError("rank-deficient model design; joint hypothesis not tested")
    target = inputs["target"]
    if target == "these_areas":
        raise ValueError("joint tests support the population and conservative targets")
    names = inputs["column_names"]
    idx = [names.index(c) for c in columns]
    Vs = inputs["sampling_covariance"] if (target == "conservative" and inputs["has_replicates"]) else np.zeros((len(names),)*2)
    seed = np.random.SeedSequence([BOOTSTRAP_SEED, zlib.crc32("|".join(columns).encode())])
    out = omnibus.w3(inputs["X"], inputs["y"], _ENGINE_MODEL[model], idx, Vs, np.random.default_rng(seed),
                     trials=inputs["trials"], exposure=inputs["exposure"])
    refusal = _refusal(model, fam, result.n_obs, target, inputs["has_replicates"], False)
    return dict(estimate=out["statistic"], se=None, p_two_sided=out["p"], ci_lower=None, ci_upper=None,
                df=out["df"], reference=f"restricted score statistic, wild score bootstrap ({omnibus.BOOTSTRAP_DRAWS} Rademacher draws)",
                columns=columns, family=fam, validated=refusal is None, confirmatory_refusal=refusal)

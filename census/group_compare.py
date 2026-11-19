# SPDX-License-Identifier: AGPL-3.0-or-later
"""Group comparisons for area-level data: t-tests, one-way ANOVA, ANCOVA and
two-way interactions, with ACS sampling error (Round 31).

Everything is fitted through :func:`census.models.fit_replicate`, so replicate
handling, reliability screens and IM-8 spatial clusters are unchanged. The
omnibus test is :func:`census.joint_tests.joint_test`; pairwise comparisons use
:func:`census.omnibus.pairwise`. Validation: ``docs/audits/omnibus_validation.md``.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import joint_tests, omnibus

DESIGNS = ("two_group", "oneway", "ancova", "twoway")
POSTHOC = ("holm", "simultaneous", "none")
MIN_GROUP_SIZE = 5
_MODELS = ("ols", "binomial", "poisson")


@dataclass
class GroupComparison:
    design: str
    model: str
    outcome: str
    group: str
    n_obs: int
    group_sizes: Dict[str, int]
    reference_group: str
    omnibus: Dict[str, Any]
    adjusted_means: pd.DataFrame
    pairwise: Optional[pd.DataFrame]
    effect_sizes: Dict[str, Any]
    validation: Dict[str, Any]
    notes: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    fit: Any = None

    def to_dict(self) -> Dict[str, Any]:
        from .results import _jsonable
        out = {k: v for k, v in self.__dict__.items() if k != "fit"}
        out["coefficients"] = self.fit.coefficients if self.fit is not None else None
        return _jsonable(out)

    def summary(self) -> str:
        o = self.omnibus
        status = "validated" if o.get("validated") else "exploratory"
        what = "interaction" if self.design == "twoway" else f"{self.outcome} across {len(self.group_sizes)} groups of {self.group}"
        text = f"Joint test of {what}: p = {o['p_two_sided']:.3g} ({status})"
        if self.pairwise is not None and len(self.pairwise):
            col = "p_simultaneous" if "p_simultaneous" in self.pairwise and self.validation.get("posthoc") == "simultaneous" else "p_holm"
            hits = int((self.pairwise[col] < 1-self.validation["confidence_level"]).sum())
            text += f"; {hits} of {len(self.pairwise)} pairwise differences significant ({col[2:]})"
        return text


def _term(name, ref):
    return f"C({name}, Treatment(reference={ref!r}))"


def _check(frame, outcome, group, design, group2, covariates, model, posthoc, trials, exposure):
    if design not in DESIGNS:
        raise ValueError(f"design must be one of {DESIGNS}")
    if model not in _MODELS:
        raise ValueError(f"model must be one of {_MODELS}")
    if posthoc not in POSTHOC:
        raise ValueError(f"posthoc must be one of {POSTHOC}")
    for col in [outcome, group] + list(covariates) + ([group2] if group2 else []):
        if col not in frame:
            raise ValueError(f"column {col!r} not in the frame")
    if design == "ancova" and not covariates:
        raise ValueError("design='ancova' needs covariates")
    if design != "ancova" and design != "twoway" and covariates:
        raise ValueError("covariates are allowed with design='ancova' or 'twoway' only")
    if design == "twoway" and not group2:
        raise ValueError("design='twoway' needs group2")
    if design != "twoway" and group2:
        raise ValueError("group2 is used only with design='twoway'")
    if model == "binomial" and not trials:
        raise ValueError("model='binomial' needs trials")
    if model == "poisson" and not exposure:
        raise ValueError("model='poisson' needs exposure (the expected count or population)")


def compare_groups(frame: pd.DataFrame, outcome: str, group: str, *, replicates: Optional[pd.DataFrame] = None,
                   covariates: Sequence[str] = (), design: str = "oneway", group2: Optional[str] = None,
                   model: str = "ols", trials: Optional[str] = None, exposure: Optional[str] = None,
                   posthoc: str = "holm", reference_group: Optional[str] = None,
                   spatial_clusters: Optional[Dict[str, Any]] = None, coords: Optional[pd.DataFrame] = None,
                   confidence_level: float = 0.90, target: Optional[str] = None) -> GroupComparison:
    """Compare an area-level outcome across groups of areas.

    ``group`` (and ``group2``) are categorical columns, for example a metro/nonmetro class
    or the state (``"state"`` uses the first two GEOID digits). Designs: ``two_group``
    (a t-test on the group indicator), ``oneway`` (ANOVA), ``ancova`` (adjusted for
    ``covariates``) and ``twoway`` (tests the group x group2 interaction). The omnibus test
    and post hoc comparisons use the Round 31 validated procedures; other combinations are
    labelled exploratory. ``spatial_clusters={"k": 8, "method": "im"}`` uses IM-8
    (Round 30 C1, naive estimand).
    """
    frame = frame.copy()
    for name in (group, group2):
        if name == "state":
            frame["state"] = frame["GEOID"].astype(str).str[:2]
    _check(frame, outcome, group, design, group2, covariates, model, posthoc, trials, exposure)
    used = frame.dropna(subset=[c for c in [group, group2] if c]).copy()
    for name in [g for g in (group, group2) if g]:
        used[name] = used[name].astype(str)
    sizes = used[group].value_counts().sort_index()
    small = sizes[sizes < MIN_GROUP_SIZE]
    if len(small):
        raise ValueError(f"every group needs at least {MIN_GROUP_SIZE} areas; too small: {small.to_dict()}")
    k = len(sizes)
    if k < 2 or (design == "two_group" and k != 2):
        raise ValueError("two_group needs exactly 2 groups; other designs need at least 2")
    ref = str(reference_group) if reference_group is not None else str(sizes.index[0])
    if ref not in sizes.index:
        raise ValueError(f"reference_group {ref!r} is not a group (groups: {list(sizes.index)})")
    spatial = spatial_clusters is not None
    if spatial and posthoc == "simultaneous":
        raise ValueError("simultaneous post hoc intervals are not available with spatial clusters; use posthoc='holm'")
    if target is None:
        target = "population" if spatial or replicates is None else "conservative"
    gterm = _term(group, ref)
    rhs = [gterm] + list(covariates)
    if design == "twoway":
        ref2 = str(used[group2].value_counts().sort_index().index[0])
        rhs = [f"{gterm} * {_term(group2, ref2)}"] + list(covariates)
    formula = f"{outcome} ~ " + " + ".join(rhs)
    from .models import fit_replicate
    fit = fit_replicate(formula, used, replicates, model=model, trials=trials, exposure=exposure,
                        confidence_level=confidence_level, target=target,
                        scale=None if spatial or model == "ols" else "robust",
                        spatial_clusters=spatial_clusters, coords=coords)
    terms = fit.joint_inputs["term_columns"]
    if design == "twoway":
        tested = next(t for t in terms if ":" in t and group in t and group2 in t)
    else:
        tested = next(t for t in terms if t.startswith(f"C({group},") and ":" not in t)
    omni = joint_tests.joint_test(fit, term=tested)
    omni["term"] = tested
    n, p = fit.n_obs, len(fit.joint_inputs["column_names"])
    names = fit.joint_inputs["column_names"]
    group_cols = list(terms[next(t for t in terms if t.startswith(f"C({group},") and ":" not in t)])
    levels = [ref] + [c.split("[T.", 1)[1][:-1] for c in group_cols]
    notes, diagnostics = [], {}
    means, pair_table = _adjusted_means(fit, names, group_cols, levels, model, spatial, confidence_level, n, p, design)
    if design != "twoway" and posthoc != "none":
        pair_table = _pairwise(fit, names, group_cols, levels, posthoc, spatial, confidence_level, n, p)
    else:
        pair_table = None
    effect = _effect_sizes(fit, names, group_cols if design != "twoway" else terms[tested], model, spatial)
    validation = dict(omnibus=bool(omni["validated"]), omnibus_refusal=omni["confirmatory_refusal"],
                      posthoc=posthoc, posthoc_validated=_posthoc_validated(posthoc, model, spatial, n),
                      confidence_level=confidence_level, audit=joint_tests.AUDIT)
    if model in ("binomial", "poisson"):
        notes.append("Adjusted means and differences are on the model's scale: differences are log odds ratios "
                     "(binomial) or log rate ratios (Poisson); means are back-transformed proportions or rate ratios.")
    notes.append("Adjusted group means are predictions at the analysed areas' covariate means." if design == "ancova"
                 else "Group means are model predictions for each group.")
    if spatial:
        notes.append("IM-8: each cluster is fitted separately; tests target the coefficients on the ACS estimates as "
                     "observed (attenuated if covariates have sampling error; Round 30 C1).")
    else:
        notes.append("Areas are assumed independent; spatial dependence can make p-values too small "
                     "(use spatial_clusters={'k': 8, 'method': 'im'} where validated).")
    if not omni["validated"]:
        notes.append("EXPLORATORY: " + (omni["confirmatory_refusal"] or "joint test not validated"))
    if posthoc != "none" and design != "twoway" and not validation["posthoc_validated"]:
        notes.append(f"EXPLORATORY: {posthoc} post hoc comparisons were not validated for this model "
                     f"({joint_tests.AUDIT}).")
    if covariates and design == "ancova":
        notes.append("If covariates have sampling error, adjusted differences can be biased (residual confounding); "
                     "this test targets the adjustment with the ACS estimates as observed.")
    diagnostics.update(_comparison_diagnostics(fit, used, outcome, group, design, model, replicates, covariates))
    return GroupComparison(design=design, model=model, outcome=outcome, group=group, n_obs=n,
                           group_sizes={str(a): int(b) for a, b in sizes.items()}, reference_group=ref,
                           omnibus=omni, adjusted_means=means, pairwise=pair_table, effect_sizes=effect,
                           validation=validation, notes=notes + list(fit.notes), diagnostics=diagnostics, fit=fit)


def _target_cov(fit, names):
    d = fit.diagnostics
    V = d["joint_model_covariance"].loc[names, names].to_numpy(float)
    if d.get("interval_target") == "conservative" and fit.joint_inputs["has_replicates"]:
        V = V + d["sampling_covariance"].loc[names, names].to_numpy(float)
    return V


def _adjusted_means(fit, names, group_cols, levels, model, spatial, level, n, p, design):
    if spatial or design == "twoway":
        return pd.DataFrame(columns=["group", "estimate", "ci_lower", "ci_upper"]), None
    X = fit.joint_inputs["X"]
    b = fit.coefficients.set_index("term").loc[names, "estimate"].to_numpy(float)
    V = _target_cov(fit, names)
    base = X.mean(axis=0)
    idx = [names.index(c) for c in group_cols]
    crit = stats.t.ppf((1+level)/2, n-p)
    rows = []
    for j, lev in enumerate(levels):
        x = base.copy(); x[idx] = 0.
        if j:
            x[idx[j-1]] = 1.
        eta, se = float(x @ b), float(np.sqrt(x @ V @ x))
        lo, hi = eta-crit*se, eta+crit*se
        inv = (lambda v: v) if model == "ols" else (lambda v: 1/(1+np.exp(-v))) if model == "binomial" else np.exp
        rows.append(dict(group=lev, estimate=float(inv(eta)), ci_lower=float(inv(lo)), ci_upper=float(inv(hi)),
                         link_estimate=eta, link_se=se))
    return pd.DataFrame(rows), None


def _pairwise(fit, names, group_cols, levels, posthoc, spatial, level, n, p):
    if spatial:
        info = fit.diagnostics["spatial_clusters"]
        terms = info["cluster_terms"]
        missing = [c for c in group_cols if c not in terms]
        if missing:
            raise ValueError(f"group columns not estimable within clusters under IM: {missing}")
        B = np.asarray(info["cluster_estimates"], float)[:, [terms.index(c) for c in group_cols]]
        B = np.column_stack((np.zeros(len(B)), B))
        rows = []
        for i, j in omnibus.pairs(len(levels)):
            d = B[:, j]-B[:, i]
            est, se = float(d.mean()), float(d.std(ddof=1)/np.sqrt(len(d)))
            t = est/se
            crit = stats.t.ppf((1+level)/2, len(d)-1)
            rows.append(dict(group_a=levels[i], group_b=levels[j], difference=est, se=se, t=t,
                             p_raw=float(2*stats.t.sf(abs(t), len(d)-1)), ci_lower=est-crit*se, ci_upper=est+crit*se))
        table = pd.DataFrame(rows)
        table["p_holm"] = _holm(table["p_raw"].to_numpy())
        return table
    b = fit.coefficients.set_index("term").loc[group_cols, "estimate"].to_numpy(float)
    V = _target_cov(fit, names)
    idx = [names.index(c) for c in group_cols]
    r = omnibus.pairwise(b, V[np.ix_(idx, idx)], n-p, level=level)
    crit_marginal = stats.t.ppf((1+level)/2, n-p)
    rows = []
    for m, (i, j) in enumerate(r["pairs"]):
        row = dict(group_a=levels[i], group_b=levels[j], difference=float(r["difference"][m]), se=float(r["se"][m]),
                   t=float(r["t"][m]), p_raw=float(r["p_raw"][m]), p_holm=float(r["p_holm"][m]),
                   ci_lower=float(r["difference"][m]-crit_marginal*r["se"][m]),
                   ci_upper=float(r["difference"][m]+crit_marginal*r["se"][m]))
        if posthoc == "simultaneous":
            row.update(p_simultaneous=float(r["p_simultaneous"][m]), simultaneous_lower=float(r["lower"][m]),
                       simultaneous_upper=float(r["upper"][m]))
        rows.append(row)
    return pd.DataFrame(rows)


def _holm(p):
    order = np.argsort(p); m = len(p); out = np.empty(m); running = 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (m-rank)*p[i])); out[i] = running
    return out


def _posthoc_validated(posthoc, model, spatial, n):
    if posthoc == "none" or n < joint_tests.VALIDATED_MIN_N:
        return False
    if spatial:
        return posthoc == "holm"   # Holm over IM-8 t tests, each validated in Round 30 (C1)
    return model in joint_tests.PAIRWISE_VALIDATED[posthoc]


def _effect_sizes(fit, names, tested_cols, model, spatial):
    """Partial eta^2 and omega^2 for OLS (descriptive point estimates; they ignore sampling error)."""
    if model != "ols" or spatial:
        return {"note": "eta^2/omega^2 are defined for OLS fits only"}
    X, y = fit.joint_inputs["X"], fit.joint_inputs["y"]
    idx = [names.index(c) for c in tested_cols]
    keep = [j for j in range(X.shape[1]) if j not in idx]
    rss = lambda A: float(np.sum((y-A @ np.linalg.lstsq(A, y, rcond=None)[0])**2))
    full, restricted = rss(X), rss(X[:, keep])
    n, p, q = len(y), X.shape[1], len(idx)
    ss_effect, mse = restricted-full, full/(n-p)
    eta = ss_effect/(ss_effect+full)
    omega = max(0., (ss_effect-q*mse)/(ss_effect+(n-q)*mse))
    return {"partial_eta_squared": eta, "partial_omega_squared": omega,
            "note": "descriptive point estimates from sums of squares; they ignore ACS sampling error and have no interval"}


def _comparison_diagnostics(fit, used, outcome, group, design, model, replicates, covariates):
    out: Dict[str, Any] = {}
    if model != "ols":
        return out
    X, y = fit.joint_inputs["X"], fit.joint_inputs["y"]
    resid = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    labels = used.loc[used[[outcome, group] + list(covariates)].notna().all(axis=1), group].astype(str).to_numpy()
    if len(labels) == len(resid):
        groups = [resid[labels == g] for g in np.unique(labels)]
        lev = stats.levene(*groups, center="median")
        out["brown_forsythe_spread"] = {"statistic": float(lev.statistic), "p": float(lev.pvalue),
                                        "note": "residual spread by group; information only, never a gate"}
        if design in ("oneway", "two_group") and replicates is None:
            from statsmodels.stats.oneway import anova_oneway
            vals = [y[labels == g] for g in np.unique(labels)]
            classical = stats.f_oneway(*vals)
            welch = anova_oneway(vals, use_var="unequal")
            out["classical_comparison"] = {
                "f_oneway": {"statistic": float(classical.statistic), "p": float(classical.pvalue)},
                "welch_anova": {"statistic": float(welch.statistic), "p": float(welch.pvalue)},
                "note": "ignores sampling error; comparison only"}
    return out

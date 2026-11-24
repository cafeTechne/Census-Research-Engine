# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 89: ``causal_question`` (target trial) and ``dag`` (causal diagram) manifest blocks.

``causal_question``: {eligibility, intervention, comparator, time_zero, outcome, follow_up, contrast
("average_effect" | "effect_in_treated"), target ("super_population" | "these_areas")[, exposure, versions, note]}.
``dag``: {edges: ["A -> B", ...], treatment, outcome[, nodes, note]}; unmeasured nodes are named U, U1, U_x.
Every analysis whose formula contains the DAG's treatment and outcome is checked by the backdoor criterion: a formula
that leaves a backdoor path open, or adjusts for a mediator, another descendant of treatment, a collider it opens or an
unmeasured node, is a validation error (manifests are pre-registered); a manifest flagged ``exploratory: true`` gets
the same findings in its methods text instead. Hernán and Robins, *What If*, chapters 3, 6-8, 18, 22.
"""
from typing import Any, Dict, List, Mapping

from .. import causal_spec as cs


def _checks(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    dag = manifest.get("dag")
    out = []
    g = cs.parse_dag(dag["edges"], dag.get("nodes") or ())
    for a in manifest.get("analyses") or []:
        if a.get("method") == "estimate_effect":
            trt = a.get("treatment") or a.get("x")
            if a.get("outcome") == dag["outcome"] and trt == dag["treatment"]:
                adjust = list(a.get("confounders") or (a.get("args") or {}).get("controls") or [])
                out.append({"analysis": a.get("id"), **cs.check_adjustment(g, dag["treatment"], dag["outcome"], adjust)})
            continue
        f = str(a.get("formula", ""))
        if "~" not in f:
            continue
        try:
            y, adjust = cs.formula_adjustment(f, dag["treatment"])
        except cs.DagError:
            continue
        if y != dag["outcome"]:
            continue
        out.append({"analysis": a.get("id"), **cs.check_adjustment(g, dag["treatment"], dag["outcome"], adjust)})
    return out


def causal_errors(manifest: Mapping[str, Any]) -> List[str]:
    errs: List[str] = []
    if "causal_question" in manifest:
        errs += cs.trial_errors(manifest["causal_question"])
    if "dag" not in manifest:
        return errs
    try:
        rep = cs.dag_report(manifest["dag"])
        checks = _checks(manifest)
    except cs.DagError as exc:
        return errs + [f"dag: {exc}"]
    if not checks:
        errs.append(f"dag: no analysis formula has outcome {rep['outcome']!r} and treatment {rep['treatment']!r}")
    if manifest.get("exploratory"):
        return errs
    for c in checks:
        errs += [f"analyses ({c['analysis']}): {p}; sufficient sets from the diagram: "
                 f"{rep['minimal_adjustment_sets'] or 'none'}" for p in c["problems"]]
    return errs


def causal_methods(manifest: Mapping[str, Any], lines: List[str], cites: List[str]) -> None:
    q, dag = manifest.get("causal_question"), manifest.get("dag")
    if not q and not dag:
        return
    lines += ["", "### Causal question", ""]
    if q:
        lines.append("The causal question is stated as the protocol of a target trial (Hernán and Robins 2020):")
        lines += [f"- {x}" for x in cs.trial_text(q)]
    if dag:
        try:
            rep = cs.dag_report(dag)
            checks = _checks(manifest)
        except cs.DagError as exc:
            lines.append(f"Causal diagram invalid: {exc}.")
            return
        lines.append(f"Adjustment sets were chosen from a pre-registered causal diagram ({rep['nodes']} nodes) by the "
                     "backdoor criterion, not by associational rules. Minimal sufficient sets: "
                     + ("; ".join("{" + ", ".join(s) + "}" for s in rep["minimal_adjustment_sets"])
                        or "none (unmeasured confounding cannot be removed by adjustment)") + ".")
        for c in checks:
            verdict = "blocks every backdoor path" if c["sufficient"] else "is NOT sufficient: " + "; ".join(c["problems"])
            lines.append(f"- Analysis `{c['analysis']}` adjusts for {{{', '.join(c['adjusted'])}}}, which {verdict}.")
            lines += [f"  - Note: {w}" for w in c["warnings"]]
    cites.append("hernan_robins")

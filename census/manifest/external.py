# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest external definitions."""

from typing import Any, Dict, List, Mapping
from .schema import (
    _formula_names,
    _variable_tables,
)



def external_names(manifest: Mapping[str, Any]) -> List[str]:
    """Names of the manifest's ``external`` variables (well-formed entries only)."""
    ext = manifest.get("external")
    return [str(e["name"]) for e in (ext if isinstance(ext, list) else [])
            if isinstance(e, Mapping) and e.get("name") is not None]


def external_circularity(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Analyses with an external outcome, with the covariates that measure the outcome model's inputs
    (``overlap``) and those that measure the outcome's construct directly in the ACS (``equivalent``)."""
    from ..health_sources import circularity_overlap, equivalent_tables, measure_kind
    ext = {str(e["name"]): e for e in manifest.get("external") or [] if isinstance(e, Mapping) and "name" in e}
    if not ext:
        return []
    tables = _variable_tables(manifest)
    out = []
    for a in manifest.get("analyses") or []:
        if not isinstance(a, Mapping) or "~" not in str(a.get("formula", "")):
            continue
        lhs, rhs = str(a["formula"]).split("~", 1)
        ys = [y if y in ext else y[:-10] for y in _formula_names(lhs)
              if y in ext or (y.endswith("_numerator") and y[:-10] in ext)]
        if not ys:
            continue
        covs = [c for c in _formula_names(rhs) if c in tables]
        for y in ys:
            src, meas = ext[y].get("source"), ext[y].get("measure")
            try:
                kind = measure_kind(src, meas)
                hit = {c: circularity_overlap(src, tables[c], meas) for c in covs}
                eq = {c: equivalent_tables(src, meas, tables[c]) for c in covs}
            except (ValueError, KeyError, TypeError):  # unknown source or measure: reported by validation
                continue
            out.append({"analysis": a.get("id"), "outcome": y, "source": src, "measure": meas, "kind": kind,
                        "overlap": {c: v for c, v in hit.items() if v},
                        "equivalent": {c: v for c, v in eq.items() if v},
                        "has_equivalent": bool(_has_equivalent(src, meas))})
    return out


def _ext_source_text(entry: Mapping[str, Any]) -> str:
    from ..health_sources import SOURCES, source_text
    try:
        return source_text(str(entry["source"]), entry["measure"])
    except (KeyError, ValueError):
        return str(SOURCES.get(entry.get("source"), {}).get("model_text", ""))


def _has_equivalent(source: Any, measure: Any) -> tuple:
    from ..health_sources import acs_equivalent
    try:
        return acs_equivalent(str(source), measure)
    except ValueError:
        return ()


def circularity_errors(manifest: Mapping[str, Any]) -> List[str]:
    """The enforced circularity rule (PLAN_ROUND_21 Part 2, C1): R1 same construct, R2 model inputs."""
    from ..health_sources import CIRCULARITY_RULE, acs_equivalent
    errors: List[str] = []
    by_analysis: Dict[Any, List[Dict[str, Any]]] = {}
    for c in external_circularity(manifest):
        by_analysis.setdefault(c["analysis"], []).append(c)
    hyps = [h for h in manifest.get("hypotheses") or [] if isinstance(h, Mapping)]
    tables = _variable_tables(manifest)
    for aid, recs in by_analysis.items():
        tested = [h for h in hyps if h.get("analysis") == aid]
        for c in recs:
            if c["has_equivalent"]:
                eq_tabs = "/".join(t.rstrip("*") + ("*" if t.endswith("*") else "")
                                   for t in acs_equivalent(c["source"], c["measure"])[:4])
                if not c["equivalent"]:
                    errors.append(
                        f"analyses {aid}: CIRCULARITY R1: the outcome {c['outcome']} ({c['source']} "
                        f"{c['measure']}) measures a construct the ACS measures directly ({eq_tabs}). Use the "
                        "ACS measure as the outcome of a determinant study; an external measure of the same "
                        "construct is allowed only to compare the two (the model must contain the ACS measure "
                        f"and only it may be tested). {CIRCULARITY_RULE}")
                    continue
                for h in tested:
                    term = [n for n in _formula_names(str(h.get("term", ""))) if n in tables] or [str(h.get("term"))]
                    if not all(t in c["equivalent"] for t in term):
                        errors.append(
                            f"hypotheses {h.get('id')}: CIRCULARITY R1: analysis {aid} compares the external "
                            f"{c['outcome']} with its ACS equivalent {sorted(c['equivalent'])}; only that "
                            f"comparison may be tested, not {h.get('term')!r} (a determinant study uses the ACS "
                            "measure as its outcome)")
            if c["kind"] == "direct":
                continue
            for h in tested:
                term = [n for n in _formula_names(str(h.get("term", ""))) if n in c["overlap"]]
                just = h.get("circularity_justification")
                if term and not (isinstance(just, str) and len(just.strip()) >= 20):
                    fams = "; ".join(f"{t}: " + ", ".join(f"{lab} {'/'.join(tabs)}" for lab, tabs in c["overlap"][t].items())
                                     for t in term)
                    errors.append(
                        f"hypotheses {h.get('id')}: CIRCULARITY R2: the tested term {h.get('term')!r} is built from "
                        f"inputs of the model that produced {c['outcome']} ({c['source']}, {c['kind']}: {fams}); "
                        "its coefficient partly recovers that model, not the world. Test a direct outcome (the "
                        "ACS measure, vital records), or add a written circularity_justification (20+ "
                        "characters) to the hypothesis")
    return errors

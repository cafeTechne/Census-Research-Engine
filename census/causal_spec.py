# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 89: causal question specification: target trial and causal diagram (backlog N65).

Hernán and Robins, *Causal Inference: What If* (chapters 3, 6-8, 18, 22; mapping in
``docs/literature/hernan_robins_what_if.md``):
- a causal effect is defined only for a well-defined intervention, stated as the protocol of a **target trial**
  (eligibility, intervention and comparator, time zero, outcome and follow-up, contrast, target population);
- the **causal diagram** (DAG), not an associational rule such as the 10% change-in-estimate rule, decides which
  variables to adjust for. Adjusting for a collider, a mediator or another descendant of treatment induces bias;
  adjusting for an instrument can amplify bias.

DAG checks are exact graph algorithms:
- d-separation by the moralized ancestral graph (Lauritzen et al. 1990);
- the backdoor criterion (Pearl 2009, section 3.3.1): no adjusted variable descends from treatment, and the set
  d-separates treatment and outcome once treatment's outgoing edges are removed;
- minimal sufficient adjustment sets among observed nodes (unmeasured nodes are named ``U...``), by enumeration
  over ancestors of treatment and outcome (DAGs up to 20 nodes).
A path-level explanation (which backdoor paths stay open) comes from path enumeration, which tests cross-check
against d-separation.
"""
import itertools
import re
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

MAX_NODES = 20
TRIAL_FIELDS = ("eligibility", "intervention", "comparator", "time_zero", "outcome", "follow_up", "contrast",
                "target")
CONTRASTS = ("average_effect", "effect_in_treated")
TARGETS = ("super_population", "these_areas")
# Exposures that are not interventions unless the specification names one (Hernán and Robins 3.4-3.5).
SOCIAL_EXPOSURE_PATTERN = re.compile(
    r"pover|income|race|racial|black|white|hispanic|latino|asian|ethnic|educat|college|degree|ses\b|socioecon|"
    r"segregat|depriv|unemploy|wealth|class\b|immigra|foreign_born|language|english", re.I)
TEXT = "Hernán and Robins 2020"


class DagError(ValueError):
    pass


def unmeasured(node: str) -> bool:
    """Unmeasured (latent) nodes are named U, U1, U_x, ... (not usable for adjustment)."""
    return bool(re.fullmatch(r"U(\d+|_\w+)?", node))


def parse_dag(edges: Iterable[Any], nodes: Iterable[str] = ()) -> Dict[str, Set[str]]:
    """Children map from edges given as ``"A -> B"`` strings or ``[A, B]`` pairs; refuses cycles and self-loops."""
    children: Dict[str, Set[str]] = {n: set() for n in nodes}
    for e in edges:
        if isinstance(e, str):
            parts = [p.strip() for p in e.split("->")]
            if len(parts) < 2 or not all(parts):
                raise DagError(f"edge {e!r} must look like 'A -> B' (chains 'A -> B -> C' allowed)")
            pairs = list(zip(parts, parts[1:]))
        elif isinstance(e, (list, tuple)) and len(e) == 2 and all(isinstance(x, str) and x for x in e):
            pairs = [tuple(e)]
        else:
            raise DagError(f"edge {e!r} must be 'A -> B' or [A, B]")
        for a, b in pairs:
            if a == b:
                raise DagError(f"self-loop on {a!r}")
            for n in (a, b):
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", n):
                    raise DagError(f"node name {n!r} must be a variable name")
            children.setdefault(a, set()).add(b)
            children.setdefault(b, set())
    if len(children) > MAX_NODES:
        raise DagError(f"{len(children)} nodes; at most {MAX_NODES} are supported")
    cyc = find_cycle(children)
    if cyc:
        raise DagError("the diagram has a cycle: " + " -> ".join(cyc))
    return children


def find_cycle(children: Mapping[str, Set[str]]) -> Optional[List[str]]:
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(n):
        state[n] = 1
        stack.append(n)
        for c in sorted(children.get(n, ())):
            if state.get(c) == 1:
                return stack[stack.index(c):]+[c]
            if c not in state:
                r = visit(c)
                if r:
                    return r
        state[n] = 2
        stack.pop()
        return None
    for n in sorted(children):
        if n not in state:
            r = visit(n)
            if r:
                return r
    return None


def parents_of(children: Mapping[str, Set[str]]) -> Dict[str, Set[str]]:
    par: Dict[str, Set[str]] = {n: set() for n in children}
    for a, cs in children.items():
        for b in cs:
            par[b].add(a)
    return par


def ancestors(children: Mapping[str, Set[str]], xs: Iterable[str]) -> Set[str]:
    """xs and all their ancestors."""
    par = parents_of(children)
    out, todo = set(xs), list(xs)
    while todo:
        for p in par[todo.pop()]:
            if p not in out:
                out.add(p)
                todo.append(p)
    return out


def descendants(children: Mapping[str, Set[str]], xs: Iterable[str]) -> Set[str]:
    """xs and all their descendants."""
    out, todo = set(xs), list(xs)
    while todo:
        for c in children[todo.pop()]:
            if c not in out:
                out.add(c)
                todo.append(c)
    return out


def d_separated(children: Mapping[str, Set[str]], xs: Iterable[str], ys: Iterable[str], zs: Iterable[str]) -> bool:
    """True when xs and ys are d-separated given zs (moralized ancestral graph)."""
    xs, ys, zs = set(xs), set(ys), set(zs)
    keep = ancestors(children, xs | ys | zs)
    par = parents_of(children)
    nbr: Dict[str, Set[str]] = {n: set() for n in keep}
    for n in keep:
        ps = [p for p in par[n] if p in keep]
        for p in ps:
            nbr[n].add(p); nbr[p].add(n)
        for a, b in itertools.combinations(ps, 2):  # marry parents
            nbr[a].add(b); nbr[b].add(a)
    seen = set(xs - zs)
    todo = list(seen)
    while todo:
        n = todo.pop()
        if n in ys:
            return False
        for m in nbr[n]:
            if m not in zs and m not in seen:
                seen.add(m)
                todo.append(m)
    return True


def _without_out_edges(children: Mapping[str, Set[str]], t: str) -> Dict[str, Set[str]]:
    g = {n: set(cs) for n, cs in children.items()}
    g[t] = set()
    return g


def paths(children: Mapping[str, Set[str]], a: str, b: str) -> List[List[Tuple[str, str]]]:
    """All simple paths from a to b in the skeleton, as [(node, arrow)] where arrow is '->' or '<-' toward the next."""
    par = parents_of(children)
    out = []

    def walk(n, path, seen):
        if n == b:
            out.append(path)
            return
        for c in sorted(children[n]):
            if c not in seen:
                walk(c, path+[(n, "->")], seen | {c})
        for p in sorted(par[n]):
            if p not in seen:
                walk(p, path+[(n, "<-")], seen | {p})
    walk(a, [], {a})
    return [p+[(b, "")] for p in out]


def path_open(children: Mapping[str, Set[str]], path: Sequence[Tuple[str, str]], zs: Set[str]) -> bool:
    """A path is open given zs when every collider on it is in zs or has a descendant in zs, and no non-collider is."""
    for i in range(1, len(path)-1):
        node = path[i][0]
        into_from_left = path[i-1][1] == "->"
        into_from_right = path[i][1] == "<-"
        if into_from_left and into_from_right:  # collider
            if not (descendants(children, [node]) & zs):
                return False
        elif node in zs:
            return False
    return True


def path_text(path: Sequence[Tuple[str, str]]) -> str:
    return " ".join(f"{n} {a}".strip() for n, a in path)


def backdoor_paths(children: Mapping[str, Set[str]], t: str, y: str) -> List[List[Tuple[str, str]]]:
    """Paths from t to y that start with an arrow into t."""
    return [p for p in paths(children, t, y) if p[0][1] == "<-"]


def check_adjustment(children: Mapping[str, Set[str]], treatment: str, outcome: str,
                     adjust: Iterable[str]) -> Dict[str, Any]:
    """Backdoor check of one adjustment set, with reasons (path-level) and role flags."""
    for n in (treatment, outcome):
        if n not in children:
            raise DagError(f"{n!r} is not a node of the diagram")
    zs = set(adjust)
    unknown = sorted(zs - set(children))
    if unknown:
        raise DagError(f"adjusted variables not in the diagram: {unknown} (add them, with their arrows)")
    desc_t = descendants(children, [treatment]) - {treatment}
    anc_y = ancestors(children, [outcome])
    mediators = sorted(z for z in zs if z in desc_t and z in anc_y)
    other_desc = sorted(z for z in zs if z in desc_t and z not in anc_y)
    latent = sorted(z for z in zs if unmeasured(z))
    blocked = d_separated(_without_out_edges(children, treatment), [treatment], [outcome], zs)
    open_bd = [path_text(p) for p in backdoor_paths(children, treatment, outcome) if path_open(children, p, zs)]
    colliders = sorted(z for z in zs if z not in desc_t
                       and _opens_path(children, treatment, outcome, z, zs))
    no_t = {n: {c for c in cs if c != treatment} for n, cs in children.items() if n != treatment}
    instruments = sorted(z for z in zs if z not in desc_t and treatment in children[z]
                         and d_separated(no_t, [z], [outcome], set())
                         and not _on_backdoor(children, treatment, outcome, z))
    sufficient = blocked and not mediators and not other_desc and not latent
    problems = []
    if mediators:
        problems.append(f"adjusts for mediator(s) {mediators} (on the causal path from {treatment} to {outcome}): "
                        "removes part of the effect and can open collider paths (Hernán and Robins 18.2)")
    if other_desc:
        problems.append(f"adjusts for descendant(s) of treatment {other_desc}: selection-type bias (Hernán and "
                        "Robins 18.2, Figure 18.3)")
    if colliders:
        problems.append(f"adjusting for {colliders} opens a non-causal path through a collider (M-bias; Hernán and "
                        "Robins 7.4, Figure 7.4)")
    if latent:
        problems.append(f"{latent} are unmeasured and cannot be adjusted for")
    if not blocked:
        problems.append("backdoor path(s) remain open: " + "; ".join(open_bd[:5]) if open_bd else
                        "the set does not d-separate treatment and outcome without treatment's outgoing arrows")
    warnings = []
    if instruments:
        warnings.append(f"{instruments} affect the outcome only through treatment (instrument-like); adjusting for "
                        "them adds no control of confounding and can amplify any residual bias (Hernán and Robins 18.2)")
    return dict(treatment=treatment, outcome=outcome, adjusted=sorted(zs), sufficient=sufficient,
                backdoor_blocked=blocked, open_backdoor_paths=open_bd, mediators=mediators,
                treatment_descendants=other_desc, colliders_opened=colliders, instruments=instruments,
                unmeasured_adjusted=latent, problems=problems, warnings=warnings)


def _opens_path(children, t, y, z, zs) -> bool:
    """Adjusting for z (with the rest of zs) opens a backdoor path that is closed without it (z acts as a collider
    or a collider's descendant on that path)."""
    rest = zs - {z}
    return any(not path_open(children, p, rest) and path_open(children, p, zs) for p in backdoor_paths(children, t, y))


def _on_backdoor(children, t, y, z) -> bool:
    return any(any(n == z for n, _ in p[1:-1]) and path_open(children, p, set())
               for p in backdoor_paths(children, t, y))


def minimal_adjustment_sets(children: Mapping[str, Set[str]], treatment: str, outcome: str,
                            limit: int = 50) -> List[List[str]]:
    """Minimal sufficient adjustment sets among observed non-descendants of treatment (ancestors of t or y)."""
    desc_t = descendants(children, [treatment])
    cand = sorted(n for n in ancestors(children, [treatment, outcome])
                  if n not in desc_t and n != outcome and not unmeasured(n))
    g = _without_out_edges(children, treatment)
    found: List[FrozenSet[str]] = []
    for k in range(len(cand)+1):
        for combo in itertools.combinations(cand, k):
            s = frozenset(combo)
            if any(f <= s for f in found):
                continue
            if d_separated(g, [treatment], [outcome], s):
                found.append(s)
                if len(found) >= limit:
                    return [sorted(f) for f in found]
    return [sorted(f) for f in found]


def dag_report(dag: Mapping[str, Any], adjust: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Check a ``dag`` block ({edges, treatment, outcome[, nodes]}) and, when given, an adjustment set."""
    if not isinstance(dag, Mapping):
        raise DagError("dag must be an object with edges, treatment and outcome")
    extra = set(dag) - {"edges", "treatment", "outcome", "nodes", "note"}
    if extra:
        raise DagError(f"dag: unknown keys {sorted(extra)}")
    for k in ("edges", "treatment", "outcome"):
        if not dag.get(k):
            raise DagError(f"dag needs {k!r}")
    g = parse_dag(dag["edges"], dag.get("nodes") or ())
    t, y = dag["treatment"], dag["outcome"]
    for n in (t, y):
        if n not in g:
            raise DagError(f"{n!r} is not a node of the diagram")
    if y not in descendants(g, [t]):
        raise DagError(f"the diagram has no directed path from {t!r} to {y!r}: there is no effect to estimate")
    out: Dict[str, Any] = dict(nodes=len(g), treatment=t, outcome=y,
                               minimal_adjustment_sets=minimal_adjustment_sets(g, t, y))
    if not out["minimal_adjustment_sets"]:
        out["identification"] = ("no sufficient set of observed variables: unmeasured confounding cannot be blocked "
                                 "by adjustment (consider an instrument, a difference design or bias analysis)")
    if adjust is not None:
        out["check"] = check_adjustment(g, t, y, adjust)
    out["source"] = TEXT
    return out


def formula_adjustment(formula: str, treatment: str) -> Tuple[str, List[str]]:
    """(outcome, adjustment variables) from 'y ~ t + a + C(b) + a:b'; interaction terms count their variables."""
    if "~" not in formula:
        raise DagError("formula needs '~'")
    lhs, rhs = formula.split("~", 1)
    names = []
    for n in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", rhs):
        if n in ("C", "np", "log", "I", "Q") or n in names:
            continue
        names.append(n)
    if treatment not in names:
        raise DagError(f"the treatment {treatment!r} is not in the formula {formula!r}")
    return lhs.strip(), [n for n in names if n != treatment]


def trial_errors(spec: Any) -> List[str]:
    """Errors in a ``causal_question`` (target trial) block."""
    if not isinstance(spec, Mapping):
        return ["causal_question must be an object with the target-trial fields " + ", ".join(TRIAL_FIELDS)]
    errs = [f"causal_question: unknown key {k!r}; allowed {list(TRIAL_FIELDS)+['exposure', 'versions', 'note']}"
            for k in spec if k not in TRIAL_FIELDS+("exposure", "versions", "note")]
    for k in TRIAL_FIELDS:
        v = spec.get(k)
        if not isinstance(v, str) or not v.strip():
            errs.append(f"causal_question: {k!r} is required (text)")
    if spec.get("contrast") not in (None,)+CONTRASTS and isinstance(spec.get("contrast"), str):
        errs.append(f"causal_question: contrast must be one of {list(CONTRASTS)}")
    if spec.get("target") not in (None,)+TARGETS and isinstance(spec.get("target"), str):
        errs.append(f"causal_question: target must be one of {list(TARGETS)} (Hernán and Robins 10.3)")
    if isinstance(spec.get("intervention"), str) and isinstance(spec.get("comparator"), str) \
            and spec["intervention"].strip().lower() == spec["comparator"].strip().lower():
        errs.append("causal_question: intervention and comparator are the same")
    return errs


def trial_warnings(spec: Optional[Mapping[str, Any]], exposure: Optional[str]) -> List[str]:
    """Well-defined-intervention warnings (Hernán and Robins 3.4-3.5)."""
    out = []
    social = bool(exposure and SOCIAL_EXPOSURE_PATTERN.search(exposure))
    if spec is None:
        out.append("associational (no causal question specified): state the target trial (eligibility, "
                   "intervention and comparator, time zero, outcome, follow-up, contrast, target) before reading this "
                   "as a causal effect (Hernán and Robins chapters 3 and 22)")
        if social:
            out.append(f"{exposure!r} is a social characteristic, not an intervention: many different interventions "
                       "could change it, with different effects (Hernán and Robins 3.4-3.5)")
    elif social and not (spec.get("versions") or "").strip():
        out.append(f"{exposure!r} is a social characteristic: name the intervention that changes it and the versions "
                   "that matter ('versions' field); otherwise consistency is doubtful (Hernán and Robins 3.4-3.5)")
    return out


def trial_text(spec: Mapping[str, Any]) -> List[str]:
    """Methods-text lines describing the target trial."""
    lab = {"eligibility": "Eligibility", "intervention": "Intervention", "comparator": "Comparator",
           "time_zero": "Time zero", "outcome": "Outcome", "follow_up": "Follow-up", "contrast": "Causal contrast",
           "target": "Target population", "versions": "Versions of the intervention"}
    tgt = {"super_population": "a super-population from which these areas are viewed as a sample",
           "these_areas": "these areas themselves (finite population)"}
    lines = []
    for k, name in lab.items():
        if spec.get(k):
            v = tgt.get(spec[k], spec[k]) if k == "target" else spec[k]
            lines.append(f"{name}: {v}")
    return lines


def assess(*, causal_question: Optional[Mapping[str, Any]] = None, dag: Optional[Mapping[str, Any]] = None,
           treatment: Optional[str] = None, adjust: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Tool-level assessment for exploratory causal calls: errors are reported as problems, never raised."""
    out: Dict[str, Any] = {"label": "causal (specified)" if causal_question else "associational (no causal question "
                           "specified)", "source": TEXT}
    problems: List[str] = []
    if causal_question is not None:
        problems += trial_errors(causal_question)
        out["target_trial"] = trial_text(causal_question) if isinstance(causal_question, Mapping) else []
    out["warnings"] = trial_warnings(causal_question if isinstance(causal_question, Mapping) else None,
                                     (causal_question or {}).get("exposure") if isinstance(causal_question, Mapping)
                                     and causal_question.get("exposure") else treatment)
    if dag is not None:
        try:
            d = dict(dag)
            if treatment and not d.get("treatment"):
                d["treatment"] = treatment
            rep = dag_report(d, adjust)
            out["dag"] = rep
            if "check" in rep:
                problems += rep["check"]["problems"]
                out["warnings"] += rep["check"]["warnings"]
            if rep.get("identification"):
                problems.append(rep["identification"])
        except DagError as exc:
            problems.append(f"dag: {exc}")
    out["problems"] = problems
    if problems and causal_question:
        out["label"] = "causal question specified, but the adjustment is not justified by the diagram"
    return out

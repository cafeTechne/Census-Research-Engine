# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 83: declared covariable roles (Foundations of Epidemiology chapters 7-8).

A manifest may declare ``"covariables": {"<name>": "confounder" | "effect_modifier" | "mediator" |
"direction_uncertain"}`` before analysis:
- a mediator (on the causal pathway) must not appear in any formula;
- an effect modifier must enter formulas only through an interaction with another term (``a:b`` or ``a*b``) or be
  analysed by stratum, so its stratum-specific associations are reported rather than adjusted away;
- confounders may appear as main terms; ``direction_uncertain`` marks covariables whose causal direction is unclear
  (both analyses are expected; Round 86 runs them).
"""
import re
from typing import Any, List, Mapping

ROLES = ("confounder", "effect_modifier", "mediator", "direction_uncertain")


def _terms(formula: str) -> List[str]:
    rhs = formula.split("~", 1)[1] if "~" in formula else ""
    return [t.strip() for t in re.split(r"\+|-", rhs) if t.strip()]


def covariable_errors(manifest: Mapping[str, Any]) -> List[str]:
    cov = manifest.get("covariables")
    if cov is None:
        return []
    if not isinstance(cov, dict) or not all(isinstance(k, str) for k in cov):
        return ["covariables must map variable names to roles"]
    errors = [f"covariables: {k!r} has role {v!r}; allowed {list(ROLES)}" for k, v in cov.items() if v not in ROLES]
    for a in manifest.get("analyses") or []:
        f = str(a.get("formula", ""))
        if "~" not in f:
            continue
        terms = _terms(f)
        names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f.split("~", 1)[1]))
        for name, role in cov.items():
            if name not in names:
                continue
            if role == "mediator":
                errors.append(f"analyses ({a.get('id')}): {name!r} is declared a mediator (on the causal pathway) "
                              "and must not be adjusted for in the formula")
            if role == "effect_modifier":
                main = [t for t in terms if re.fullmatch(rf"(?:C\()?{re.escape(name)}\)?", t)]
                inter = [t for t in terms if (":" in t or "*" in t) and re.search(rf"\b{re.escape(name)}\b", t)]
                if main and not inter:
                    errors.append(f"analyses ({a.get('id')}): {name!r} is declared an effect modifier; enter it "
                                  "through an interaction (or stratify) so stratum-specific associations are reported "
                                  "rather than adjusted away")
    return errors

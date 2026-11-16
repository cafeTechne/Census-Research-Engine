# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest derivations definitions."""

from typing import Any, Dict, List, Mapping



def _age_standardized_errors(d: Mapping[str, Any], errors: List[str]) -> None:
    """Validation of an ``age_standardized`` derivation (PLAN_ROUND_20 A1)."""
    from ..derived import standardization_weights
    from ..standardize import STANDARDS, normalize_bands, standard_weights
    name = d.get("name")
    groups = d.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append(f"derivation {name!r}: age_standardized needs 'groups', one {{num, den}} per age band")
        return
    for k, g in enumerate(groups):
        if not isinstance(g, Mapping) or g.get("num") is None or g.get("den") is None:
            errors.append(f"derivation {name!r}: groups[{k}] needs 'num' and 'den'")
            return
    for key in ("num", "den"):
        if d.get(key) is not None:
            errors.append(f"derivation {name!r}: age_standardized takes 'groups', not {key!r}")
    standard = d.get("standard")
    if standard is None:
        errors.append(f"derivation {name!r}: 'standard' is required ({list(STANDARDS)} or 'custom' with 'weights')")
        return
    if standard != "custom" and standard not in STANDARDS:
        errors.append(f"derivation {name!r}: unknown standard {standard!r}; expected one of {list(STANDARDS)} "
                      "or 'custom'")
        return
    if standard != "custom":
        try:
            bands = normalize_bands(d.get("bands"))
        except ValueError as exc:
            errors.append(f"derivation {name!r}: {exc}")
            return
        if len(bands) != len(groups):
            errors.append(f"derivation {name!r}: {len(bands)} bands for {len(groups)} groups")
            return
        try:
            expected = standard_weights(bands, standard)
        except ValueError as exc:
            errors.append(f"derivation {name!r}: {exc}")
            return
        given = d.get("weights")
        if given is not None and (not isinstance(given, list) or len(given) != len(expected) or any(
                not isinstance(x, (int, float)) or abs(float(x) - e) > 1e-12 for x, e in zip(given, expected))):
            errors.append(f"derivation {name!r}: weights do not match the {standard} standard over these bands "
                          f"(expected {expected}); omit them so create_manifest fills them in, or declare "
                          "\"standard\": \"custom\"")
            return
    elif d.get("weights") is None:
        errors.append(f"derivation {name!r}: standard 'custom' needs explicit 'weights'")
        return
    if d.get("weights") is not None:
        try:
            standardization_weights(d)
        except ValueError as exc:
            errors.append(f"derivation {name!r}: {exc}")


def _fill_derivation_defaults(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fill omitted ``weights`` of ``age_standardized`` derivations (in place) from their
    standard, so the hash fixes them; returns one ``{"derivation": i, "weights": [...]}``
    entry per filled derivation. Invalid entries are left for validation to report."""
    filled: List[Dict[str, Any]] = []
    derivations = manifest.get("derivations")
    for i, d in enumerate(derivations if isinstance(derivations, list) else []):
        if not (isinstance(d, dict) and d.get("op") == "age_standardized" and d.get("weights") is None
                and d.get("standard") not in (None, "custom")):
            continue
        try:
            from ..standardize import standard_weights
            d["weights"] = standard_weights(d.get("bands"), str(d["standard"]))
        except (ValueError, TypeError):
            continue
        filled.append({"derivation": i, "weights": list(d["weights"])})
    return filled

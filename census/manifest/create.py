# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest create definitions."""

from census.data_integrity import integrity_errors
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union
from .adjustments import (
    _FILL_REASONS,
    _fill_adjustment_defaults,
)
from .derivations import (
    _fill_derivation_defaults,
)
from .external import (
    _ext_source_text,
    external_circularity,
)
from .replicates import (
    _declared_covariates_only,
    census_vre_source,
    vre_unavailable,
)
from .schema import (
    load_manifest,
    manifest_hash,
)
from .validate import (
    validate_manifest,
)



@integrity_errors
def create_manifest(
    path_or_dict: Union[str, Path, Mapping[str, Any]], path: Optional[Union[str, Path]] = None,
    client: Any = None, resolve: bool = True,
) -> Dict[str, Any]:
    """Validate a manifest and record its SHA-256 before any data are pulled.

    When valid and ``path`` is given (or the input was a dict and ``path``
    is given) the manifest is written there as pretty JSON. Commit the file
    to the repository to fix the pre-registration (PLAN_ROUND_8 decision 3).

    An RPP adjustment without ``rpp_year`` gets the latest year in the active RPP
    table before validation and hashing, so the hash fixes the applied year (with
    several releases: ``dollar_year``, ``price_index`` and ``rpp_years`` get their
    defaults, :func:`_fill_adjustment_defaults`); the result says so (``filled``, ``notes``) and the completed manifest is written to
    ``path``, or, when no ``path`` is given, to a new sibling file
    ``<name>.completed.json`` (the input file is never overwritten; a dict input
    without ``path`` gets it in ``manifest``). Commit and run the completed file.
    Returns ``{"hash", "path", "errors", "valid", "notes", "filled"}`` (and
    ``"manifest"`` when something was filled in).
    """
    manifest = load_manifest(path_or_dict)
    filled = _fill_adjustment_defaults(manifest) + _fill_derivation_defaults(manifest)
    errors = validate_manifest(manifest, resolve=resolve, client=client)
    out_path = str(path) if path else (str(path_or_dict) if not isinstance(path_or_dict, Mapping) else None)
    write_to = path
    if not path and filled and out_path:
        src = Path(out_path)
        write_to = str(src.with_name(src.stem + ".completed" + (src.suffix or ".json")))
        out_path = write_to
    if not errors and write_to:
        Path(write_to).parent.mkdir(parents=True, exist_ok=True)
        Path(write_to).write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                  encoding="utf-8", newline="\n")
    where = f" (written to {write_to})" if write_to and not errors else "; commit the completed manifest"
    notes = [f"adjustments[{f['adjustment']}]: {k} was omitted; filled in with {json.dumps(v)}, "
             + _FILL_REASONS[k] + ", before hashing" + where
             for f in filled if "adjustment" in f for k, v in f.items() if k != "adjustment"]
    notes += [f"derivations[{f['derivation']}]: weights were omitted; filled in with {json.dumps(f['weights'])} "
              "from the derivation's standard population, before hashing" + where
              for f in filled if "derivation" in f]
    if census_vre_source(manifest):
        missing = vre_unavailable(manifest)
        if missing:
            notes.append("replicates (census_vre): no published Census VRE replicates for "
                         + "; ".join(f"{u['variable']} ({u['table']}, {u['release']})" for u in missing)
                         + ". Under the strict confirmatory policy a replicate analysis that uses them blocks "
                         "(replicates_incomplete) unless it declares \"replicate_scope\": \"covariates_only\" "
                         "(outcome without replicates, held at its estimate in the refits)")
        no_vre = {u["variable"] for u in missing}
        for aid, held in _declared_covariates_only(manifest).items():
            listed = [v for v in held if v not in no_vre]
            if listed:
                notes.append(f"analyses {aid}: replicate_scope 'covariates_only' declared, but the Census VRE "
                             f"registry lists replicates for the outcome {listed} in every release. The outcome "
                             "will be held at its estimate in every refit as declared (the hashed declaration "
                             "governs; the run records whether its replicates were available); remove the "
                             "declaration before hashing to use the outcome's replicates")
    if not errors:
        from ..health_sources import CIRCULARITY_RULE
        hyps = [h for h in manifest.get("hypotheses") or [] if isinstance(h, Mapping)]
        for c in external_circularity(manifest):
            model = _ext_source_text(c)
            if c["equivalent"]:
                notes.append(f"analyses {c['analysis']}: MEASUREMENT COMPARISON: the outcome {c['outcome']} "
                             f"({c['source']} {c['measure']}) is compared with its direct ACS equivalent "
                             f"{sorted(c['equivalent'])} (allowed by rule R1; a determinant study would use the "
                             "ACS measure as its outcome)")
            if c["kind"] == "direct":
                notes.append(f"analyses {c['analysis']}: the outcome {c['outcome']} is a direct external estimate "
                             f"({c['source']}: {model}); no model inputs, so no circularity check applies")
                continue
            justified = [h.get("id") for h in hyps if h.get("analysis") == c["analysis"]
                         and h.get("circularity_justification")]
            if c["overlap"]:
                notes.append(f"analyses {c['analysis']}: CIRCULARITY: the outcome {c['outcome']} is {c['kind'].replace('_', '-')} "
                             f"({c['source']}: {model}); covariates "
                             + "; ".join(k + " (" + ", ".join(lab + ": " + "/".join(t) for lab, t in v.items()) + ")"
                                         for k, v in c["overlap"].items())
                             + " measure the model's own inputs, so their coefficients partly recover the source "
                             "model, not the world (allowed as controls; tested terms need a written "
                             "circularity_justification"
                             + (f", given for {justified}" if justified else "") + ")")
            else:
                notes.append(f"analyses {c['analysis']}: the outcome {c['outcome']} is {c['kind'].replace('_', '-')} ({c['source']}: "
                             f"{model}); associations with covariates outside the model arise only through their "
                             "correlation with the model's inputs")
        if manifest.get("external"):
            notes.append("external outcomes: " + CIRCULARITY_RULE)
    if manifest.get("exploratory"):
        notes.append("registered as exploratory")
    out = {"hash": manifest_hash(manifest), "path": out_path, "errors": errors, "valid": not errors,
           "notes": notes, "filled": filled}
    if filled:
        out["manifest"] = manifest
    return out

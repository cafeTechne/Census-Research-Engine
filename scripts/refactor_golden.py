# SPDX-License-Identifier: AGPL-3.0-or-later
"""Golden snapshot of census.manifest's offline behaviour, for behaviour-preserving refactors.

Records, for every example manifest and a deterministic mutation corpus derived from them, the exact
output of validate_manifest(resolve=False), create_manifest(resolve=False) (errors, notes, hash),
methods_section(), tables_and_refs(), external_circularity() and circularity_errors(). Exceptions are
recorded as "<ExceptionType>: <message>". Run before and after a refactor; the two files must be
byte-identical.

Usage: .venv/bin/python scripts/refactor_golden.py OUT.json
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from census.manifest import (create_manifest, circularity_errors, external_circularity, load_manifest,
                             methods_section, tables_and_refs, validate_manifest)

ROOT = Path(__file__).resolve().parents[1]


def _safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001 - the exception text is part of the snapshot
        return f"{type(e).__name__}: {e}"


def mutations(m):
    """Deterministic single-change variants: drop each top-level key, blank each analysis's args,
    drop each analysis arg, drop each hypothesis key, and flip exploratory."""
    out = []
    for k in sorted(m):
        v = copy.deepcopy(m)
        del v[k]
        out.append((f"drop:{k}", v))
    for i, a in enumerate(m.get("analyses") or []):
        v = copy.deepcopy(m)
        v["analyses"][i]["args"] = {}
        out.append((f"analyses[{i}].args={{}}", v))
        for k in sorted((a.get("args") or {})):
            v = copy.deepcopy(m)
            del v["analyses"][i]["args"][k]
            out.append((f"analyses[{i}].args-{k}", v))
        v = copy.deepcopy(m)
        v["analyses"][i]["method"] = "no_such_method"
        out.append((f"analyses[{i}].method=bad", v))
    for i, h in enumerate(m.get("hypotheses") or []):
        for k in sorted(h):
            v = copy.deepcopy(m)
            del v["hypotheses"][i][k]
            out.append((f"hypotheses[{i}]-{k}", v))
    v = copy.deepcopy(m)
    v["exploratory"] = not bool(m.get("exploratory"))
    out.append(("exploratory-flip", v))
    return out


def snapshot(m):
    return {
        "validate": _safe(validate_manifest, copy.deepcopy(m), resolve=False),
        "create": _safe(lambda: {k: v for k, v in create_manifest(copy.deepcopy(m), resolve=False).items()
                                 if k in ("errors", "valid", "notes", "hash", "filled")}),
        "methods": _safe(methods_section, copy.deepcopy(m)),
        "tables_and_refs": _safe(tables_and_refs, copy.deepcopy(m)),
        "external_circularity": _safe(external_circularity, copy.deepcopy(m)),
        "circularity_errors": _safe(circularity_errors, copy.deepcopy(m)),
    }


def main(argv):
    out = {}
    for path in sorted((ROOT / "examples" / "manifests").glob("*.json")):
        m = load_manifest(path)
        out[path.name] = {"base": snapshot(m)}
        for label, v in mutations(m):
            out[path.name][label] = snapshot(v)
    text = json.dumps(out, indent=1, sort_keys=True, default=str) + "\n"
    Path(argv[1]).write_text(text, encoding="utf-8")
    print(f"{sum(len(v) for v in out.values())} snapshots from {len(out)} manifests -> {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

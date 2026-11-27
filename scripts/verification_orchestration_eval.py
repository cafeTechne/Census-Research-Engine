#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 124 (Gap Audit Phase 4): Deterministic proposition-preserving verification orchestration audit."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from census.verification import (
    BoundRequest,
    canonical_json,
    golden_proposition,
    operator_review,
    request_arguments,
)

GOLDEN_CASES = [
    ("zero_diagonal", "proved", True),
    ("row_sum", "proved", True),
    ("weighted_squares", "proved", True),
    ("centering_idempotence", "proved", True),
    ("false_diagonal_formula", "refuted", False),
    ("centering_independence", "refuted", False),
]


def run_eval() -> Dict[str, Any]:
    results = []
    binding_attacks_blocked = 0
    binding_attacks_total = 0

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name, expected_status, expected_holds in GOLDEN_CASES:
            prop = golden_proposition(name)
            rev = operator_review(prop, reviewer="phase4-auditor")
            req_path = root / f"{name}.json"
            req_path.write_text(canonical_json({"proposition": prop, "review": rev}), encoding="utf-8")
            bound = BoundRequest.from_file(str(req_path))
            out = bound.verify(**request_arguments(prop))
            rec = out.get("verification", out)
            ok = (
                rec["verification_status"] == expected_status
                and rec["claim_holds"] is expected_holds
                and rec["evidence_verified"] is True
                and rec["proposition_id"] == prop["proposition_id"]
            )
            results.append({"case": name, "status": rec["verification_status"],
                            "claim_holds": rec["claim_holds"], "evidence_verified": rec["evidence_verified"], "ok": ok})

        # Binding attack 1: substitute true zero_diagonal args against pinned false_diagonal_formula
        binding_attacks_total += 1
        false_prop = golden_proposition("false_diagonal_formula")
        true_prop = golden_proposition("zero_diagonal")
        p_atk = root / "atk_sub.json"
        p_atk.write_text(canonical_json({"proposition": false_prop,
                                         "review": operator_review(false_prop, reviewer="phase4-auditor")}),
                         encoding="utf-8")
        try:
            out_atk = BoundRequest.from_file(str(p_atk)).verify(**request_arguments(true_prop))
            rec_atk = out_atk.get("verification", out_atk)
            if (out_atk.get("success") is False or rec_atk.get("verification_status") == "error") and (
                out_atk.get("error_code") == "PROPOSITION_MISMATCH"
                or rec_atk.get("error_code") == "PROPOSITION_MISMATCH"
            ):
                binding_attacks_blocked += 1
        except Exception as exc:
            if "PROPOSITION_MISMATCH" in str(exc) or getattr(exc, "code", "") == "PROPOSITION_MISMATCH":
                binding_attacks_blocked += 1

        # Binding attack 2: unreviewed formalization must remain inconclusive (never certified)
        binding_attacks_total += 1
        p_unrev = root / "atk_unrev.json"
        p_unrev.write_text(canonical_json({"proposition": true_prop, "review": None}), encoding="utf-8")
        out_unrev = BoundRequest.from_file(str(p_unrev)).verify(**request_arguments(true_prop))
        rec_unrev = out_unrev.get("verification", out_unrev)
        if rec_unrev["verification_status"] == "inconclusive" and rec_unrev["claim_holds"] is None:
            binding_attacks_blocked += 1

    all_ok = all(r["ok"] for r in results) and (binding_attacks_blocked == binding_attacks_total)
    return {
        "ok": all_ok,
        "cases_passed": sum(1 for r in results if r["ok"]),
        "cases_total": len(results),
        "binding_attacks_blocked": binding_attacks_blocked,
        "binding_attacks_total": binding_attacks_total,
        "cases": results,
    }


def main() -> None:
    report = run_eval()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

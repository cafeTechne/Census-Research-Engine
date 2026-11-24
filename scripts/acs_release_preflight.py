#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 117: Offline preflight readiness check for Backlog N39 (ACS 2021-2025 5-year release refresh).

Inspects bundled metadata archive coverage, price-index & RPP integrity checksums, and crosswalk
validity without making any network calls. Prints a JSON readiness report and recommended refresh commands.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from census import inflation, rpp
from census.concordance import validate_all_crosswalks


def run_preflight(target_year: int = 2025) -> dict:
    # 1. Metadata archive vintages
    meta_dir = ROOT / "metadata"
    vintages = sorted(int(p.name) for p in meta_dir.iterdir() if p.is_dir() and p.name.isdigit()) if meta_dir.exists() else []
    has_target_meta = target_year in vintages

    # 2. Price-index integrity & coverage
    price_status = {}
    for idx_name in ("r-cpi-u-rs", "cpi-u", "c-cpi-u"):
        try:
            tbl = inflation.load_price_index(idx_name)
            years = sorted(int(y) for y in tbl.keys())
            price_status[idx_name] = {
                "integrity_ok": True,
                "min_year": years[0] if years else None,
                "max_year": years[-1] if years else None,
                "has_target_year": target_year in years,
            }
        except Exception as exc:
            price_status[idx_name] = {"integrity_ok": False, "error": str(exc)}

    # 3. RPP parity integrity
    try:
        rpp_info = rpp.price_parity_info()
        rpp_status = {"integrity_ok": True, "years": rpp_info.get("years", []),
                      "has_target_year": target_year in (rpp_info.get("years") or [])}
    except Exception as exc:
        rpp_status = {"integrity_ok": False, "error": str(exc)}

    # 4. Crosswalk validation
    cw_dir = ROOT / "crosswalks"
    cw_errors = []
    if cw_dir.exists():
        try:
            res = validate_all_crosswalks()
            cw_errors = res if isinstance(res, list) else (res.get("errors", []) if isinstance(res, dict) else [])
        except Exception as exc:
            cw_errors = [str(exc)]

    next_commands = []
    if not has_target_meta:
        next_commands.append(f"python scripts/fetch_metadata_archive.py --years {target_year}")
    if not all(v.get("has_target_year") for v in price_status.values()):
        next_commands.append("python scripts/update_price_indexes.py")
    if not rpp_status.get("has_target_year"):
        next_commands.append("python scripts/update_price_parities.py")

    ready = (
        has_target_meta
        and all(v.get("integrity_ok") and v.get("has_target_year") for v in price_status.values())
        and bool(rpp_status.get("integrity_ok"))
        and len(cw_errors) == 0
    )
    return {
        "target_year": target_year,
        "ready": ready,
        "metadata_vintages": vintages,
        "has_target_metadata": has_target_meta,
        "price_indexes": price_status,
        "rpp": rpp_status,
        "crosswalk_error_count": len(cw_errors),
        "next_commands": next_commands,
    }


def main():
    ap = argparse.ArgumentParser(description="Offline N39 ACS release-refresh preflight check")
    ap.add_argument("--target-year", type=int, default=2025)
    args = ap.parse_args()
    report = run_preflight(args.target_year)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

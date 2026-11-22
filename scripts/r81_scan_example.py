# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 81 exploratory example: clusters of low-birth-weight births in MI and NY counties.

Exploratory; author self-review, not independent; no pre-specified window, so the cluster is descriptive. CHR&R 2025
measure v037 (NCHS natality, 2017-2023): numerator = low-birth-weight births, denominator = live births (exact vital
counts, so the noisy-denominator caveat does not apply). Counties without a published numerator (CHR&R
suppression) are excluded by that stated rule; no count is imputed. Kulldorff Poisson scan, expected counts
proportional to live births, 50% maximum window, 999 replicates. Writes docs/audits/r81_scan_example.md (summary only).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census.health_sources import fetch_chr, parse_chr  # noqa: E402
from census.scan import spatial_scan  # noqa: E402


def main():
    f = parse_chr(fetch_chr(2025)["raw"], {"v037": "lbw"}, states=["26", "36"])
    miss = f[f.lbw_numerator.isna() | f.lbw_denominator.isna()].GEOID.tolist()
    r = spatial_scan(f.assign(Year=2022), "lbw_numerator", population="lbw_denominator", year=2022,
                     exclude=miss or None, exclude_rule="CHR&R did not publish the low-birth-weight count")
    L = ["# Round 81 example: low-birth-weight clusters in MI and NY counties (CHR&R 2025, births 2017-2023)", "",
         "Exploratory (no pre-specified window); author self-review, not independent. Expected counts proportional "
         f"to live births; 50% maximum window; 999 Monte Carlo replicates. {r['counties']} counties scanned "
         f"({len(miss)} excluded: no published count).", "",
         "| Cluster | Counties | Centre | Cases / expected | RR | p (MC) |", "| :--- | ---: | :--- | :--- | ---: | ---: |"]
    for name, c in [("primary", r["primary"])]+[(f"secondary {i+1}", c) for i, c in enumerate(r["secondary"])]:
        if c:
            L.append(f"| {name} | {len(c['counties'])} | {c['center']} | {c['cases']:.0f} / {c['expected']:.0f} | "
                     f"{c['relative_risk']:.2f} | {c['p_value']:.3f} |")
    L += ["", "Primary cluster counties: "+", ".join(r["primary"]["counties"])+".", "",
          "Notes: "+" ".join(r["notes"]), ""]
    (ROOT/"docs/audits/r81_scan_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()

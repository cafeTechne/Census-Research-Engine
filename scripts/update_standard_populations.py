# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build data/standard_populations/us2000.csv from the SEER single-age standard populations.

Values are never typed by hand. Source (National Cancer Institute, SEER):
    https://seer.cancer.gov/stdpopulations/singleages.pops.tables.csv
whose "2000 U.S. Standard Population (Census P25-1130), Single Ages to 84"
column gives ages 0-84 and 85+. That is the standard the National Center for
Health Statistics uses for age adjustment (Klein & Schoenborn 2001, Healthy
People 2010 Statistical Notes 20).

The raw download is kept in data/standard_populations/source/; the sidecar
JSON records the URL, retrieval time and SHA-256 of the raw file and of the
CSV, which census.standardize checks on every load.

Usage:
    python scripts/update_standard_populations.py                 # download
    python scripts/update_standard_populations.py --raw PATH      # use a saved copy
"""

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "standard_populations")
RAW_NAME = "singleages.pops.tables.csv"
SOURCE_URL = "https://seer.cancer.gov/stdpopulations/singleages.pops.tables.csv"
COLUMN = "2000 U.S. Standard Population (Census P25-1130)"
SUBCOLUMN = "Single Ages to 84"
EXPECTED_TOTAL = 274_633_642


def parse(raw: bytes) -> List[Tuple[int, int, int]]:
    """(age_lo, age_hi or -1 for open-ended, population) rows from the SEER table."""
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    header, sub = rows[0], rows[1]
    col = next(i for i in range(len(header)) if header[i].strip() == COLUMN)
    col = next(i for i in range(col, len(sub)) if sub[i].strip() == SUBCOLUMN)
    out: List[Tuple[int, int, int]] = []
    total = None
    for r in rows[2:]:
        if not r or not r[0].strip():
            continue
        label, value = r[0].strip(), r[col].replace(",", "").strip()
        if label == "Total":
            total = int(value)
            continue
        if not value:
            continue
        age = label.split()[0]
        if age.startswith("85"):  # "85/85+": the to-84 column holds 85 and over
            out.append((85, -1, int(value)))
        else:
            a = int(age)
            out.append((a, a, int(value)))
    ages = [lo for lo, _, _ in out]
    if ages != list(range(86)):
        raise ValueError(f"unexpected age rows {ages[:3]}..{ages[-3:]}")
    s = sum(p for _, _, p in out)
    if total != EXPECTED_TOTAL or s != total:
        raise ValueError(f"total mismatch: rows sum {s}, table total {total}, expected {EXPECTED_TOTAL}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", help="saved copy of the SEER file instead of downloading")
    args = ap.parse_args(argv)
    os.makedirs(os.path.join(OUT_DIR, "source"), exist_ok=True)
    raw_path = os.path.join(OUT_DIR, "source", RAW_NAME)
    if args.raw:
        if os.path.abspath(args.raw) != os.path.abspath(raw_path):
            shutil.copyfile(args.raw, raw_path)
    else:
        import requests
        r = requests.get(SOURCE_URL, timeout=60, headers={"User-Agent": "census-research-engine"})
        r.raise_for_status()
        with open(raw_path, "wb") as f:
            f.write(r.content)
    raw = open(raw_path, "rb").read()
    rows = parse(raw)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["age_lo", "age_hi", "population"])
    for lo, hi, p in rows:
        w.writerow([lo, "" if hi < 0 else hi, p])
    csv_bytes = buf.getvalue().encode("utf-8")
    with open(os.path.join(OUT_DIR, "us2000.csv"), "wb") as f:
        f.write(csv_bytes)
    sidecar = {
        "name": "us2000",
        "description": "2000 U.S. standard population (Census P25-1130), single ages 0-84 and 85+",
        "source": SOURCE_URL,
        "source_column": f"{COLUMN} / {SUBCOLUMN}",
        "reference": "Klein, R.J. & Schoenborn, C.A. (2001). Age adjustment using the 2000 projected U.S. "
                     "population. Healthy People 2010 Statistical Notes 20. NCHS.",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_file": f"data/standard_populations/source/{RAW_NAME}",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "total": EXPECTED_TOTAL,
    }
    with open(os.path.join(OUT_DIR, "us2000.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(sidecar, f, indent=2)
        f.write("\n")
    print(json.dumps(sidecar, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

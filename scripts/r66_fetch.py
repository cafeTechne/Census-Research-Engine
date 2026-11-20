# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 66: download (into the engine caches) the public inputs for replications A and B and simulation S.

No comparison with any published value is computed here.
- A: ACS 2019-2023 tract B11002, B11002A, B11002B for the 50 states and DC (CHR's v141 inputs), and B03002 for
  GA, TX, AZ, MI and NY (the engine's standard groups, for the interval part), with the B03002 VRE tract files.
- B: ACS 2019-2023 state B19083 (the published Gini) and the 2019-2023 PUMS housing files of 12 pre-set states.
- S: B17001 tract counts for GA, TX and AZ.
Usage: scripts/r66_fetch.py [--skip-pums]
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import pums, replicate  # noqa: E402
from census.workflows import _client  # noqa: E402

YEAR = 2023
STATES = ["01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21",
          "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
          "40", "41", "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56"]
INTERVAL_STATES = ["13", "48", "04", "26", "36"]          # GA, TX, AZ, MI, NY
SIM_STATES = ["13", "48", "04"]
GINI_STATES = ["56", "50", "10", "35", "28", "04", "13", "26", "36", "48", "06", "37"]  # WY VT DE NM MS AZ GA MI NY TX CA NC


def main():
    c = _client()
    todo = [(s, t, "tract") for s in STATES for t in ("B11002", "B11002A", "B11002B")]
    todo += [(s, "B03002", "tract") for s in INTERVAL_STATES] + [(s, "B17001", "tract") for s in SIM_STATES]
    todo += [(s, "B19083", "state") for s in GINI_STATES]
    for i, (s, t, g) in enumerate(todo):
        if c.fetch(YEAR, s, t, geo_level=g) is None:
            raise SystemExit(f"API failure {t} {s} {g}: {c.last_error}")
        if i % 20 == 0:
            print("api", i, len(todo), flush=True)
    for s in INTERVAL_STATES:
        replicate.fetch_vre("B03002", YEAR, "tract", state_code=s)
        print("vre", s, flush=True)
    if "--skip-pums" not in sys.argv:
        for s in GINI_STATES:
            t0 = time.time()
            pums.fetch_pums(s, YEAR, record="housing", columns=["HINCP", "ADJINC", "TYPEHUGQ", "NP"])
            print("pums", s, round(time.time()-t0), flush=True)


if __name__ == "__main__":
    main()

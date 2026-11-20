# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 66: numeric replications A (CHR 2025 county Black/White dissimilarity) and B (Census state Gini, B19083).

Frozen with the criterion (docs/audits/r66_replication_criterion.md). Inputs are the engine caches filled by
scripts/r66_fetch.py and the CHR measure file pinned by commit and SHA-256. Writes
docs/audits/r66_numeric_replication.md/.json and, for A, a per-county comparison
docs/audits/r66_chr_segregation_comparison.csv.gz (our values beside CHR's published values).

Usage: scripts/r66_numeric_replication.py --criterion-commit SHA [--part A|B|AB]
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from census import pums, replicate, segregation  # noqa: E402
from census.pums_inequality import pums_inequality  # noqa: E402
from census.workflows import _client  # noqa: E402

YEAR = 2023
CHR_COMMIT = "a516395d02b1aa6ff10da092267525a215cc3ff4"
CHR_URL = ("https://raw.githubusercontent.com/countyhealthrankings/county_health_measure_calculations/"
           f"{CHR_COMMIT}/measure_datasets/v141_r2025.csv")
CHR_SHA256 = "2c737ea89db403c0cbf825b10ad2e03fccfcdc4e66fd242eb90b2a9c305636fe"
STATES = ["01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21",
          "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
          "40", "41", "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56"]
EXCLUDED = {"36103", "36111"}            # suppressed by CHR in 2025 (Suffolk, Ulster)
INTERVAL_STATES = ["13", "48", "04", "26", "36"]
GINI_STATES = ["56", "50", "10", "35", "28", "04", "13", "26", "36", "48", "06", "37"]
A_MEDIAN_MAX, A_WITHIN, A_SHARE = .5, 1.0, .90
B_MEDIAN_MAX, B_CONTAIN_MIN = .005, 10
FROZEN = ["scripts/r66_numeric_replication.py", "docs/audits/r66_replication_criterion.md", "census/segregation.py",
          "census/pums_inequality.py", "census/pums_inequality_core.py"]
OUT = ROOT/"docs/audits/r66_numeric_replication"


def frame(client, state, table, geo="tract"):
    rows = client.fetch(YEAR, state, table, geo_level=geo)
    if rows is None:
        raise SystemExit(f"{table} {state} missing: {client.last_error}")
    df = pd.DataFrame(rows[1:], columns=rows[0])
    if geo == "tract":
        df["GEOID"] = df.state+df.county+df.tract
    return df


def chr_values():
    path = Path(os.getenv("CENSUS_REPLICATION_DIR", ROOT/".cache/replication"))/"v141_r2025.csv"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(requests.get(CHR_URL, headers={"User-Agent": "census-research-engine"}, timeout=60).content)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CHR_SHA256:
        raise SystemExit("CHR file hash differs from the pinned value")
    d = pd.read_csv(io.BytesIO(raw), dtype={"statecode": str, "countycode": str, "fipscode": str})
    d = d[(d.countycode != "000") & d.v141_rawvalue.notna()]
    return d.set_index("fipscode").v141_rawvalue.astype(float)


def part_a(client):
    tr = []
    for s in STATES:
        a, w, b = (frame(client, s, t) for t in ("B11002", "B11002A", "B11002B"))
        m = a[["GEOID"]].assign(tot=pd.to_numeric(a.B11002_001E, errors="coerce"))
        m = m.merge(w[["GEOID", "B11002A_001E"]], on="GEOID").merge(b[["GEOID", "B11002B_001E"]], on="GEOID")
        tr.append(m.rename(columns={"B11002A_001E": "white", "B11002B_001E": "black"}))
    tr = pd.concat(tr)
    tr[["white", "black"]] = tr[["white", "black"]].apply(pd.to_numeric, errors="coerce")
    tr["county"] = tr.GEOID.str[:5]
    ours = {}
    for c, g in tr.groupby("county"):
        if c[:2] == "09" or c in EXCLUDED or g.black.sum() < 100:
            continue
        if g[["white", "black"]].isna().any().any():
            continue                                    # CHR: a missing tract makes the county missing
        d = float(segregation._indices(g[["black", "white"]].to_numpy(float)[None])[0, 0])*100
        if d > 0:
            ours[c] = d
    pub = chr_values()
    pub = pub[(pub.index.str[:2] != "09") & ~pub.index.isin(EXCLUDED)]
    both = sorted(set(ours) & set(pub.index))
    cmp_ = pd.DataFrame(dict(county=both, ours=[ours[c] for c in both], published=pub.loc[both].to_numpy()))
    cmp_["difference"] = cmp_.ours-cmp_.published
    med = float(cmp_.difference.abs().median()); share = float((cmp_.difference.abs() <= A_WITHIN).mean())
    out = dict(counties_compared=len(cmp_), only_ours=sorted(set(ours)-set(pub.index)),
               only_published=sorted(set(pub.index)-set(ours)), median_abs_difference=med,
               share_within_1=share, max_abs_difference=float(cmp_.difference.abs().max()),
               large=cmp_[cmp_.difference.abs() > 2].round(3).to_dict("records"),
               replicated=bool(med <= A_MEDIAN_MAX and share >= A_SHARE))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(cmp_.round(6).to_csv(index=False).encode())
    (ROOT/"docs/audits/r66_chr_segregation_comparison.csv.gz").write_bytes(buf.getvalue())
    out["interval_part"] = interval_part(client, pub)
    return out


def interval_part(client, pub):
    """Descriptive: the engine's B03002 non-Hispanic Black vs non-Hispanic White D with VRE replicates."""
    long = pd.concat([replicate.fetch_vre("B03002", YEAR, "tract", state_code=s, lines=[3, 4])
                      for s in INTERVAL_STATES], ignore_index=True)
    long["variable"] = long.variable.map({"B03002_003": "white", "B03002_004": "black"})
    f = long.pivot(index="GEOID", columns="variable", values="estimate")[["black", "white"]].reset_index()
    f["Year"] = YEAR
    rep = long[["GEOID", "variable", *replicate.REPLICATE_COLUMNS]].copy(); rep["Year"] = YEAR
    parts, failed = [], []
    f["county"] = f.GEOID.str[:5]; rep["county"] = rep.GEOID.str[:5]
    for c, fc in f.groupby("county"):
        try:   # deviation 1: per county; a county whose replicate refit is undefined is listed, not fatal
            parts.append(segregation.segregation_replicate(fc.drop(columns="county"), ["black", "white"],
                                                           rep[rep.county == c].drop(columns="county")))
        except Exception as exc:  # noqa: BLE001
            failed.append(dict(county=c, error=type(exc).__name__))
    res = pd.concat(parts, ignore_index=True)
    res = res[res.statistic == "dissimilarity"].copy()
    res["chr_published"] = res.GEOID.map(pub/100)
    keep = ["GEOID", "estimate", "ci_lower", "ci_upper", "noise_level", "validated", "chr_published"]
    keep = [k for k in keep if k in res]
    return dict(counties=int(len(res)), validated=int(res.validated.sum()), failed=failed,
                with_chr_value=int(res.chr_published.notna().sum()),
                table=res[keep].round(4).to_dict("records"))


def part_b(client):
    rows = []
    for s in GINI_STATES:
        g = frame(client, s, "B19083", geo="state")
        pub, moe = float(g.B19083_001E[0]), float(g.B19083_001M[0])
        h = pums.fetch_pums(s, YEAR, record="housing", columns=["HINCP", "ADJINC", "TYPEHUGQ", "NP"])
        h = h[(pd.to_numeric(h.TYPEHUGQ) == 1) & (pd.to_numeric(h.NP) > 0) & h.HINCP.notna()].copy()
        h["inc"] = pd.to_numeric(h.HINCP)*pd.to_numeric(h.ADJINC)/1e6
        neg = float((h.inc < 0).mean())
        prim = h.assign(inc=h.inc.clip(lower=0))
        sec = h[h.inc >= 0]
        r = {}
        for name, df in (("primary_negatives_to_zero", prim), ("secondary_negatives_dropped", sec)):
            t = pums_inequality(df, "inc", weight="housing")["table"].set_index("measure").loc["gini"]
            r[name] = dict(estimate=float(t.estimate), lower=float(t.lower), upper=float(t.upper),
                           validated=bool(t.validated))
        p = r["primary_negatives_to_zero"]
        rows.append(dict(state=s, published=pub, published_moe=moe, households=int(len(h)), negative_share=neg,
                         **{f"{k}_{m}": v for k, d in r.items() for m, v in d.items()},
                         difference=p["estimate"]-pub, contains=bool(p["lower"] <= pub <= p["upper"])))
    t = pd.DataFrame(rows)
    med = float(t.difference.abs().median()); contain = int(t.contains.sum())
    return dict(table=t.round(5).to_dict("records"), median_abs_difference=med, contained=contain,
                mean_difference=float(t.difference.mean()),
                replicated=bool(med <= B_MEDIAN_MAX and contain >= B_CONTAIN_MIN))


def validate_pins(commit):
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit("differs from criterion commit: "+rel)


def write(result):
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1, default=float)+"\n")
    L = ["# Round 66 numeric replications A and B", "", f"Criterion commit: `{result['criterion_commit']}`.", ""]
    if "A" in result:
        a = result["A"]
        L += ["## A. CHR 2025 county Black/White dissimilarity", "",
              f"- Counties compared: {a['counties_compared']} (ours only: {len(a['only_ours'])}; CHR only: "
              f"{len(a['only_published'])}).",
              f"- Median |difference|: {a['median_abs_difference']:.4f} points; within 1 point: "
              f"{a['share_within_1']:.4f}; largest: {a['max_abs_difference']:.4f}.",
              f"- Counties more than 2 points apart: {len(a['large'])}.",
              f"- **Outcome: {'replicated' if a['replicated'] else 'not replicated'}** (pre-set: median <= "
              f"{A_MEDIAN_MAX}, share within {A_WITHIN} >= {A_SHARE}).",
              f"- Interval part (descriptive; B03002 non-Hispanic groups, VRE replicates): "
              f"{a['interval_part']['counties']} counties, {a['interval_part']['validated']} validated.", ""]
    if "B" in result:
        b = result["B"]
        L += ["## B. Census state Gini (B19083) from PUMS", "",
              "| State | Published (MOE) | PUMS Gini (90% CI) | Difference | Contains |", "| :--- | :--- | :--- | ---: | :--- |"]
        for r in b["table"]:
            L.append(f"| {r['state']} | {r['published']:.4f} ({r['published_moe']:.4f}) | "
                     f"{r['primary_negatives_to_zero_estimate']:.4f} ({r['primary_negatives_to_zero_lower']:.4f}-"
                     f"{r['primary_negatives_to_zero_upper']:.4f}) | {r['difference']:+.4f} | {r['contains']} |")
        L += ["", f"Median |difference| {b['median_abs_difference']:.4f}; contained {b['contained']} of 12; mean "
              f"difference {b['mean_difference']:+.4f}. **Outcome: {'replicated' if b['replicated'] else 'not replicated'}** "
              f"(pre-set: median <= {B_MEDIAN_MAX}, contained >= {B_CONTAIN_MIN}).", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit", required=True)
    ap.add_argument("--part", default="AB")
    a = ap.parse_args()
    validate_pins(a.criterion_commit)
    c = _client()
    result = dict(criterion_commit=a.criterion_commit, chr_commit=CHR_COMMIT, chr_sha256=CHR_SHA256)
    if "A" in a.part:
        result["A"] = part_a(c)
    if "B" in a.part:
        result["B"] = part_b(c)
    write(result)
    print(json.dumps({k: v.get("replicated") for k, v in result.items() if isinstance(v, dict)}))


if __name__ == "__main__":
    main()

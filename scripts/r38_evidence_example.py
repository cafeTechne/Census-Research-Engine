# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 38 exploratory example: pooling Round 29's MI/NY and OH/PA poverty coefficients.

Reads the registered results in the v0.26.0 attachment (coefficients only). Exploratory.
Usage: scripts/r38_evidence_example.py R29_ARCHIVE OUT_DIR
"""
import json
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import evidence
from census.results import _jsonable


def main(archive, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    coef = {}
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(archive) as tar:
        for case in ("mi_ny", "oh_pa"):
            for h in ("h1", "h2", "h3"):
                name = f"r29/{case}/confirmatory/bundle/results/{h}.json"
                tar.extract(tar.getmember(name), tmp, filter="data")
                rows = json.loads((Path(tmp)/name).read_text())["coefficients"]
                r = next(r for r in rows if r["term"] == "poverty")
                coef[(case, h)] = (r["estimate"], r["se_total"] if r.get("se_total") is not None else r["se_model"])
    res = {}
    for h, label in (("h1", "premature"), ("h2", "drug overdose"), ("h3", "heart disease")):
        (a, sa), (b, sb) = coef[("mi_ny", h)], coef[("oh_pa", h)]
        res[h] = dict(outcome=label, mi_ny=(a, sa), oh_pa=(b, sb),
                      hksj=evidence.combine_estimates([a, b], [sa, sb], labels=["MI/NY", "OH/PA"]),
                      fixed=evidence.combine_estimates([a, b], [sa, sb], method="fixed"),
                      equivalence=evidence.equivalence(a, sa, b, sb, margin=.01),
                      power=evidence.power(sa))
        p, f = res[h]["hksj"]["pooled"], res[h]["fixed"]["pooled"]
        print(label, f"MI/NY {a:.4f}±{sa:.4f} OH/PA {b:.4f}±{sb:.4f} | HKSJ {p['estimate']:.4f} [{p['lower']:.4f},{p['upper']:.4f}] "
              f"| fixed {f['estimate']:.4f} [{f['lower']:.4f},{f['upper']:.4f}] | I2 {res[h]['hksj']['heterogeneity']['I2']:.2f} "
              f"| TOST p {res[h]['equivalence']['p']:.3f} eq={res[h]['equivalence']['equivalent']} | MDE {res[h]['power']['minimum_detectable_effect']:.4f}")
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])

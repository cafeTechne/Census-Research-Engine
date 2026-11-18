# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 29 registration and runs. WONDER inputs are local, pinned manual exports.

Register BOTH manifests, commit them, then run with --registration COMMIT.
The run command refuses changed registrations and existing output directories.
Only Census ACS/VRE and Census boundary downloads use the network.
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from census.manifest import create_manifest, manifest_hash, run_manifest
from census.wonder_reference import acs_age_sex_bands

CASES = {"mi_ny": ("26", "36"), "oh_pa": ("39", "42")}
CAUSES = {"H1": "premature_all_causes", "H2": "drug_overdose", "H3": "heart_disease"}


def manifest_path(case):
    suffix = "mortality_smr" if case == "mi_ny" else "replication"
    return ROOT / "examples/manifests" / f"r29_{case}_{suffix}.json"


def pinned(kind, cause):
    path = Path("external_data/wonder/ucd/2018-2022") / kind / (cause + ".tsv")
    return {"file": str(path), "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def build_manifest(states):
    template = acs_age_sex_bands(2022)
    m = dict(schema_version=1, title="County mortality and poverty, ACS/WONDER 2018–2022",
             created="2026-11-18", authors=["human:cafeTechne"], releases=[2022],
             geography={"level": "county", "states": list(states)}, confidence_level=.90,
             missing="complete_case", correction={"method": "holm", "family": "all"},
             replicates={"source": "census_vre"}, data_source={"synthetic": False},
             variables=template["variables"] + [{"name": "pov_total", "ref": "2022:B17001_001"},
                                              {"name": "pov_below", "ref": "2022:B17001_002"}],
             derivations=template["derivations"] + [
                 {"name": "poverty", "op": "proportion", "num": "pov_below", "den": "pov_total", "as_percent": True},
                 {"name": "acs_population", "op": "sum", "num": template["population_bands"]}],
             exclusions=[{"rule": "cv_screen", "action": "flag", "variables": ["poverty"], "threshold": 30}],
             external=[], analyses=[], hypotheses=[])
    for hyp, cause in CAUSES.items():
        name = hyp.lower()
        reference = pinned("national_age_sex", "all_causes" if hyp == "H1" else cause)
        bands = template["population_bands"]
        if hyp == "H1":
            reference["ages_under"] = 75
            bands = [b for b in bands if not b.endswith(("75_84", "85_plus"))]
        m["external"].append(dict(source="wonder", name=name, measure="deaths", **pinned("county", cause)))
        m["derivations"].append(dict(name="E_"+name, op="expected_count", population_bands=bands,
                                     period_years=5, reference_export=reference))
        m["analyses"].append(dict(id=name, method="fit_replicate", formula=f"{name}_numerator ~ poverty + C(GEOID.str[:2])",
                                  args={"model": "poisson", "scale": "robust", "target": "conservative", "exposure": "E_"+name}))
        m["analyses"].append(dict(id="smr_"+name, method="smr", observed=name+"_numerator", population_bands=bands,
                                  reference_export=reference, period_years=5,
                                  reference_source="Owner manual WONDER UCD national age × sex export, 2018–2022; annual person-year rates"))
        m["hypotheses"].append(dict(id=hyp, analysis=name, statistic="coefficient", term="poverty", direction="greater",
                                    statement=f"{cause}: mortality relative to the age/sex standard increases with poverty percentage, conditional on state."))
    m["protocol"] = {
        "review": "author self-review, not independent; owner checkpoint passed 2026-11-18",
        "models": "Poisson log link; HC3 plus ACS covariate replicate variance; expected-death offsets held fixed",
        "replication": "same coefficient sign and Holm p < 0.10 in OH/PA; Holm family H1–H3 separately in each geography",
        "h2_sensitivity": {"assign_all_suppressed": [1, 9], "outputs": "coefficients only; never county imputed values",
                           "holm": "replace H2 raw p only; retain registered H1 and H3 raw p",
                           "robust": "same support/non-support conclusion in complete-case and both refits; these are not strict bounds"},
        "descriptive": "posterior EB SMR maps with suppressed counties masked; exploratory population-weighted SII/log RII across poverty ridits",
        "limitations": "independent-area inference; spatial dependence unresolved; ecological association, no causal interpretation; no GLM attenuation correction",
        "outputs": "study states only; no reference death-count vectors, raw exports, complementary totals or per-county suppressed-derived values"}
    return m


def register():
    built = {case: build_manifest(states) for case, states in CASES.items()}
    left, right = (copy.deepcopy(built[c]) for c in CASES)
    left.pop("geography"); right.pop("geography")
    assert left == right
    if any(manifest_path(c).exists() for c in CASES):
        raise ValueError("Refusing to overwrite a registration")
    # Validate both before writing either; no outcomes or associations are read.
    for case, m in built.items():
        result = create_manifest(m, resolve=False)
        if not result["valid"]:
            raise ValueError(result["errors"])
    for case, m in built.items():
        result = create_manifest(m, path=manifest_path(case), resolve=False)
        print(case, result["hash"])


def check_registration(commit):
    for case in CASES:
        path = manifest_path(case)
        original = subprocess.check_output(["git", "show", f"{commit}:{path.relative_to(ROOT)}"], cwd=ROOT)
        if original != path.read_bytes():
            raise ValueError("Registered manifest differs from committed bytes")
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True)


def write_json(path, value):
    def default(v):
        if isinstance(v, (np.bool_, np.integer, np.floating)): return v.item()
        raise TypeError(type(v).__name__)
    path.write_text(json.dumps(value, indent=2, default=default, allow_nan=False)+"\n")


def sensitivity(frame, replicates, hypotheses):
    from census.models import fit_replicate
    from census.multitest import adjust_pvalues
    from scipy.stats import norm
    hidden = frame.h2_flag.eq(2)
    baseline = hypotheses.set_index("id")
    rows = [{"assignment": "complete-case", "estimate": float(baseline.loc["H2", "estimate"]),
             "holm_p": float(baseline.loc["H2", "p_adjusted"]), "supported": bool(baseline.loc["H2", "significant"])}]
    if hidden.any():
        for value in (1, 9):
            working = frame.copy()
            working.loc[hidden, "h2_numerator"] = value
            result = fit_replicate("h2_numerator ~ poverty + C(GEOID.str[:2])", working, replicates,
                                   model="poisson", exposure="E_h2", scale="robust", target="conservative",
                                   replicate_policy="strict", fixed_variables=("h2_numerator",))
            coef = result.coefficients.set_index("term").loc["poverty"]
            p = float(norm.sf(coef.estimate/coef.se_total))
            adjusted = adjust_pvalues([baseline.loc["H1", "p_value"], p, baseline.loc["H3", "p_value"]], "holm")[1]
            rows.append(dict(assignment=f"all suppressed set to {value} (internal only)", estimate=float(coef.estimate),
                             se_total=float(coef.se_total), ci_lower=float(coef.ci_lower), ci_upper=float(coef.ci_upper),
                             p_value=p, holm_p=float(adjusted), supported=bool(adjusted < .10)))
    return dict(status="pre-registered sensitivity, not strict bounds", suppressed_counties=int(hidden.sum()),
                rows=rows, robust=len({r["supported"] for r in rows}) == 1)


def run(case, commit):
    check_registration(commit)
    folder = ROOT / "studies_output/r29" / case
    if folder.exists(): raise ValueError("Refusing to overwrite existing study outputs")
    from dotenv import dotenv_values
    from census.api import CensusAPIClient
    from census.wonder_outputs import restore_snapshot, audit_outputs
    # Read the owner key privately; exceptions and logs never include it.
    import os
    env = dotenv_values(Path("/home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/.env"))
    key = os.environ.get("CENSUS_API_KEY") or env.get("CENSUS_API_KEY")
    client = CensusAPIClient(api_key=key)
    out = run_manifest(manifest_path(case), folder / "confirmatory", client=client)
    if not out["success"]:
        write_json(folder / "failure.json", {"errors": out.get("errors"), "deviations": out.get("deviations")})
        raise RuntimeError("Registered run incomplete; inspect failure.json (no automatic fallback)")
    run_info = json.loads((folder / "confirmatory/bundle/results/run.json").read_text())
    policy = run_info["wonder_output_policy"]
    reps = pd.read_parquet(folder / "confirmatory/analysed/replicates.parquet")
    frame = restore_snapshot(out["frame"], ["h1", "h2", "h3"])
    sens = sensitivity(frame, reps, out["hypotheses"])
    write_json(folder / "h2_sensitivity.json", sens)
    write_json(folder / "registration.json", {"commit": commit, "manifest_hash": out["manifest_hash"]})
    audit = audit_outputs(folder, policy)
    write_json(folder / "privacy_audit.json", audit)
    if not audit["passed"]: raise ValueError("WONDER output disclosure audit failed")
    print(case, out["analysis_status"], "privacy audit passed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("register", "run"))
    p.add_argument("--case", choices=tuple(CASES))
    p.add_argument("--registration")
    args = p.parse_args()
    if args.action == "register": register()
    else:
        if not args.case or not args.registration: p.error("run requires --case and --registration")
        run(args.case, args.registration)


if __name__ == "__main__": main()

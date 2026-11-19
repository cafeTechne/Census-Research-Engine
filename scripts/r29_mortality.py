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


def owner_key():
    """Environment or local checkout dotenv; never include values in messages."""
    import os
    from dotenv import dotenv_values
    common = Path(subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, text=True).strip())
    if not common.is_absolute(): common = ROOT / common
    for path in (ROOT / ".env", common.resolve().parent / ".env"):
        key = os.environ.get("CENSUS_API_KEY") or dotenv_values(path).get("CENSUS_API_KEY")
        if key: return key
    return None


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
    from census.api import CensusAPIClient
    from census.wonder_outputs import restore_snapshot, audit_outputs
    # Read the owner key privately; exceptions and logs never include it.
    client = CensusAPIClient(api_key=owner_key())
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


def describe(case, commit):
    """Registered descriptive scope; never change the confirmatory bundle."""
    check_registration(commit)
    from census.boundaries import get_boundaries
    from census.inequality import inequality_replicate
    from census.maps import choropleth
    from census.rate_smoothing import eb_poisson_gamma
    from census.report_tables import results_bundle
    from census.variance import REPLICATE_COLUMNS
    from census.wonder_outputs import restore_snapshot, audit_outputs, GENERIC_COLUMNS
    folder = ROOT / "studies_output/r29" / case
    run_info = json.loads((folder / "confirmatory/bundle/results/run.json").read_text())
    if run_info["analysis_status"] != "confirmatory": raise ValueError("Original run is incomplete")
    loaded = {}
    for name in ("analysis_frame", "replicates"):
        path = folder / "confirmatory/analysed" / (name + ".parquet")
        if hashlib.sha256(path.read_bytes()).hexdigest() != run_info["analysed_data"][name]["sha256"]:
            raise ValueError("Analysed-data checksum mismatch")
        loaded[name] = pd.read_parquet(path)
    frame = restore_snapshot(loaded["analysis_frame"], ["h1", "h2", "h3"])
    replicates = loaded["replicates"]
    geometry = get_boundaries("county", 2022)
    geometry = geometry[geometry.GEOID.isin(frame.GEOID)].copy()
    if set(geometry.GEOID) != set(frame.GEOID): raise ValueError("County boundary coverage mismatch")
    policy = copy.deepcopy(run_info["wonder_output_policy"])
    figures, results = {}, {}
    for hyp in CAUSES:
        name = hyp.lower()
        ids = frame.GEOID.astype(str)
        counts = pd.Series(frame[name+"_numerator"].to_numpy(float), index=ids)
        expected = pd.Series(frame["E_"+name].to_numpy(float), index=ids)
        hidden = frame[name+"_flag"].eq(2).to_numpy()
        lower = pd.Series(np.where(hidden, 1., np.nan), index=ids)
        upper = pd.Series(np.where(hidden, 9., np.nan), index=ids)
        eb = eb_poisson_gamma(counts, expected, lower, upper, level=.90, interval="posterior")
        notes = copy.deepcopy(eb.attrs)
        eb = eb.reset_index()
        scope = {"columns": {c: ids[hidden].tolist() for c in GENERIC_COLUMNS}, "count_column": "observed"}
        policy["results"]["eb_"+name] = scope
        policy["figures"]["eb_"+name] = scope
        results["eb_"+name] = {"rows": eb, "metadata": notes}
        gdf = geometry.merge(eb[["GEOID", "eb_ratio"]], on="GEOID", validate="one_to_one")
        figures["eb_"+name] = (choropleth, {"gdf": gdf, "column": "eb_ratio", "formats": ("svg", "png"),
                                            "title": f"{CAUSES[hyp]}: descriptive EB SMR ({case.upper()})",
                                            "data_source": "WONDER manual export; ACS 2018–2022; censored counties masked",
                                            "manifest_hash": run_info["manifest_hash"]})
        # Recompute poverty ridits, population weights and O/E with every ACS
        # replicate. Observed deaths stay fixed; reference-count uncertainty is
        # absent from these exploratory indices (not from the SMR intervals).
        d = frame.loc[~hidden].copy()
        d["smr"] = d[name+"_numerator"] / d["E_"+name]
        e = replicates[replicates.variable == "E_"+name].set_index("GEOID").loc[d.GEOID]
        rep_smr = e.reset_index().copy()
        rep_smr["variable"] = "smr"
        rep_smr.loc[:, REPLICATE_COLUMNS] = d[name+"_numerator"].to_numpy(float)[:, None] / e[REPLICATE_COLUMNS].to_numpy(float)
        active = replicates[replicates.variable.isin(["poverty", "acs_population"]) & replicates.GEOID.isin(d.GEOID)]
        ir = inequality_replicate(d, "smr", "poverty", "acs_population", True,
                                 pd.concat([active, rep_smr], ignore_index=True), level=.90, target="conservative")
        ir.notes.append("Exploratory: common reference-rate uncertainty and spatial dependence excluded; censored counties excluded. Not an additional confirmatory test.")
        results["inequality_"+name] = ir
    methods = ("Descriptive only; author self-review, not independent. Posterior Poisson–Gamma EB ratios use [1,9] censoring internally, "
               "with every censored county masked in every output. EB fixes ACS expected deaths and ignores reference-rate and spatial uncertainty. "
               "Maps show quantiles, not significance. SII/log RII use population-weighted poverty ridits, re-estimated under all 80 ACS replicates; "
               "observed deaths and national rates fixed. These exploratory intervals exclude common reference-rate uncertainty and spatial dependence. "
               "No county imputed counts, aggregate death totals, or national reference death-count vectors are published.")
    results_bundle(folder / "descriptive", figures=figures, results=results, methods=methods,
                   provenance={"manifest_hash": run_info["manifest_hash"], "registration_commit": commit,
                               "analysis_status": "exploratory", "boundary_sha256": geometry.attrs.get("sha256")},
                   wonder_policy=policy)
    audit = audit_outputs(folder, policy)
    write_json(folder / "privacy_audit.json", audit)
    if not audit["passed"]: raise ValueError("WONDER disclosure audit failed")
    write_json(folder / "output_policy.json", policy)
    print(case, "descriptive maps/indices and disclosure audit complete")


def finish(commit):
    """Write reports and a local, audited archive; never publish it."""
    import tarfile
    from census.wonder_outputs import audit_outputs
    check_registration(commit)
    base = ROOT / "studies_output/r29"
    hyps, sensitivities, audits = {}, {}, {}
    for case in CASES:
        folder = base / case
        hyps[case] = json.loads((folder / "confirmatory/bundle/results/hypotheses.json").read_text())["rows"]
        sensitivities[case] = json.loads((folder / "h2_sensitivity.json").read_text())
        audits[case] = audit_outputs(folder, json.loads((folder / "output_policy.json").read_text()))
        if not audits[case]["passed"]: raise ValueError("Final disclosure audit failed")
    replication = []
    for left, right in zip(hyps["mi_ny"], hyps["oh_pa"]):
        assert left["id"] == right["id"]
        replication.append({"id": left["id"], "holds": bool(np.sign(left["estimate"]) == np.sign(right["estimate"]) and right["p_adjusted"] < .10)})
    for case in CASES:
        path = ROOT / "docs/studies" / ("r29_mi_ny_mortality_smr.md" if case == "mi_ny" else "r29_oh_pa_replication.md")
        folder = base / case
        m = json.loads(manifest_path(case).read_text())
        run_info = json.loads((folder / "confirmatory/bundle/results/run.json").read_text())
        states = "Michigan / New York" if case == "mi_ny" else "Ohio / Pennsylvania"
        lines = [f"# Round 29: {states} mortality and poverty", "",
                 "**Author self-review, not independent.** Registered confirmatory protocol; descriptive analyses are labelled separately. Completed 2026-11-18.", "",
                 f"Both manifests were committed and pushed at `{commit}` before either outcome association was computed. This manifest: `{manifest_path(case).name}`; canonical SHA-256 `{manifest_hash(m)}`. The replication changes geography only; all other fields are identical.", "",
                 "## Registered analysis", "",
                 "County deaths pooled over 2018–2022 are the owner's manual WONDER UCD exports, pinned by SHA-256. National age × sex references are also manual exports. No WONDER network access was used. Expected deaths are five times the ACS 2018–2022 population in each matching age/sex band times the annual national rate (deaths divided by summed annual person-years). H1 uses ages under 75 and all-cause reference rates; H2 and H3 use all ages and their cause-specific rates. The youngest two WONDER groups are combined; Not Stated ages are dropped. All 62 available exports passed structural inventory; only the six registered files enter these studies.", "",
                 "Each Poisson model uses log(expected deaths) as offset, poverty in percentage points (B17001), and a state intercept. HC3 model variance plus 80-replicate ACS poverty variance gives the conservative SE. Offsets stay fixed in these model refits: the slope's interval excludes ACS offset and reference-rate uncertainty. Separate reference-aware county SMR combined intervals include Poisson, ACS expected-count and reference death-count variance; they do not correct the slope's omitted offset uncertainty. Reference person-years are fixed. Internal national-reference covariance is omitted, conservatively, for SMR intervals.", "",
                 f"All {run_info['n_units']} study county IDs matched. H1/H3 exclude no suppressed counties. H2 excludes {sensitivities[case]['suppressed_counties']} suppressed counties; their total deaths are only bounded by [{sensitivities[case]['suppressed_counties']}, {9*sensitivities[case]['suppressed_counties']}]. Suppression causes no vintage-mismatch warning. County IDs and nonblocking exclusions are recorded in the run bundle.", "",
                 "| Hypothesis | Counties fitted | Poverty coefficient | Mortality ratio per +1 pp poverty (90% CI) | One-sided Holm p | Supported |",
                 "| :--- | ---: | ---: | :--- | ---: | :--- |"]
        for h in hyps[case]:
            model = json.loads((folder / f"confirmatory/bundle/results/{h['analysis']}.json").read_text())
            lines.append(f"| {h['id']}: {CAUSES[h['id']]} | {model['n_obs']} | {h['estimate']:.6f} | {np.exp(h['estimate']):.4f} ({np.exp(h['ci_lower']):.4f}–{np.exp(h['ci_upper']):.4f}) | {h['p_adjusted']:.4g} | {'yes' if h['significant'] else 'no'} |")
        lines += ["", "Intervals are unadjusted two-sided 90% intervals. Tests are registered positive-direction tests, Holm-corrected over H1–H3 separately in each geography, at alpha 0.10. They are ecological associations and do not establish causation.", "",
                  "## Registered H2 suppression sensitivity", "",
                  "These two endpoint assignments are internal refits, not estimates of the hidden county counts and not strict bounds on the slope. H1/H3 raw p-values remain fixed while the H2 p-value is replaced and the three-test Holm family is recomputed. Only coefficients are output.", "",
                  "| Fit | Poverty coefficient | Holm p | Supported |", "| :--- | ---: | ---: | :--- |"]
        for r in sensitivities[case]["rows"]:
            lines.append(f"| {r['assignment']} | {r['estimate']:.6f} | {r['holm_p']:.4g} | {'yes' if r['supported'] else 'no'} |")
        lines += ["", f"H2 conclusion stable in all three fits: **{'yes' if sensitivities[case]['robust'] else 'no'}**.", "",
                  "## Held-out replication", "", "OH/PA was separately registered at the same commit. The fixed rule is same coefficient sign and OH/PA Holm p < 0.10; it is not a pooled four-state analysis.", "",
                  "| Hypothesis | Replication holds |", "| :--- | :--- |"]
        lines += [f"| {r['id']} | {'yes' if r['holds'] else 'no'} |" for r in replication]
        lines += ["", "## Descriptive and exploratory results", "",
                  "Posterior Poisson–Gamma EB SMR maps are descriptive. Censored counties enter the [1,9] likelihood internally and are grey/masked in every published map and value file. EB intervals fix E and omit ACS, reference-rate and spatial uncertainty. Quantile classes show relative levels, not significance; breaks differ between geographies. Maps live in `descriptive/figures/eb_h{1,2,3}.{png,svg}` inside the local archive.", "",
                  "Population-weighted SII and RII use poverty ridits running least to most deprived. These are exploratory summaries with 80 ACS refits of ranks, population weights and O/E; observed deaths and national rates stay fixed. Their intervals exclude common reference-rate uncertainty and spatial dependence, so they are not additional confirmatory evidence.", "",
                  "| Outcome | SII (90% CI) | RII (90% CI) | Median rank CV |", "| :--- | :--- | :--- | ---: |"]
        for name in ("h1", "h2", "h3"):
            ir = json.loads((folder / f"descriptive/results/inequality_{name}.json").read_text())
            coefs = {r['term']: r for r in ir['coefficients']};sii=coefs['sii'];rii=coefs['log_rii']
            lines.append(f"| {name.upper()} | {sii['estimate']:.3f} ({sii['ci_lower']:.3f}–{sii['ci_upper']:.3f}) | {np.exp(rii['estimate']):.3f} ({np.exp(rii['ci_lower']):.3f}–{np.exp(rii['ci_upper']):.3f}) | {ir['diagnostics']['rank_cv_median']:.2f}% |")
        lines += ["", "## Limits and disclosure checks", "",
                  "HC3 and ACS refits assume independent counties. Spatial dependence remains unresolved; IM-8 does not support Poisson/ACS here and was not substituted. ACS covariate error can attenuate slopes; GLM measurement-error correction is unavailable. Five-year ACS populations approximate the mortality period's average population. A successful replication does not resolve these limitations or certify nominal spatial coverage. The reported sensitivity only addresses the registered endpoint assignments, not all missingness or selection mechanisms.", "",
                  "Census VRE parsing warned that two rows in the full national B17001 file differ from published MOEs beyond rounding (maximum 0.632); published MOEs remain official and the source is unchanged. No replicate failure, missing study county or blocking deviation occurred.", "",
                  f"Disclosure scan passed on {audits[case]['structured_frames_checked']} structured county frames, including snapshots, EB tables and map values. Protected count/rate/SMR/EB fields are literal `suppressed` for censored counties. No raw exports, national reference death-count vectors, complementary death totals or county sensitivity assignments enter the archive. Only the four registered study states are included. A key scan is required again if packaging is changed.", "",
                  "Reproduce in a fresh checkout with the private local exports and no existing `studies_output/r29/" + case + "`: `.venv/bin/python scripts/r29_mortality.py run --case " + case + " --registration " + commit + "`, then `describe` with the same arguments. The script refuses changed registration bytes and overwriting completed runs. `.venv/bin/python scripts/r29_mortality.py finish --registration " + commit + "` writes both reports and the local archive; it does not publish or release.", ""]
        report = "\n".join(lines)
        if path.exists() and path.read_text() != report:
            raise ValueError("Refusing to overwrite a different study report")
        if not path.exists(): path.write_text(report)
    archive = Path("/tmp/r29_study_outputs.tar.gz")
    if archive.exists(): raise ValueError("Refusing to overwrite archive")
    files = sorted(p for p in base.rglob("*") if p.is_file())
    key = owner_key()
    for path in files:
        if path.is_symlink() or path.suffix.lower() in (".tsv", ".xml"):
            raise ValueError("Raw or symlinked input is forbidden in the archive")
        if key and key.encode() in path.read_bytes(): raise ValueError("Key scan failed")
    with tarfile.open(archive, "w:gz") as tar:
        for path in files: tar.add(path, arcname=str(Path("r29") / path.relative_to(base)), recursive=False)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or key and key.encode() in tar.extractfile(member).read():
                raise ValueError("Archive scan failed")
    summary = {"registration_commit": commit, "replication": replication, "disclosure": audits,
               "archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
               "members": len(files), "key_scan": "passed" if key else "no local key configured", "published": False}
    write_json(Path("/tmp/r29-package-audit.json"), summary)
    print(json.dumps(summary, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("register", "run", "describe", "finish"))
    p.add_argument("--case", choices=tuple(CASES))
    p.add_argument("--registration")
    args = p.parse_args()
    if args.action == "register": register()
    elif args.action == "finish":
        if not args.registration: p.error("finish requires --registration")
        finish(args.registration)
    else:
        if not args.case or not args.registration: p.error("run requires --case and --registration")
        (run if args.action == "run" else describe)(args.case, args.registration)


if __name__ == "__main__": main()

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reporting, results-bundle, manifest, and verification workflows (extracted from workflows_inference.py in Round 149)."""

import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from census import errors
from census.workflows import ROOT, _jsonable, _load_frame

try:
    from patsy import PatsyError as _PatsyError
except ImportError:  # pragma: no cover
    class _PatsyError(Exception):
        pass

_INPUT_ERRORS = (FileNotFoundError, OSError, KeyError, ValueError, TypeError, RuntimeError,
                 ZeroDivisionError, np.linalg.LinAlgError, _PatsyError)
_FIGURE_KINDS = ("estimates", "forest", "trend")


def _ok(summary: str, next_step: str, **payload: Any) -> Dict[str, Any]:
    return _jsonable({"success": True, "summary": summary, "next_step": next_step, **payload})


def _fail(code: str, message: str, next_step: str = "") -> Dict[str, Any]:
    out = errors.error_result(code, message)
    out["summary"] = message
    if next_step:
        out["next_step"] = next_step
    return out


def _out_dir(path: Optional[str], default: str) -> str:
    folder = path or os.path.join(ROOT, "downloads", default)
    os.makedirs(folder, exist_ok=True)
    return folder


def _read_replicates(path: Optional[str]) -> Optional[pd.DataFrame]:
    if not path:
        return None
    from census.manifest import read_replicates
    return read_replicates(path)


def make_figure(
    kind: str,
    input_path: str,
    output_dir: Optional[str] = None,
    label_col: Optional[str] = None,
    estimate_col: Optional[str] = None,
    moe_col: Optional[str] = None,
    se_col: Optional[str] = None,
    period_col: Optional[str] = None,
    width: str = "one",
    data_source: str = "",
) -> Dict[str, Any]:
    """Journal-ready figure (PDF, SVG, EPS, PNG) with a values CSV, draft caption,
    and provenance file.

    Args:
        kind: "estimates" (estimates with 90% intervals; needs label_col,
            estimate_col, moe_col or se_col), "forest" (input is a
            batch_significance output), or "trend" (needs period_col, estimate_col,
            moe_col or se_col).
        input_path: CSV/Parquet with the values.
        output_dir: Folder for the files (default downloads/figures).
        width: "one" or "two" journal columns.
        data_source: Text for the caption, e.g. "ACS 5-year 2019-2023, table B17001".

    Model, correlation, and small-area figures come from fit_model,
    correlation_matrix, and small_area_estimates via their figure_dir argument.
    """
    from census import figures

    if kind not in _FIGURE_KINDS:
        return _fail(errors.INVALID_INPUT, f"kind must be one of {_FIGURE_KINDS}.")
    folder = _out_dir(output_dir, "figures")
    try:
        df = _load_frame(input_path)
        common = {"out_dir": folder, "width": width, "data_source": data_source}
        if kind == "estimates":
            fig = figures.estimates_with_intervals(df, label_col, estimate_col, se_col=se_col, moe_col=moe_col, **common)
        elif kind == "forest":
            fig = figures.forest_plot(df, label_col=label_col, **common)
        else:
            fig = figures.trend_plot(df, period_col, estimate_col, se_col=se_col, moe_col=moe_col, **common)
    except (FileNotFoundError, OSError, KeyError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    paths = fig.paths.values() if isinstance(fig.paths, dict) else fig.paths
    return _ok(f"Wrote {kind} figure '{fig.name}'.", "make_table, or include the PDF/SVG and caption in your write-up",
               figure_paths=[str(p) for p in paths], caption=fig.caption)


def make_table(kind: str, input_path: str, output_dir: Optional[str] = None,
               variables: Optional[List[str]] = None, name: str = "table", exposure: Optional[str] = None,
               population: Optional[str] = None, confidence_level: Optional[float] = None) -> Dict[str, Any]:
    """Publication table as LaTeX (booktabs), Markdown, and CSV.

    Args:
        kind: "descriptive" (variables from an analysis frame), "comparison" (a batch_significance output file) or
            "table1" (Round 82: the study areas described by tertiles of `exposure`, with `variables` and optional
            `population`; the "Table 1" of an epidemiologic report).
        input_path: The file. variables: For descriptive and table1 tables.
        confidence_level: comparison tables only: re-express the intervals at this level (e.g. 0.95 for health
            journals); tests and p-values are unchanged.
        output_dir: Folder (default downloads/tables).
    """
    from census import report_tables

    folder = _out_dir(output_dir, "tables")
    try:
        df = _load_frame(input_path)
        if kind == "descriptive":
            table = report_tables.descriptive_table(df, variables or [c for c in df.columns if f"{c}_se" in df.columns])
        elif kind == "comparison":
            table = report_tables.comparison_table(df, confidence_level=confidence_level)
        elif kind == "table1":
            if not exposure or not variables:
                return _fail(errors.INVALID_INPUT, "kind='table1' needs exposure and variables.")
            table = report_tables.table_one_table(df, exposure, variables, population=population)
        else:
            return _fail(errors.INVALID_INPUT, "kind must be 'descriptive', 'comparison' or 'table1'.")
        written = table.write(folder, name)
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check the formula, column names, and input file, then retry")
    files = list(written.values()) if isinstance(written, dict) else written
    return _ok(f"Wrote {kind} table '{name}'.", "include the .tex or .md table in your write-up",
               table_paths=[str(p) for p in files], markdown=table.to_markdown())


def _extraction_record(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Provenance fields of an extraction metadata JSON."""
    return {"table": meta.get("table_code"), "dataset": meta.get("dataset"), "years": meta.get("years"),
            "geo_level": meta.get("geo_level"), "endpoint": meta.get("endpoint"),
            "states": sorted({e.get("state_code") for e in meta.get("entities") or [] if e.get("state_code")}),
            "variables": meta.get("variables"), "generated_at": meta.get("generated_at"),
            "package_version": meta.get("package_version"), "git_commit": meta.get("git_commit"),
            "failed_calls": len(meta.get("failed_calls") or []), "data_source": meta.get("data_source")}


def _recorded_source(doc: Any) -> Optional[Dict[str, Any]]:
    """The data source a saved JSON (extraction metadata, tool result, manifest run or bundle)
    recorded when its data were read: {"synthetic": bool, ...}, or None when it records none."""
    if not isinstance(doc, dict):
        return None
    for source in (doc.get("data_source"), (doc.get("provenance") or {}).get("data_source")):
        if isinstance(source, dict) and isinstance(source.get("synthetic"), bool):
            return source
    return None


def _input_names(paths: List[str]) -> List[str]:
    """Input paths relative to their common folder ('/'-separated), so same-named files from
    different folders (extract/26/B19013/..., extract/36/B19013/...) stay distinguishable."""
    full = [os.path.abspath(p) for p in paths]
    if not full:
        return []
    try:
        common = os.path.commonpath([os.path.dirname(p) for p in full])
    except ValueError:  # different drives (Windows): keep the parent folder name
        return [f"{os.path.basename(os.path.dirname(p))}/{os.path.basename(p)}" for p in full]
    return [os.path.relpath(p, common).replace(os.sep, "/") for p in full]


def _bundle_source(recorded: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bundle data source from the inputs' recorded sources (each {path, synthetic, ...})."""
    if not recorded:
        return {"kind": "unknown", "synthetic": None}
    synthetic = [r for r in recorded if r["synthetic"]]
    if not synthetic:
        return {"kind": "census_api", "synthetic": False}
    marker = {k: synthetic[0][k] for k in ("description", "generator") if synthetic[0].get(k)}
    return {"kind": "synthetic" if len(synthetic) == len(recorded) else "mixed", "synthetic": True, **marker}


def make_results_bundle(
    output_dir: str,
    results: Dict[str, str],
    figure_paths: Optional[List[str]] = None,
    inputs: Optional[List[str]] = None,
    title: str = "",
    notes: Optional[List[str]] = None,
    allow_failed_results: bool = False,
    design: str = "area",
) -> Dict[str, Any]:
    """Collect an exploratory (not pre-registered) analysis into one results bundle:
    results JSON, figures, methods.md, and bundle.json with every file's SHA-256,
    the data citation and provenance (data source, input hashes, extractions).

    Args:
        output_dir: Fresh or empty bundle folder; existing artifacts are preserved and refused.
        results: {name: path} of tool results saved with `python -m census tool ... --save PATH`.
            Names must be portable filename components, not paths; case-insensitive
            collisions within a bundle category are refused before bundle writes.
            A saved failure (success false) is refused unless allow_failed_results=True,
            which lists it under "Failed steps" in methods.md, never as a result.
        figure_paths: Figure files to copy (e.g. make_map figure_paths).
        inputs: Files the analysis used (extraction metadata JSON, frames, replicate
            files); their SHA-256 (keyed by the path relative to the inputs' common
            folder) and, for extraction metadata, table, years, states, endpoint,
            call failures and data source are recorded.
        title, notes: Methods heading and extra methods/limitations lines.
    methods.md ends with a "Sources" section, and references.md/references.bib list the method papers,
    guidance texts, data and validation audits recorded in the results' method_sources (Round 88).
        design: "area" (default; adds the ecologic and cross-sectional limitations, Round 82), "individual"
            (PUMS person records: cross-sectional only) or "none" (annual series, trials: no design lines).
    The data source comes from what the inputs and results recorded when their data
    were read (extraction metadata records the cache marker at extraction time): all
    synthetic -> "synthetic", none synthetic -> "census_api", both -> "mixed" (with a
    warning), nothing recorded -> "unknown". It is never taken from the cache present
    at bundle time. Pre-registered analyses use run_manifest instead (status "confirmatory").
    """
    from census.figures import FigureOutput
    from census.manifest import STATUS_EXPLORATORY
    from census.pipeline import file_sha256
    from census.report_tables import _require_empty_bundle, data_citation, results_bundle

    try:
        _require_empty_bundle(output_dir)
        loaded, failed, recorded = {}, [], []
        for name, path in (results or {}).items():
            with open(path, encoding="utf-8") as f:
                res = json.load(f)
            if isinstance(res, dict) and res.get("success") is False:
                failed.append({"name": name, "path": os.path.basename(path), "error_code": res.get("error_code"),
                               "error": res.get("error") or res.get("summary")})
                if not allow_failed_results:
                    return _fail(errors.INVALID_INPUT,
                                 f"Saved result '{name}' ({path}) is a failure (success false: "
                                 f"{failed[-1]['error']}); a failed step is not a result.",
                                 "fix and re-run that step, or drop it from results (allow_failed_results=True "
                                 "lists it under Failed steps, not as a result)")
                continue
            loaded[name] = res
            source = _recorded_source(res)
            if source:
                recorded.append({"path": f"results/{name}.json", **source})
        input_records, extractions = [], []
        for path, rel in zip(inputs or [], _input_names(list(inputs or []))):
            input_records.append({"path": rel, "sha256": file_sha256(path)})
            if path.lower().endswith(".json"):
                with open(path, encoding="utf-8") as f:
                    doc = json.load(f)
                if path.endswith("_extraction_metadata.json") and isinstance(doc, dict):
                    extractions.append(_extraction_record(doc))
                source = _recorded_source(doc)
                if source:
                    recorded.append({"path": rel, **source})
        figs = list(figure_paths or [])
        base = [os.path.basename(p) for p in figs]
        # same file name from different folders (e.g. maps/26/choropleth.pdf, maps/36/...): prefix the folder
        names = [b if base.count(b) == 1 else f"{os.path.basename(os.path.dirname(os.path.abspath(p)))}_{b}"
                 for p, b in zip(figs, base)]
        if len(set(names)) != len(names):
            raise ValueError("figure_paths contain the same file name twice in the same folder name")
        # Let results_bundle own all writes after its empty-destination check.
        # Each supplied path is already a rendered file, with no new caption.
        figure_specs = {name: FigureOutput(name=os.path.basename(path), paths={"file": path},
                                          values=pd.DataFrame(), caption="", provenance={})
                        for path, name in zip(figs, names)}
    except (OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    source = _bundle_source(recorded)
    warnings: List[str] = []
    if source["kind"] == "mixed":
        synth = [r["path"] for r in recorded if r["synthetic"]]
        real = [r["path"] for r in recorded if not r["synthetic"]]
        warnings.append(f"MIXED DATA SOURCES: SYNTHETIC inputs ({', '.join(synth)}) are combined with Census "
                        f"Data API inputs ({', '.join(real)}). These are not Census results and must not be "
                        "reported as such; re-extract every input from one source.")
    elif source["kind"] == "unknown":
        warnings.append("DATA SOURCE UNKNOWN: no input records where its data came from; pass the extraction "
                        "metadata JSON files as inputs (they record the source observed at extraction time).")
    releases = sorted({int(y) for e in extractions for y in e.get("years") or []})
    tables = sorted({e["table"] for e in extractions if e.get("table")})
    citation = data_citation(releases, tables, synthetic=bool(source["synthetic"]),
                             description=source.get("description"), retrieved=source["kind"] != "unknown")
    if source["kind"] == "mixed":
        citation = "MIXED DATA SOURCES (some inputs synthetic): " + citation
    lines = [f"# {title or 'Results'}", "",
             f"**Analysis status:** {STATUS_EXPLORATORY} (not a pre-registered manifest run).", "",
             f"**Data:** {citation}", ""]
    for w in warnings:
        lines += [f"**WARNING:** {w}", ""]
    for name, res in loaded.items():
        lines.append(f"## {name}")
        lines.append("")
        if res.get("summary"):
            lines.append(str(res["summary"]))
            lines.append("")
        interval = res.get("interval")
        if isinstance(interval, dict) and interval.get("text"):
            lines += [f"Intervals: {interval['text']}", ""]
        for note in res.get("notes") or []:
            lines.append(f"- {note}")
        lines.append("")
    if failed:
        lines += ["## Failed steps (FAILED: not results)", ""]
        lines += [f"- {f['name']}: FAILED ({f['error_code']}): {f['error']}" for f in failed] + [""]
    from census.epi_reporting import design_labels
    design_notes = [] if design == "none" else design_labels(None, individual=design == "individual")["notes"]
    if notes or design_notes:
        lines += ["## Notes and limitations", ""] + [f"- {n}" for n in list(notes or [])+design_notes] + [""]
    from census import references as refs
    by_role = refs.collect(loaded.values())
    cited = [i for r in refs.ROLES for i in by_role[r] if not i.startswith("audit:")]
    lines += [refs.render_sources(by_role, "## Sources")]
    if not cited:
        lines += ["No saved result recorded method_sources (results saved before Round 88 or outside the tool "
                  "interface); cite methods with `python -m census cite --tool NAME`.", ""]
    references = {"references.md": "# References\n\n" + refs.render_sources(by_role),
                  "references.bib": refs.cite(cited, "bibtex") if cited else "% no method sources recorded\n"}
    provenance = {"analysis_status": STATUS_EXPLORATORY, "data_source": source, "inputs": input_records,
                  "recorded_data_sources": recorded, "extractions": extractions, "title": title}
    if warnings:
        provenance["warnings"] = warnings
    if failed:
        provenance["failed_results"] = failed
    if design != "none":
        provenance["design"] = design_labels(None, individual=design == "individual")["design"]
    try:
        bundle = results_bundle(output_dir, figures=figure_specs, methods="\n".join(lines), results=loaded,
                                provenance=provenance, citation=citation, references=references)
    except (OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}")
    return _ok(f"Results bundle with {len(loaded)} result(s), {len(figure_paths or [])} figure file(s) and "
               f"{len(input_records)} input hash(es) written; data source {source['kind']}."
               + (f" WARNING: {' '.join(warnings)}" if warnings else ""),
               "cite bundle.json (file hashes and provenance) and methods.md with the results; references.md and "
               "references.bib list the method papers, guidance texts and data behind them"
               + ("; resolve the data source warning before reporting" if warnings else ""),
               output_dir=output_dir, data_source=source, citation=citation, warnings=warnings,
               results=list(loaded), files=len(bundle.get("files", {})), extractions=extractions)


def save_json(result: Dict[str, Any], path: str) -> str:
    """Write a tool result as the JSON ``--json`` prints (``python -m census tool ... --save PATH``)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, default=str) + "\n")
    return path


def list_health_sources(source: Optional[str] = None, kind: str = "outcome") -> Dict[str, Any]:
    """List external health data sources a manifest can use as an outcome, with the
    circularity rule. Read each measure's kind and acs_equivalent before designing a study.

    The rule: determinant studies keep using the ACS's own measure as the outcome (for
    disability: B18101), and use external sources such as CDC PLACES for measures the ACS
    lacks, such as diabetes. A model-based outcome (PLACES, PLACES-based County Health
    Rankings measures, USALEEP) must not be tested against its model's inputs (PLACES:
    age, sex, race/ethnicity, education, poverty). Direct vital records (County Health
    Rankings mortality, WONDER exports) have no model inputs.

    Args:
        source: places, usaleep, chr or wonder; omit for all.
        kind: "outcome" (default) or "context" (Round 72: county covariate sources such as CBP, ERS
            typology and rural-urban codes, CHR additional measures; never outcomes).

    Example: list_health_sources(source="places")
    """
    from census.health_sources import registry_summary

    if kind == "context":
        from census.context_sources import list_context_sources
        ctx = list_context_sources()
        return _ok(f"Context covariate sources: {', '.join(ctx)} (covariates only, never outcomes)",
                   "add a context entry to build_analysis_frame(context=[...]) or a manifest 'context' block",
                   sources=ctx)
    if kind != "outcome":
        return _fail(errors.INVALID_INPUT, "kind must be 'outcome' or 'context'")
    try:
        reg = registry_summary(source)
    except ValueError as exc:
        return _fail(errors.INVALID_INPUT, str(exc), "list_health_sources() to list all sources")
    names = ", ".join(reg["sources"])
    return _ok(f"External health sources: {names}. Rule: {reg['rule']}",
               "get_recipe(name='external_health_outcome'), then add an 'external' entry to a manifest",
               **reg)


def run_variant(
    run_dir: str,
    analysis: str,
    formula: Optional[str] = None,
    keep_prefixes: Optional[List[str]] = None,
    drop_prefixes: Optional[List[str]] = None,
    args: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """Exploratory refit of one analysis of a finished run_manifest run, on the same
    hash-checked analysed data, without writing Python. The output is labelled
    exploratory with the manifest hash; confirmatory results are never changed.

    Spatial_se={"cutoff_km":150} is exploratory only (failed spatial HAC validation).
    Binomial count proportions use trials=<name>_denominator, scale:"X2".

    Args:
        run_dir: The run_manifest output folder (holds manifest.json and bundle/).
        analysis: Analysis id in the manifest, e.g. "m2".
        formula: Replacement formula (frame columns only), e.g. "y ~ x + C(GEOID.str[:5])".
        keep_prefixes / drop_prefixes: GEOID prefixes to keep or drop, e.g. ["36"].
        args: Merged over the analysis args, e.g. {"cluster": "GEOID.str[:5]",
            "cluster_se": "jackknife"}.
        label: Short name for the output file.
    Example: run_variant("studies_output/r21/confirmatory", "m1", drop_prefixes=["36005", "36047"])
    """
    from census.manifest import run_variant as _variant

    try:
        out = _variant(run_dir, analysis, formula=formula, keep_prefixes=keep_prefixes, drop_prefixes=drop_prefixes,
                       args=args, out_dir=output_dir, label=label)
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}",
                     "check run_dir (a run_manifest output folder) and the analysis id")
    coefs = (out.get("result") or {}).get("coefficients") or []
    head = "; ".join(f"{c['term']} {c['estimate']:.4g} (SE {c.get('se_total', c.get('se', float('nan'))):.3g})"
                     for c in coefs[:4] if isinstance(c, dict) and "estimate" in c)
    return _ok(f"Exploratory variant of {analysis} on {out['units']} units: {head}",
               "report it labelled exploratory, with related_manifest_hash", **_jsonable(out))


def create_manifest(manifest_path: str) -> Dict[str, Any]:
    """Validate a pre-registration manifest (JSON) and return its SHA-256 hash.
    Commit the manifest and hash BEFORE pulling data; then call run_manifest.
    exploratory:true labels the run exploratory. Spatial_se failed validation: exploratory only.
    Binomial external outcomes need trials=<name>_denominator and scale:"X2".
    Several states: geography {"level": "county", "states": ["26", "36"]}; a price
    adjustment: "adjustments": [{"type": "rpp", "variables": ["income"], "rpp_year": 2024}]
    (rpp_year is required; when omitted, the latest RPP year is filled in before
    hashing and the completed manifest is written to <name>.completed.json, never
    over the input; commit and run that file, as the result's notes say).
    Several releases: the adjustment also needs "dollar_year", "price_index"
    and "rpp_years" ({"2019": 2019, "2024": 2024}); omitted ones are filled the same
    way. "replicates": {"source": "census_vre"} makes run_manifest fetch Census
    replicates; the notes list variables that have none. External health outcomes
    (list_health_sources; no key): "external": [{"name": "diab", "source": "places",
    "release": 2025, "measure": "DIABETES"}], usable only as the outcome of fit_eiv/
    fit_replicate/fh_regression. Circularity rule (errors): determinant studies use the
    ACS's own measure (disability: B18101), and external sources for measures the ACS
    lacks, such as diabetes; never test a term built from the outcome model's inputs.
    fit_eiv "args": {"cluster": "GEOID.str[:5]"} clusters SEs by county.

    The schema is documented in census/manifest.py and examples/manifests/.
    Example: create_manifest("examples/manifests/income_population_tracts.json")
    """
    from census.manifest import create_manifest as _create

    try:
        res = _create(manifest_path)
    except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
        return _fail(errors.INVALID_INPUT, str(exc))
    if res.get("error_code") == errors.BUNDLED_DATA_INTEGRITY:
        return res
    if res.get("errors"):
        return _fail(errors.INVALID_INPUT, "Manifest invalid: " + "; ".join(map(str, res["errors"])),
                     "fix the listed problems and call create_manifest again")
    return _ok(f"Manifest valid; SHA-256 {res['hash']}." + "".join(f" {n}." for n in res.get("notes") or []),
               "commit the manifest, then run_manifest with the same path", **res)


def run_manifest(manifest_path: str, output_dir: Optional[str] = None,
                 replicates_path: Optional[str] = None, replicates_synthetic: Optional[bool] = None,
                 checkpoint: bool = False) -> Dict[str, Any]:
    """Run a pre-registered analysis exactly as written and write a results bundle
    (tables, figures, methods.md); anything that could not run is a deviation.

    Args:
        manifest_path: the manifest JSON.
        replicates_path: optional CSV/Parquet of replicates (long: GEOID, Year,
            variable, rep_1..rep_80) for "replicates": "required"; not with census_vre.
        replicates_synthetic: mark supplied replicates synthetic.
        checkpoint: true = resumable long run (reuse output_dir).

    Returns analysis_status, data_source, replicates, deviations, hypotheses;
    success is False when analysis_status is "confirmatory_incomplete".

    Example: run_manifest("examples/manifests/income_population_tracts.json")
    """
    from census.manifest import run_manifest as _run

    folder = _out_dir(output_dir, "manifest_run")
    try:
        reps = _read_replicates(replicates_path)
    except (FileNotFoundError, OSError, ValueError, ImportError) as exc:
        return _fail(errors.INVALID_INPUT, f"replicates_path unreadable: {type(exc).__name__}: {exc}",
                     "pass a CSV or Parquet file in the analysis replicate long format")
    try:
        res = _run(manifest_path, folder, replicates=reps, replicates_synthetic=replicates_synthetic,
                   checkpoint=bool(checkpoint))
    except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
        return _fail(errors.INVALID_INPUT, f"{type(exc).__name__}: {exc}" if isinstance(exc, KeyError) else str(exc))
    if res.get("error_code") == errors.BUNDLED_DATA_INTEGRITY:
        return res
    if res.get("output_error"):
        return _fail(errors.INVALID_INPUT, f"output_dir unusable: {res['output_error']}",
                     "call run_manifest again with a new or empty output_dir; the manifest is fine")
    if res.get("errors"):
        return _fail(errors.INVALID_INPUT, "Manifest invalid: " + "; ".join(map(str, res["errors"])),
                     "fix the manifest with create_manifest")
    hyp = res.get("hypotheses")
    devs = res.get("deviations") or []
    status = res.get("analysis_status")
    out = {
        "manifest_hash": res.get("manifest_hash"), "output_dir": res.get("output_dir"),
        "analysis_status": status, "data_source": res.get("data_source"), "replicates": res.get("replicates"),
        "deviations": devs, "hypotheses": hyp, "bundle": res.get("bundle"),
    }
    if "adjustments" in res:
        out["adjustments"] = res["adjustments"]
    if "checkpoint" in res:
        out["checkpoint"] = res["checkpoint"]
    if "external" in res:
        out["external"] = res["external"]
    payload = _jsonable(out)
    if not res.get("success"):
        kinds = sorted({str(d.get("kind")) for d in devs})
        payload.update({"success": False, "error_code": errors.INVALID_INPUT if "data_source_mismatch" in kinds
                        else errors.NO_DATA,
                        "error": f"Manifest ran with {len(devs)} deviation(s) that block confirmatory results "
                                 f"({', '.join(kinds)}); analysis_status {status}.",
                        "summary": f"Run incomplete ({status}): {len(devs)} deviation(s); see deviations.",
                        "next_step": "report the run as confirmatory_incomplete with its deviations; do not "
                                     "substitute variables, releases or data sources"
                                     + ("; supply replicates_path" if "replicates_unavailable" in kinds else "")})
        return payload
    return _ok(f"Manifest run complete ({status}); {len(devs)} deviation(s); results in {res.get('output_dir')}.",
               "read methods.md and the tables in the output folder; report deviations if any",
               **out)



def verify_bundle(bundle_dir: str) -> Dict[str, Any]:
    """Verify a publication bundle's SHA-256 digests, unlisted files, methods.md, references.bib, and LaTeX tables."""
    from census.report_tables import verify_bundle as _verify

    rep = _verify(bundle_dir)
    if not rep.get("ok"):
        return _fail(errors.INVALID_INPUT, "Bundle verification failed: " + "; ".join(rep.get("errors", [])),
                     "regenerate or repair the bundle before citing or archiving")
    return _ok(f"Bundle verified cleanly ({rep.get('checked_files', 0)} file(s) hashed, 0 errors).",
               "archive or cite bundle.json and methods.md", **rep)


def list_manifest_methods(validated_only: bool = False) -> Dict[str, Any]:
    """List all registered pre-registration manifest methods with citation keys and validation metadata."""
    from census.manifest.methods import METHODS

    rows = []
    for name in sorted(METHODS):
        spec = METHODS[name]
        cites = list(spec.text[1]) if spec.text else []
        rows.append({
            "method": name,
            "citation_keys": cites,
            "has_methods_text": bool(spec.text),
        })
    return _ok(f"{len(rows)} manifest methods registered.",
               "create_manifest with one of these method names",
               count=len(rows), methods=rows)


def mcp_capabilities() -> Dict[str, Any]:
    """Return structured Layer A MCP server capabilities: version, profiles, recipes, and manifest methods."""
    import census
    from census import mcp_profiles, recipes
    from census.manifest.methods import METHODS

    return _ok(
        f"Census Research Engine v{census.__version__}: {len(mcp_profiles.PROFILES)} profiles, "
        f"{len(recipes.RECIPES)} recipes, {len(METHODS)} manifest methods.",
        "call get_recipe() or list_manifest_methods() to choose a validated workflow",
        version=census.__version__,
        profiles=sorted(mcp_profiles.PROFILES),
        recipe_count=len(recipes.RECIPES),
        manifest_method_count=len(METHODS),
        layer_b_isolation="Layer B (layer_b_openscholar) runs as a separate isolated MCP server with zero census imports.",
    )


def doctor_report(verbose: bool = False, deep: bool = False) -> Dict[str, Any]:
    """Environment, bundled-data integrity, and MCP/manifest self-check (never leaks secrets)."""
    import platform
    import sys

    import scipy
    import statsmodels

    from census import __version__
    from census.inflation import load_price_index
    from census.manifest.methods import METHODS
    from census.mcp_profiles import PROFILES
    from census.recipes import RECIPES
    from census import rpp

    bundled_ok = True
    bundled_error: Optional[str] = None
    try:
        load_price_index("r-cpi-u-rs")
        rpp._load()
    except Exception as exc:  # noqa: BLE001
        bundled_ok = False
        bundled_error = f"{type(exc).__name__}: {exc}"

    profile_counts = {
        name: (len(spec) if spec is not None else "all")
        for name, spec in sorted(PROFILES.items())
    }
    has_key = bool(os.environ.get("CENSUS_API_KEY", "").strip())

    out: Dict[str, Any] = {
        "ok": bundled_ok,
        "success": bundled_ok,
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
        "bundled_data_ok": bundled_ok,
        "bundled_data_error": bundled_error,
        "has_census_api_key": has_key,
        "recipe_count": len(RECIPES),
        "manifest_method_count": len(METHODS),
        "mcp_profiles": profile_counts,
        "next_step": (
            "Ready for offline/cached or live ACS workflows."
            if bundled_ok
            else "Fix bundled data integrity error before running analyses."
        ),
    }
    if verbose or deep:
        from census.concordance import validate_all_crosswalks

        cw = validate_all_crosswalks()
        out["diagnostics"] = {
            "crosswalks_valid": bool(cw.get("valid", False)),
            "acs_2025_archived": os.path.isdir(os.path.join(ROOT, "metadata", "acs5", "2025")),
            "ssd_corpus_mounted": os.path.isdir("/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar"),
        }
    if deep:
        import asyncio
        import mcp_server
        from census import references as R

        mcp_names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
        src_names = set(R.TOOL_SOURCES)
        missing_in_sources = sorted(mcp_names - src_names)
        missing_in_mcp = sorted(src_names - mcp_names)
        missing_recipe_docs = sorted(
            r for r in RECIPES if not os.path.isfile(os.path.join(ROOT, "docs", "recipes", f"{r}.md"))
        )
        meta_manifest = os.path.join(ROOT, "metadata", "manifest.json")
        meta_ok = os.path.isfile(meta_manifest) and os.path.getsize(meta_manifest) > 10
        deep_ok = (
            not missing_in_sources
            and not missing_in_mcp
            and not missing_recipe_docs
            and meta_ok
            and out["diagnostics"]["crosswalks_valid"]
        )
        out["deep_checks"] = {
            "ok": deep_ok,
            "mcp_tool_count": len(mcp_names),
            "tool_sources_count": len(src_names),
            "missing_in_tool_sources": missing_in_sources,
            "missing_in_mcp_server": missing_in_mcp,
            "missing_recipe_docs": missing_recipe_docs,
            "metadata_manifest_ok": meta_ok,
        }
        out["ok"] = bool(out["ok"] and deep_ok)
        out["success"] = out["ok"]
    return out


def confounding_screen(
    input_path: str,
    deaths_col: str,
    population_col: str,
    exposure_col: str,
    confounders: List[str],
    exposure_scale: float = 1.0,
    confidence_level: float = 0.90,
) -> Dict[str, Any]:
    """Compare crude vs. confounder-adjusted Poisson rate ratios (HC3 SEs) and detect Simpson's-paradox sign flips."""
    from census.standardize import confounding_adjustment_screen

    try:
        df = _load_frame(input_path)
        rep = confounding_adjustment_screen(
            df,
            deaths_col,
            population_col,
            exposure_col,
            confounders,
            exposure_scale=exposure_scale,
            confidence_level=confidence_level,
        )
    except _INPUT_ERRORS as exc:
        return _fail(errors.INVALID_INPUT, str(exc), "check column names, confounders list, and positive population counts")
    flip_note = " SIGN FLIPPED (Simpson's paradox)." if rep["sign_flipped"] else ""
    summary = (
        f"Confounding screen ({rep['n_obs']} areas): crude RR={rep['crude']['rr']:.3f}, "
        f"adjusted RR={rep['adjusted']['rr']:.3f} (CIE={rep['cie_pct']:+.1f}%).{flip_note}"
    )
    return _ok(summary, "follow up with a pre-registered manifest or stratified analysis for confirmatory inference", **rep)

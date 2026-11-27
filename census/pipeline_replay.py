# SPDX-License-Identifier: AGPL-3.0-or-later
"""Extraction diffing, output verification & replay (extracted from census/pipeline.py in Round 152)."""
from census.pipeline import (  # noqa: F401
    Any,
    CensusAPIClient,
    DIFFABLE_EXTENSIONS,
    Dict,
    Entity,
    List,
    LogFn,
    MAX_DIFF_SAMPLES,
    Mapping,
    Optional,
    REPLAY_REQUIRED_FIELDS,
    REPLAY_SCHEMA_VERSION,
    REVISION_EXPLANATION,
    ResearchOptions,
    _key_columns,
    _load_table,
    _row_ids,
    datetime,
    errors,
    fields,
    file_sha256,
    get_default_cache,
    json,
    os,
    pd,
    run_batch,
    timezone,
)



def diff_frames(
    old: pd.DataFrame, new: pd.DataFrame, max_samples: int = MAX_DIFF_SAMPLES
) -> Dict[str, Any]:
    """Cell-level comparison of two output tables (values compared as strings).

    Rows are matched on (GEOID, Year) when those identify rows uniquely,
    otherwise by position.
    """
    keys = _key_columns(old, new)
    o = old.set_index(keys) if keys else old.reset_index(drop=True)
    n = new.set_index(keys) if keys else new.reset_index(drop=True)
    cols = [c for c in o.columns if c in n.columns]
    rows = o.index.intersection(n.index)
    oc = o.loc[rows, cols].astype(str)
    nc = n.loc[rows, cols].astype(str)
    changed = oc.ne(nc)
    n_changed = int(changed.values.sum())
    samples: List[Dict[str, Any]] = []
    if n_changed:
        positions = list(zip(*changed.values.nonzero()))[:max_samples]
        source = o if keys else old.reset_index(drop=True)
        for r, c in positions:
            sample = _row_ids(source, changed.index[r], keys)
            sample.update({"column": str(cols[c]), "old": oc.iat[r, c], "new": nc.iat[r, c]})
            samples.append(sample)
    by_column = changed.sum()
    removed = o.index.difference(n.index)
    added = n.index.difference(o.index)

    def _labels(index: Any) -> List[Any]:
        return [list(x) if isinstance(x, tuple) else x for x in list(index[:max_samples])]

    return {
        "matched_on": keys or "row_position",
        "n_cells_compared": int(changed.size),
        "n_cells_changed": n_changed,
        "changed_by_column": {str(k): int(v) for k, v in by_column[by_column > 0].items()},
        "changes_sample": samples,
        "rows_removed": int(len(removed)),
        "rows_added": int(len(added)),
        "rows_removed_sample": _labels(removed),
        "rows_added_sample": _labels(added),
        "columns_removed": [str(c) for c in o.columns if c not in n.columns],
        "columns_added": [str(c) for c in n.columns if c not in o.columns],
    }


def _diff_files(old_path: str, new_path: str) -> Dict[str, Any]:
    old_sheets, new_sheets = _load_table(old_path), _load_table(new_path)
    sheets: Dict[str, Any] = {}
    for name in sorted(set(old_sheets) | set(new_sheets)):
        if name not in old_sheets or name not in new_sheets:
            sheets[name] = {"sheet_added" if name in new_sheets else "sheet_removed": True}
            continue
        sheets[name] = diff_frames(old_sheets[name], new_sheets[name])
    if list(sheets) == [""]:
        return sheets[""]
    return {
        "n_cells_changed": sum(d.get("n_cells_changed", 0) for d in sheets.values()),
        "sheets": sheets,
    }


_DIFF_FLAGS = (
    "n_cells_changed", "rows_removed", "rows_added", "columns_removed",
    "columns_added", "sheet_added", "sheet_removed",
)


def _data_identical(diff: Mapping[str, Any]) -> bool:
    parts = list(diff["sheets"].values()) if "sheets" in diff else [diff]
    return all(not any(p.get(k) for k in _DIFF_FLAGS) for p in parts)


def _verify_outputs(
    original: Mapping[str, Any], replay: Mapping[str, Any], original_dir: str, replay_dir: str
) -> Dict[str, Any]:
    old_files: Mapping[str, str] = original.get("output_files") or {}
    new_files: Mapping[str, str] = replay.get("output_files") or {}
    files: Dict[str, Dict[str, Any]] = {}
    for rel in sorted(set(old_files) | set(new_files)):
        entry: Dict[str, Any] = {
            "original_sha256": old_files.get(rel),
            "replay_sha256": new_files.get(rel),
        }
        if rel not in new_files:
            entry["status"] = "missing_in_replay"
        elif rel not in old_files:
            entry["status"] = "new_in_replay"
        elif old_files[rel] == new_files[rel]:
            entry["status"] = "identical"
        else:
            entry["status"] = "changed"
            old_path = os.path.join(original_dir, *rel.split("/"))
            new_path = os.path.join(replay_dir, *rel.split("/"))
            if not rel.lower().endswith(DIFFABLE_EXTENSIONS):
                entry["diff"] = None
            elif not os.path.isfile(old_path):
                entry["diff_unavailable"] = "original file no longer exists; hashes only"
            elif file_sha256(old_path) != old_files[rel]:
                entry["diff_unavailable"] = "original file was modified after extraction"
            else:
                try:
                    entry["diff"] = _diff_files(old_path, new_path)
                except Exception as exc:  # unreadable file: report, do not fail the replay
                    entry["diff_unavailable"] = f"could not compare: {exc}"
                else:
                    if _data_identical(entry["diff"]):
                        # Same cells, different bytes (e.g. workbook timestamps).
                        entry["status"] = "equivalent"
        files[rel] = entry
    counts: Dict[str, int] = {}
    for entry in files.values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    verified = bool(files) and all(
        e["status"] in ("identical", "equivalent") for e in files.values()
    )
    if not old_files:
        explanation = "The original metadata records no output files; nothing to verify."
        verified = False
    elif verified:
        explanation = "Every output file matches the original (byte-identical or identical cells)."
    else:
        explanation = REVISION_EXPLANATION
    return {
        "verified": verified,
        "file_status_counts": counts,
        "n_cells_changed": sum(
            (e.get("diff") or {}).get("n_cells_changed", 0) for e in files.values()
        ),
        "files": files,
        "explanation": explanation,
    }


def _provenance_differences(original: Mapping[str, Any], replay: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    if original.get("package_version") != replay.get("package_version"):
        out.append(
            f"package_version {original.get('package_version')} -> {replay.get('package_version')}"
        )
    old_v = (original.get("concordance") or {}).get("metadata_vintages") or {}
    new_v = (replay.get("concordance") or {}).get("metadata_vintages") or {}
    for year in sorted(set(old_v) | set(new_v)):
        a, b = old_v.get(year) or {}, new_v.get(year) or {}
        if (a.get("sha256") != b.get("sha256") or a.get("source") != b.get("source")
                or ("integrity" in a and a.get("integrity") != b.get("integrity"))
                or ("groups" in a and a.get("groups") != b.get("groups"))):
            out.append(
                f"{year} metadata: {a.get('source')}/{a.get('sha256')} -> "
                f"{b.get('source')}/{b.get('sha256')}"
            )
    a_c, b_c = original.get("concordance") or {}, replay.get("concordance") or {}
    if a_c.get("overrides_sha256") != b_c.get("overrides_sha256"):
        out.append(
            f"overrides file {a_c.get('overrides_sha256')} -> {b_c.get('overrides_sha256')}"
        )
    if original.get("selected_concept_ids") != replay.get("selected_concept_ids"):
        out.append("variables resolved to a different concept selection")
    return out


def _entity_from_dict(d: Mapping[str, Any]) -> Entity:
    names = {f.name for f in fields(Entity)}
    return Entity(**{k: v for k, v in d.items() if k in names})


def _options_from_metadata(meta: Mapping[str, Any]) -> ResearchOptions:
    names = {f.name for f in fields(ResearchOptions)}
    recorded = meta.get("options") or {}
    opts = ResearchOptions(**{k: v for k, v in recorded.items() if k in names and k != "cpi_table"})
    if meta.get("cpi_table"):
        opts.cpi_table = {int(y): float(v) for y, v in meta["cpi_table"].items()}
    return opts


def replay_extraction(
    metadata_path: str,
    output_dir: Optional[str] = None,
    verify: bool = True,
    client: Optional[CensusAPIClient] = None,
    refresh: bool = False,
    log: Optional[LogFn] = None,
) -> Dict[str, Any]:
    """Re-run an extraction from its ``<table>_extraction_metadata.json``.

    Uses the recorded table, dataset, years, exact entity list, variables and
    research options (including a caller-supplied cpi_table). Outputs go to
    ``output_dir`` (default ``<original dir>/replays/<UTC timestamp>``; the
    original directory itself is refused so the files being verified survive).

    With ``verify``, every output file's SHA-256 is compared with the hash in
    the original metadata, and changed CSV/Parquet/Excel outputs are compared
    cell by cell (GEOID/year/column/old/new). Differences, e.g. Census
    revisions, give ``success: True, verified: False`` with an explanation.

    ``refresh=True`` bypasses the query cache so the live API is queried
    (detects revisions); by default the recorded ``use_cache`` option is
    honoured, which reproduces cached responses offline.
    """
    try:
        with open(metadata_path, encoding="utf-8") as f:
            original = json.load(f)
    except OSError as exc:
        return errors.error_result(
            errors.INVALID_INPUT, f"Cannot read extraction metadata '{metadata_path}': {exc}"
        )
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, f"'{metadata_path}' is not valid JSON: {exc}")
    if not isinstance(original, dict):
        return errors.error_result(
            errors.INVALID_INPUT, f"'{metadata_path}' is not extraction metadata."
        )
    missing = [k for k in REPLAY_REQUIRED_FIELDS if k not in original]
    if missing:
        return errors.error_result(
            errors.INVALID_INPUT,
            f"'{metadata_path}' (package_version {original.get('package_version', 'unknown')}) "
            f"lacks fields needed for replay: {missing}. Metadata written before replay "
            f"support (schema {REPLAY_SCHEMA_VERSION}) cannot be replayed exactly; re-run the "
            "extraction with the current package to get replayable metadata.",
            missing_fields=missing,
            metadata_package_version=original.get("package_version"),
        )
    try:
        schema = int(original["replay_schema_version"])
    except (TypeError, ValueError):
        schema = REPLAY_SCHEMA_VERSION + 1
    if schema > REPLAY_SCHEMA_VERSION:
        return errors.error_result(
            errors.INVALID_INPUT,
            f"Metadata replay schema {original['replay_schema_version']!r} is not supported "
            f"by this package (supports {REPLAY_SCHEMA_VERSION}); upgrade the package.",
        )

    original_dir = os.path.dirname(os.path.abspath(metadata_path))
    if output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output_dir = os.path.join(original_dir, "replays", stamp)
    if os.path.normcase(os.path.abspath(output_dir)) == os.path.normcase(original_dir):
        return errors.error_result(
            errors.INVALID_INPUT,
            "output_dir is the original extraction directory; replaying there would "
            "overwrite the outputs being verified. Choose another directory.",
        )

    try:
        entities = [_entity_from_dict(d) for d in original["entities"]]
        options = _options_from_metadata(original)
    except (TypeError, ValueError, AttributeError) as exc:
        return errors.error_result(errors.INVALID_INPUT, f"Malformed metadata: {exc}")
    if refresh:
        options.use_cache = False
    if client is None:
        import census.pipeline as _pl
        client = _pl.CensusAPIClient(cache=get_default_cache() if options.use_cache else None)

    result = run_batch(
        original["table_code"],
        entities,
        original["years"],
        output_dir,
        original["output_format"],
        options,
        original["dataset"],
        client,
        log=log,
        variables=original["variables"],
    )
    base = {
        "output_dir": output_dir,
        "original_metadata_path": os.path.abspath(metadata_path),
        "data_source": "query cache allowed" if client.cache is not None else "live API",
    }
    if not result.get("success"):
        return {**result, **base}

    with open(result["metadata_path"], encoding="utf-8") as f:
        replayed = json.load(f)
    out: Dict[str, Any] = {
        "success": True,
        **base,
        "metadata_path": result["metadata_path"],
        "table_code": result["table_code"],
        "successful_calls": result["successful_calls"],
        "failed_calls": result["failed_calls"],
        "provenance_differences": _provenance_differences(original, replayed),
    }
    if verify:
        out.update(_verify_outputs(original, replayed, original_dir, output_dir))
        if result["failed_calls"]:
            out["explanation"] += (
                f" {len(result['failed_calls'])} request(s) failed during replay "
                "(see failed_calls), so missing rows may reflect API errors, not revisions."
            )
    else:
        out["verified"] = None
    return out

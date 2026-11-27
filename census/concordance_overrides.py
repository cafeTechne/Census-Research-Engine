# SPDX-License-Identifier: AGPL-3.0-or-later
"""Concordance rule/override validation & crosswalk helpers (extracted from census/concordance.py in Round 172)."""
from census.concordance import (  # noqa: F401
    Any,
    CROSSWALK_COLUMNS,
    Concordance,
    Dict,
    IDENTITY_RE,
    ISSUE_INVALID_OVERRIDE,
    Issue,
    List,
    NORMALIZATION_VERSION,
    Optional,
    PRIMARY_SOURCE_HOSTS,
    RULES_SUFFIX,
    RULE_COLUMNS,
    SOURCE_MISSING,
    Sequence,
    Set,
    Tuple,
    _unique_keys,
    _units_for_year,
    boundary_is_adjacent,
    crosswalk_dir,
    csv,
    evidence_id_for,
    evidence_path,
    json,
    label_numbers,
    load_rules,
    match_key,
    os,
    re,
    rewrite_label,
    rules_path,
    table_variables,
    urlparse,
    validate_crosswalk_row,
)



def build_rule_evidence(
    table_code: str,
    dataset: str,
    from_year: int,
    to_year: int,
    pattern: str,
    replacement: str,
    client: Any = None,
) -> Dict[str, Any]:
    """Machine-generated evidence for one rule, built only from vintage metadata.

    Lists every (code, before, after) label rewrite, the resulting new matches,
    the rewritten lines that still match nothing, and every guardrail
    violation (numeric changes, conflicting links). Validators regenerate it
    and compare, so stale or hand-edited evidence is rejected.
    """
    table = table_code.upper()
    from_year, to_year = int(from_year), int(to_year)
    compiled = re.compile(pattern)
    import census.concordance as _conc
    vars1, src1 = _conc.table_variables(table, dataset, from_year, client)
    vars2, src2 = _conc.table_variables(table, dataset, to_year, client)
    units1 = _units_for_year(vars1, dataset, from_year)
    units2 = _units_for_year(vars2, dataset, to_year)
    keys1, amb1 = _unique_keys(units1)
    keys2, amb2 = _unique_keys(units2)
    # Exact (automatic) links across the boundary, both directions.
    exact_fwd = {b1: keys2[k] for k, b1 in keys1.items() if k in keys2}
    exact_back = {b2: b1 for b1, b2 in exact_fwd.items()}

    rewrites: List[Dict[str, Any]] = []
    matches: List[Dict[str, str]] = []
    unmatched: List[Dict[str, str]] = []
    conflicts: List[Dict[str, str]] = []
    numeric: List[Dict[str, Any]] = []
    for base in sorted(units1):
        role, canon, _ = units1[base]
        after = rewrite_label(canon, compiled, replacement)
        if after == canon:
            continue
        rewrites.append({"code": base, "role": role, "before": canon, "after": after})
        if label_numbers(canon) != label_numbers(after):
            numeric.append(
                {"code": base, "before_numbers": label_numbers(canon), "after_numbers": label_numbers(after)}
            )
        target = keys2.get((role, match_key(after)))
        if base in amb1:
            unmatched.append({"code": base, "reason": f"ambiguous in {from_year}"})
        elif target is None:
            reason = "matches an ambiguous later line" if any(
                match_key(units2[b][1]) == match_key(after) for b in amb2
            ) else "no later line has this label"
            unmatched.append({"code": base, "reason": reason})
        elif exact_fwd.get(base) == target:
            continue  # already linked automatically; nothing new
        elif base in exact_fwd:
            conflicts.append(
                {
                    "code": base,
                    "to_code": target,
                    "reason": f"{base} already continues as {exact_fwd[base]} in {to_year}; "
                    "the rule would link it to a second later line",
                }
            )
        elif target in exact_back:
            conflicts.append(
                {
                    "code": base,
                    "to_code": target,
                    "reason": f"{target} already continues {exact_back[target]} from {from_year}; "
                    "the rule would map two earlier codes to one later concept",
                }
            )
        else:
            matches.append({"from_code": base, "to_code": target, "role": role, "label": units2[target][1]})
    by_target: Dict[str, List[str]] = {}
    for m in matches:
        by_target.setdefault(m["to_code"], []).append(m["from_code"])
    for target, sources in sorted(by_target.items()):
        if len(sources) > 1:
            conflicts.append(
                {
                    "code": ",".join(sources),
                    "to_code": target,
                    "reason": "the rule maps two earlier codes to one later concept",
                }
            )
    return {
        "kind": "rule",
        "table": table,
        "dataset": dataset,
        "from_year": from_year,
        "to_year": to_year,
        "pattern": pattern,
        "replacement": replacement,
        "normalization_version": NORMALIZATION_VERSION,
        "metadata_sources": {str(from_year): src1, str(to_year): src2},
        "rewrites": rewrites,
        "matches": matches,
        "unmatched": unmatched,
        "conflicts": conflicts,
        "numeric_changes": numeric,
    }


def rule_guardrail_errors(evidence: Dict[str, Any]) -> List[str]:
    """Guardrail violations recorded in rule evidence (empty = acceptable)."""
    errors: List[str] = []
    for year, source in (evidence.get("metadata_sources") or {}).items():
        if source == SOURCE_MISSING:
            errors.append(f"no variable metadata for {year}; the rule cannot be verified")
    if not evidence.get("rewrites"):
        errors.append("the rule matches zero labels")
    elif not evidence.get("matches"):
        errors.append("the rule produces no new matches")
    numeric = evidence.get("numeric_changes") or []
    if numeric:
        codes = ", ".join(n["code"] for n in numeric[:5])
        errors.append(
            f"the rule changes a number (age, dollar or other bound) in {len(numeric)} label(s), e.g. {codes}"
        )
    conflicts = evidence.get("conflicts") or []
    if conflicts:
        errors.append(f"the rule creates {len(conflicts)} conflicting link(s): {conflicts[0]['reason']}")
    return errors


def _check_rule_row(
    row: Dict[str, str], dataset: str, table: str, client: Any = None
) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """(errors, regenerated evidence) for one rule row."""
    errors: List[str] = []
    required = ("table", "from_year", "to_year", "pattern", "rationale", "source_url", "evidence_id", "drafted_by", "reviewed_by", "reviewed_on")
    missing = [c for c in required if not str(row.get(c, "")).strip()]
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    row_table = str(row.get("table", "")).strip().upper()
    if row_table and row_table != table.upper():
        errors.append(f"rule table {row_table} does not match its file's table {table.upper()}")
    drafted, reviewed = str(row.get("drafted_by", "")).strip(), str(row.get("reviewed_by", "")).strip()
    for name, value in (("drafted_by", drafted), ("reviewed_by", reviewed)):
        if value and not IDENTITY_RE.match(value):
            errors.append(f"{name} must look like 'human:<name>' or 'agent:<model>/<session>'")
    if drafted and reviewed and drafted == reviewed:
        errors.append("reviewed_by must differ from drafted_by")
    host = urlparse(str(row.get("source_url", "")).strip()).hostname or ""
    if not any(host == h or host.endswith("." + h) for h in PRIMARY_SOURCE_HOSTS):
        errors.append("source_url must be a census.gov primary source")
    try:
        from_year = int(str(row.get("from_year", "")).strip())
        to_year = int(str(row.get("to_year", "")).strip())
    except ValueError:
        errors.append("from_year and to_year must be integers")
        return errors, None
    if not boundary_is_adjacent(dataset, from_year, to_year):
        errors.append(f"{from_year} -> {to_year} is not one adjacent vintage boundary")
    pattern = str(row.get("pattern", ""))
    replacement = str(row.get("replacement", "") or "")
    try:
        compiled = re.compile(pattern)
        compiled.sub(replacement, "")  # surfaces bad group references
    except (re.error, IndexError) as exc:
        errors.append(f"pattern/replacement is not a valid regular expression: {exc}")
        return errors, None
    if not pattern:
        return errors, None

    regenerated = build_rule_evidence(table, dataset, from_year, to_year, pattern, replacement, client)
    errors.extend(rule_guardrail_errors(regenerated))
    eid = str(row.get("evidence_id", "")).strip()
    path = evidence_path(eid) if eid else ""
    if not eid or not os.path.exists(path):
        errors.append("evidence_id must reference a file in crosswalks/evidence/")
    else:
        with open(path, encoding="utf-8") as f:
            evidence = json.load(f)
        if evidence_id_for(evidence) != eid:
            errors.append("evidence file content does not match its evidence_id")
        elif evidence != regenerated:
            errors.append(
                "evidence no longer matches this rule and the archived metadata; regenerate it "
                "with draft_rule_override"
            )
    return errors, regenerated


def validate_rule_row(
    row: Dict[str, str], dataset: str, table: str, client: Any = None
) -> List[str]:
    """Return the list of problems with one rule row (empty = valid).

    Requirements: a census.gov source_url; two different identities; an
    adjacent year boundary; generated evidence whose hash matches its ID and
    that still matches the archive when regenerated; and the guardrails (the
    rule rewrites at least one label, creates at least one match, changes no
    number in any label, and never links two earlier codes to one later line
    or one earlier code to two later lines).
    """
    return _check_rule_row(row, dataset, table, client)[0]


def rule_cross_conflicts(
    checked: Sequence[Tuple[int, Dict[str, str], Optional[Dict[str, Any]]]]
) -> Dict[int, List[str]]:
    """Rules on the same boundary must not claim the same earlier or later line."""
    claimed: Dict[Tuple[int, int, str, str], int] = {}
    out: Dict[int, List[str]] = {}
    for line, _row, evidence in checked:
        if not evidence:
            continue
        b = (evidence["from_year"], evidence["to_year"])
        for m in evidence.get("matches", []):
            for side, code in (("from", m["from_code"]), ("to", m["to_code"])):
                key = (b[0], b[1], side, code)
                if key in claimed and claimed[key] != line:
                    out.setdefault(line, []).append(
                        f"{code} is already linked by the rule on line {claimed[key]}"
                    )
                claimed.setdefault(key, line)
    return out


def _apply_rules(conc: Concordance, client: Any = None) -> Set[str]:
    """Apply valid rules for the concordance's table; return merged concept IDs."""
    rows = load_rules(conc.dataset, conc.table)
    if not rows:
        return set()
    checked = []
    for idx, row in enumerate(rows, start=2):
        errors, evidence = _check_rule_row(row, conc.dataset, conc.table, client)
        checked.append((idx, row, evidence, errors))
    cross = rule_cross_conflicts([(i, r, e) for i, r, e, errs in checked if not errs])
    merged: Set[str] = set()
    for idx, row, evidence, errors in checked:
        errors = errors + cross.get(idx, [])
        if errors:
            conc.issues.append(
                Issue(
                    ISSUE_INVALID_OVERRIDE,
                    [],
                    f"rule row {idx} rejected: {'; '.join(errors)}",
                    {"row": row, "errors": errors, "file": rules_path(conc.dataset, conc.table)},
                )
            )
            continue
        assert evidence is not None
        y1, y2 = evidence["from_year"], evidence["to_year"]
        if y1 not in conc.years or y2 not in conc.years:
            continue
        reviewer = row["reviewed_by"].strip()
        map1, map2 = conc.code_map(y1), conc.code_map(y2)
        linked: List[Dict[str, str]] = []
        skipped: List[Dict[str, str]] = []
        for m in evidence["matches"]:
            a_id, b_id = map1.get(m["from_code"]), map2.get(m["to_code"])
            a = conc.concepts.get(a_id or "")
            b = conc.concepts.get(b_id or "")
            if a is None or b is None or a is b:
                continue
            if max(a.codes) >= y2 or min(b.codes) <= y1:
                skipped.append({**m, "reason": "concepts overlap in years"})
                continue
            for year, base in a.codes.items():
                b.codes[year] = base
                b.decided_by[year] = reviewer
                if year in a.universes:
                    b.universes[year] = a.universes[year]
            del conc.concepts[a.concept_id]
            merged.discard(a.concept_id)
            merged.add(b.concept_id)
            linked.append({**m, "concept_id": b.concept_id, "merged_concept_id": a.concept_id})
        record = {
            **{c: str(row.get(c, "") or "") for c in RULE_COLUMNS},
            "decision": "rule",
            "line": str(idx),
            "file": rules_path(conc.dataset, conc.table),
            "merges": len(linked),
        }
        conc.rules_applied.append({**record, "links": linked, "skipped": skipped})
        conc.overrides_applied.append(record)
    return merged


def validate_rule_file(dataset: str, table: str, client: Any = None) -> Dict[str, Any]:
    """Validate one crosswalks/<dataset>/<table>_rules.csv file."""
    path = rules_path(dataset, table)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header_ok = list(reader.fieldnames or []) == RULE_COLUMNS
        rows = list(reader)
    file_errors = [] if header_ok else [f"header must be: {','.join(RULE_COLUMNS)}"]
    checked = []
    for idx, row in enumerate(rows, start=2):
        errors, evidence = _check_rule_row(row, dataset, table, client)
        file_errors.extend(f"line {idx}: {e}" for e in errors)
        if not errors:
            checked.append((idx, row, evidence))
    for idx, errs in sorted(rule_cross_conflicts(checked).items()):
        file_errors.extend(f"line {idx}: {e}" for e in errs)
    return {"file": f"{dataset}/{os.path.basename(path)}", "rows": len(rows), "errors": file_errors, "kind": "rule"}


def validate_all_crosswalks(client: Any = None) -> Dict[str, Any]:
    """Validate every crosswalk and rule file (used by CI and the MCP tool)."""
    root = crosswalk_dir()
    results: List[Dict[str, Any]] = []
    if os.path.isdir(root):
        for dataset in sorted(os.listdir(root)):
            ddir = os.path.join(root, dataset)
            if dataset == "evidence" or not os.path.isdir(ddir):
                continue
            for name in sorted(os.listdir(ddir)):
                if not name.endswith(".csv"):
                    continue
                table = name[:-4]
                if table.endswith(RULES_SUFFIX):
                    results.append(validate_rule_file(dataset, table[: -len(RULES_SUFFIX)], client))
                    continue
                with open(os.path.join(ddir, name), newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    header_ok = list(reader.fieldnames or []) == CROSSWALK_COLUMNS
                    rows = list(reader)
                file_errors = [] if header_ok else [f"header must be: {','.join(CROSSWALK_COLUMNS)}"]
                for idx, row in enumerate(rows, start=2):
                    for err in validate_crosswalk_row(row, dataset, table, client):
                        file_errors.append(f"line {idx}: {err}")
                results.append({"file": f"{dataset}/{name}", "rows": len(rows), "errors": file_errors})
    return {
        "valid": all(not r["errors"] for r in results),
        "files": results,
    }

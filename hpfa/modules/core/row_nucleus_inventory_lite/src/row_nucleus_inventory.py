from __future__ import annotations

import argparse, csv, hashlib, io, json, re, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

MODULE_ID = "row_nucleus_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "ROW_NUCLEUS_SURFACE_CANDIDATE_ONLY"
REQUIRED = ("start", "end", "period", "action")
SUPPORT = ("code", "team", "pos_x", "pos_y")
SIG_FIELDS = (*REQUIRED, *SUPPORT)
REVIEW_STATUSES = {"TOKEN_FALLBACK_REVIEW_REQUIRED", "CONFLICT_REVIEW_REQUIRED", "UNKNOWN_UNREVIEWED"}
OUT = {
    "main": "row_nucleus_inventory_lite_v1.json",
    "summary": "row_nucleus_inventory_lite_v1.txt",
    "analyst": "row_nucleus_inventory_analyst_audit_v1.txt",
    "rollup": "g01_g18_data_quality_rollup_v1.json",
    "rollup_txt": "g01_g18_data_quality_rollup_v1.txt",
}


def norm_text(v: Any) -> str | None:
    s = re.sub(r"\s+", " ", str(v or "").strip()).casefold()
    return None if not s or s in {"none", "null", "nan", "n/a", "na", "-"} else s


def norm_num(v: Any) -> str | None:
    s = str(v or "").strip()
    if not s or s.casefold() in {"none", "null", "nan", "n/a", "na", "-"}:
        return None
    if "," in s and "." not in s:
        s = s.replace(" ", "").replace(",", ".")
    try:
        n = Decimal(s)
    except InvalidOperation:
        return norm_text(s)
    if not n.is_finite():
        return None
    s = format(n.normalize(), "f")
    return (s.rstrip("0").rstrip(".") if "." in s else s) or "0"


def norm_field(k: str, v: Any) -> str | None:
    return norm_num(v) if k in {"id", "start", "end", "period", "pos_x", "pos_y"} else norm_text(v)


def norm_header(v: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(v or "").casefold())).strip("_")


def norm_label(v: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(v or "").casefold().replace("%", " percent "))).strip()


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_out(path: str | Path) -> Path:
    out = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in out.parts and out.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return out


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("upstream_output_unreadable_or_malformed") from exc
    if not isinstance(value, dict):
        raise ValueError("upstream_output_not_object")
    return value


def upstream_guard(items: list[tuple[str, dict[str, Any]]]) -> tuple[list[str], list[str]]:
    blocks, reviews = [], []
    for name, p in items:
        if p.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"canonical_event_count_claimed:{name}")
        if p.get("production_release") is True:
            blocks.append(f"unexpected_production_claim:{name}")
        status = str(p.get("module_status") or p.get("status") or "UNKNOWN")
        if status == "FAIL_CLOSED":
            blocks.append(f"upstream_fail_closed:{name}")
        elif status not in {"PASS", "REVIEW_REQUIRED", "SPEC_ONLY", "SMOKE_PASS"}:
            reviews.append(f"upstream_status_review:{name}:{status}")
        blocks.extend(f"upstream_hard_block:{name}:{x}" for x in p.get("hard_block_hits", []) or [])
    return sorted(set(blocks)), sorted(set(reviews))


def runtime_path(root: Path, row: dict[str, Any]) -> Path:
    path = (root / str(row.get("relative_path") or row.get("file_name") or "")).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("surface_path_outside_active_match") from exc
    return path


def csv_rows(root: Path, audit: dict[str, Any]) -> list[dict[str, Any]]:
    headers = [str(x) for x in audit.get("raw_columns", []) or []]
    delim = audit.get("delimiter_candidate")
    if not headers or not delim:
        raise ValueError("csv_parse_contract_missing")
    try:
        text = runtime_path(root, audit).read_text(encoding=str(audit.get("encoding_candidate") or "utf-8"))
        parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=str(delim)))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError("csv_surface_unreadable_or_malformed") from exc
    normalized = [norm_header(x) for x in headers]
    header_i = next((i for i, row in enumerate(parsed) if [norm_header(x) for x in row] == normalized), None)
    if header_i is None:
        raise ValueError("csv_header_contract_mismatch")
    positions = {name: i for i, name in enumerate(normalized) if name}
    bundle = audit.get("field_bundle") or {}

    def idx(key: str, fallback: str | None = None) -> int | None:
        raw = bundle.get(key)
        return positions.get(norm_header(raw)) if raw is not None and norm_header(raw) in positions else positions.get(fallback or key)

    indexes = {"id": positions.get("id"), "start": idx("start"), "end": idx("end"), "period": idx("period", "half"), "action": idx("action"), "code": positions.get("code"), "team": idx("team"), "pos_x": idx("start_x", "pos_x"), "pos_y": idx("start_y", "pos_y")}
    if any(indexes[k] is None for k in ("id", *REQUIRED)):
        raise ValueError("csv_required_nucleus_field_missing")
    result = []
    for row in parsed[header_i + 1 :]:
        if len(row) != len(headers) or not any(str(x).strip() for x in row) or [norm_header(x) for x in row] == normalized:
            continue

        def value(k: str) -> str | None:
            i = indexes[k]
            return str(row[i]).strip() if i is not None else None

        action, code, team = value("action"), value("code"), value("team")
        if not team and code and action and code.endswith(f" - {action}"):
            team = code[: -len(f" - {action}")].strip() or None
        raw = {"id": value("id"), "start": value("start"), "end": value("end"), "period": value("period"), "action": action, "code": code, "team": team, "pos_x": value("pos_x"), "pos_y": value("pos_y")}
        result.append({k: norm_field(k, v) for k, v in raw.items()})
    return result


def local_name(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def descendant(elem: ET.Element, name: str) -> str | None:
    for node in elem.iter():
        if local_name(node.tag).casefold() == name.casefold() and str(node.text or "").strip():
            return str(node.text).strip()
    return None


def group_map(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("candidate_only") is not True or payload.get("validated_semantics") is not False:
        raise ValueError("xml_group_registry_not_candidate_only")
    result = {}
    for row in payload.get("exact_group_rules", []) or []:
        raw, key = norm_text(row.get("raw_group_label")), str(row.get("field_key_candidate") or "")
        if not raw or not key or not row.get("rule_id") or not row.get("source_ref"):
            raise ValueError("xml_group_registry_rule_incomplete")
        if raw in result and result[raw] != key:
            raise ValueError("xml_group_registry_conflict")
        result[raw] = key
    if not {"action", "period", "team", "pos_x", "pos_y"}.issubset(set(result.values())):
        raise ValueError("xml_group_registry_incomplete")
    return result


def xml_rows(root: Path, audit: dict[str, Any], mapping: dict[str, str]) -> list[dict[str, Any]]:
    guard = audit.get("security_guard") or {}
    if guard.get("status") != "PASS" or guard.get("dtd_or_entity_declaration_present") is True:
        raise ValueError("xml_security_contract_not_pass")
    selected = str(audit.get("selected_row_tag_candidate") or "")
    if not selected:
        raise ValueError("xml_row_container_candidate_missing")
    try:
        tree = ET.parse(runtime_path(root, audit)).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError("xml_surface_unreadable_or_malformed") from exc
    result = []
    for elem in tree.iter():
        if local_name(elem.tag) != selected:
            continue
        labels: dict[str, list[str]] = defaultdict(list)
        for label in elem.iter():
            if local_name(label.tag).casefold() != "label":
                continue
            group, text = descendant(label, "group"), descendant(label, "text")
            key = mapping.get(norm_text(group) or "") if group and text else None
            if key:
                labels[key].append(text)

        def one(key: str) -> str | None:
            values = list(dict.fromkeys(labels.get(key, [])))
            return values[0] if len(values) == 1 else None

        action, code, team = one("action"), descendant(elem, "code"), one("team")
        if not team and code and action and code.endswith(f" - {action}"):
            team = code[: -len(f" - {action}")].strip() or None
        raw = {"id": descendant(elem, "ID"), "start": descendant(elem, "start"), "end": descendant(elem, "end"), "period": one("period"), "action": action, "code": code, "team": team, "pos_x": one("pos_x"), "pos_y": one("pos_y")}
        result.append({k: norm_field(k, v) for k, v in raw.items()})
    return result


def unique_files(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped, seen = defaultdict(list), set()
    for row in payload.get("files", []) or []:
        role = str(row.get("source_role") or "UNKNOWN")
        key = (role, str(row.get("sha256") or row.get("relative_path") or ""))
        if key in seen:
            continue
        seen.add(key)
        grouped[role].append(row)
    return dict(grouped)


def indexed(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int], int]:
    counts = Counter(str(r.get("id")) for r in rows if r.get("id") is not None)
    duplicates = {k: n for k, n in counts.items() if n > 1}
    values = {str(r["id"]): r for r in rows if r.get("id") is not None and counts[str(r["id"])] == 1}
    return values, duplicates, sum(r.get("id") is None for r in rows)


def semantic_index(payload: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    result: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("provider_label_records", []) or []:
        key = (str(row.get("source_role") or "UNKNOWN"), norm_label(row.get("raw_label") or row.get("normalized_label")))
        if key[1]:
            result[key].append(row)
    return dict(result)


def gate(gid: str, status: str, message: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"gate_id": gid, "status": status, "message": message, "evidence": evidence or {}}


def build_inventory(root_path: str | Path, inventory: dict[str, Any], csv_payload: dict[str, Any], xml_payload: dict[str, Any], field_payload: dict[str, Any], label_payload: dict[str, Any], reconciliation: dict[str, Any], aggregate: dict[str, Any], dictionary: dict[str, Any], xml_registry: dict[str, Any]) -> dict[str, Any]:
    root = Path(root_path).expanduser().resolve(strict=False)
    blocks, reviews = upstream_guard([("inventory", inventory), ("csv", csv_payload), ("xml", xml_payload), ("field_semantics", field_payload), ("label_semantics", label_payload), ("reconciliation", reconciliation), ("aggregate_alignment", aggregate), ("metric_dictionary", dictionary)])
    if not root.is_dir(): blocks.append("input_root_missing")
    if not root.as_posix().rstrip("/").endswith("runtime/active_single_match/current"): blocks.append("runtime_authority_path_invalid")
    if reconciliation.get("module_id") != "cross_format_reconciliation_lite_v1": blocks.append("reconciliation_contract_mismatch")
    if label_payload.get("module_id") != "provider_label_value_semantics_lite_v1": blocks.append("label_semantics_contract_mismatch")
    if dictionary.get("module_id") != "provider_metric_dictionary_lite_v1": blocks.append("metric_dictionary_contract_mismatch")
    if (inventory.get("duplicate_report") or {}).get("exact_duplicate_reflection_count") is None: blocks.append("duplicate_reflection_lineage_missing")
    try: mapping = group_map(xml_registry)
    except ValueError as exc: mapping = {}; blocks.append(str(exc))

    nuclei, role_audits = [], []
    semantics = semantic_index(label_payload)
    csv_roles, xml_roles = unique_files(csv_payload), unique_files(xml_payload)
    roles = sorted(set(csv_roles) | set(xml_roles))
    if not blocks:
        for role in roles:
            if len(csv_roles.get(role, [])) != 1 or len(xml_roles.get(role, [])) != 1:
                reviews.append(f"unpaired_or_ambiguous_role:{role}"); continue
            cfile, xfile = csv_roles[role][0], xml_roles[role][0]
            try: crows, xrows = csv_rows(root, cfile), xml_rows(root, xfile, mapping)
            except ValueError as exc: blocks.append(f"row_surface_unreadable:{role}:{exc}"); continue
            ci, cd, cm = indexed(crows); xi, xd, xm = indexed(xrows)
            if cd or xd: blocks.append(f"duplicate_provider_row_id_candidate:{role}")
            if cm or xm: blocks.append(f"missing_provider_row_id_candidate:{role}")
            role_records, sig_ids = [], defaultdict(list)
            for row_id in sorted(set(ci) | set(xi), key=lambda v: (len(v), v)):
                c, x = ci.get(row_id), xi.get(row_id); rep = c or x or {}
                req_bad = [f for f in REQUIRED if c is None or x is None or c.get(f) is None or c.get(f) != x.get(f)]
                sup_bad = [f for f in SUPPORT if c is not None and x is not None and (c.get(f) is not None or x.get(f) is not None) and c.get(f) != x.get(f)]
                pp = [f for f in SUPPORT if c is not None and x is not None and c.get(f) is not None and c.get(f) == x.get(f)]
                bm = [f for f in SUPPORT if c is not None and x is not None and c.get(f) is None and x.get(f) is None]
                om = [f for f in SUPPORT if c is not None and x is not None and ((c.get(f) is None) != (x.get(f) is None))]
                sig0, sig1 = digest(*(rep.get(f) for f in SIG_FIELDS)), digest(row_id, *(rep.get(f) for f in SIG_FIELDS))
                sig_ids[sig0].append(row_id)
                sem = semantics.get((role, norm_label(rep.get("action"))), [])
                statuses = sorted({str(r.get("mapping_status") or "UNKNOWN") for r in sem})
                families = sorted({str(r.get("action_family_candidate")) for r in sem if r.get("action_family_candidate")})
                reasons = []
                if c is None or x is None: reasons.append("one_sided_visible_surface")
                if req_bad: reasons.append("required_field_mismatch")
                if sup_bad: reasons.append("supporting_field_mismatch")
                if not sem or any(s in REVIEW_STATUSES for s in statuses): reasons.append("semantic_mapping_not_cleared")
                if len(families) > 1: reasons.append("multiple_action_family_candidates")
                rec = {
                    "nucleus_id": "rn_" + digest(role, row_id, sig1, cfile.get("sha256"), xfile.get("sha256"))[:24],
                    "source_role": role, "provider_row_id_candidate": row_id,
                    "source_relative_paths": [str(cfile.get("relative_path") or cfile.get("file_name") or ""), str(xfile.get("relative_path") or xfile.get("file_name") or "")],
                    "source_sha256_lineage": [cfile.get("sha256"), xfile.get("sha256")],
                    "csv_surface_ref": bool(c), "xml_surface_ref": bool(x),
                    "candidate_signature_without_id": sig0, "candidate_signature_with_id": sig1,
                    "start_candidate": rep.get("start"), "end_candidate": rep.get("end"), "period_candidate": rep.get("period"),
                    "action_raw": rep.get("action"), "code_raw": rep.get("code"), "team_raw_candidate": rep.get("team"),
                    "pos_x_candidate": rep.get("pos_x"), "pos_y_candidate": rep.get("pos_y"),
                    "semantic_role_candidates": sorted({str(r.get("semantic_role_candidate")) for r in sem if r.get("semantic_role_candidate")}),
                    "action_family_candidates": families,
                    "outcome_candidates": sorted({str(r.get("outcome_candidate")) for r in sem if r.get("outcome_candidate")}),
                    "mapping_statuses": statuses, "mapping_rule_ids": sorted({str(r.get("rule_id")) for r in sem if r.get("rule_id")}),
                    "cross_format_support_status": "EXACT_REQUIRED_AND_SUPPORT_CANDIDATE" if not req_bad and not sup_bad and c is not None and x is not None else "REVIEW_REQUIRED_SURFACE_SUPPORT",
                    "present_present_support_fields": pp, "both_missing_support_fields": bm, "one_missing_support_fields": om,
                    "required_mismatch_fields": req_bad, "supporting_mismatch_fields": sup_bad,
                    "cross_id_collision_status": "NOT_EVALUATED", "duplicate_reflection_status": "LINEAGE_PRESERVED_NOT_RECOUNTED",
                    "aggregate_definition_dependency": "DERIVATION_DEPENDENCY_UNRESOLVED",
                    "ambiguity_reasons": sorted(set(reasons)), "hard_block_hits": [], "review_hits": sorted(set(reasons)),
                    "nucleus_status": "REVIEW_REQUIRED" if reasons else "PASS",
                    "validated_event_identity": False, "canonical_event_count": CANONICAL_EVENT_COUNT, "claim_ceiling": CLAIM_CEILING,
                }
                role_records.append(rec)
            collisions = {s: ids for s, ids in sig_ids.items() if len(ids) > 1}
            for rec in role_records:
                if rec["candidate_signature_without_id"] in collisions:
                    rec["cross_id_collision_status"] = "CROSS_ID_COLLISION_CANDIDATE"
                    rec["review_hits"] = sorted(set(rec["review_hits"] + ["cross_id_signature_collision_candidate"])); rec["ambiguity_reasons"] = rec["review_hits"]; rec["nucleus_status"] = "REVIEW_REQUIRED"
                else: rec["cross_id_collision_status"] = "NO_COLLISION_OBSERVED"
            nuclei.extend(role_records)
            role_audits.append({"source_role": role, "csv_row_candidate_count": len(crows), "xml_row_candidate_count": len(xrows), "nucleus_candidate_count": len(role_records), "cross_id_collision_candidate_count": sum(len(ids)-1 for ids in collisions.values()), "review_required_nucleus_count": sum(r["nucleus_status"] == "REVIEW_REQUIRED" for r in role_records)})

    blocks, reviews = sorted(set(blocks)), sorted(set(reviews))
    review_count = sum(r.get("nucleus_status") == "REVIEW_REQUIRED" for r in nuclei)
    collision_count = sum(r.get("cross_id_collision_status") == "CROSS_ID_COLLISION_CANDIDATE" for r in nuclei)
    unknown_count = sum(not r.get("mapping_statuses") for r in nuclei)
    reflection_count = int((inventory.get("duplicate_report") or {}).get("exact_duplicate_reflection_count") or 0)
    gates = [
        gate("G01", "FAIL_CLOSED" if blocks else "PASS", "Upstream contracts checked.", {"hard_block_hits": blocks}),
        gate("G02", "FAIL_CLOSED" if "runtime_authority_path_invalid" in blocks else "PASS", "Runtime authority checked.", {"input_root": str(root)}),
        gate("G03", "PASS", "Source-role and reference separation preserved.", {"source_roles": roles}),
        gate("G04", "FAIL_CLOSED" if blocks else "PASS", "Field semantics dependency checked."),
        gate("G05", "FAIL_CLOSED" if any("required_nucleus_field_missing" in x for x in blocks) else "PASS", "Required row fields checked."),
        gate("G06", "REVIEW_REQUIRED" if any("required_field_mismatch" in r.get("review_hits", []) for r in nuclei) else "PASS", "Temporal surface checked."),
        gate("G07", "REVIEW_REQUIRED" if any(r.get("pos_x_candidate") is None or r.get("pos_y_candidate") is None for r in nuclei) else "PASS", "Coordinate surface checked."),
        gate("G08", "FAIL_CLOSED" if any("provider_row_id_candidate" in x for x in blocks) else "PASS", "Provider row-id surface checked."),
        gate("G09", "REVIEW_REQUIRED" if any(r.get("cross_format_support_status") != "EXACT_REQUIRED_AND_SUPPORT_CANDIDATE" for r in nuclei) else "PASS", "Same-role reconciliation checked."),
        gate("G10", "PASS", "Duplicate reflections remain lineage.", {"exact_duplicate_reflection_count": reflection_count}),
        gate("G11", "REVIEW_REQUIRED" if collision_count else "PASS", "Cross-ID collisions checked.", {"collision_nucleus_count": collision_count}),
        gate("G12", "REVIEW_REQUIRED" if unknown_count or review_count else "PASS", "Label semantic readiness checked."),
        gate("G13", "REVIEW_REQUIRED" if any(len(r.get("action_family_candidates") or []) != 1 for r in nuclei) else "PASS", "Action-family ambiguity checked."),
        gate("G14", "PASS", "Identity remains candidate-only."), gate("G15", "PASS", "Missing and zero remain distinct."),
        gate("G16", "REVIEW_REQUIRED" if aggregate.get("definition_alignment_cleared") is not True else "PASS", "Aggregate derivation dependency checked."),
        gate("G17", "PASS", "Claim layer remains closed.", {"claim_allowed": False}),
        gate("G18", "PASS", "Traceability and release invariants preserved.", {"canonical_event_count": CANONICAL_EVENT_COUNT, "production_release": False}),
    ]
    states = [g["status"] for g in gates]; rollup = "FAIL_CLOSED" if "FAIL_CLOSED" in states else ("REVIEW_REQUIRED" if "REVIEW_REQUIRED" in states else "PASS")
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews or review_count or rollup == "REVIEW_REQUIRED" else "PASS")
    return {
        "module_id": MODULE_ID, "status": status, "module_status": status, "runtime_evidence_status": "NOT_EVALUATED", "release_status": "NOT_PRODUCTION", "input_root": str(root),
        "row_nuclei": nuclei, "row_nucleus_candidate_count": len(nuclei), "row_nucleus_pass_count": sum(r["nucleus_status"] == "PASS" for r in nuclei), "row_nucleus_review_required_count": review_count,
        "source_role_count": len(role_audits), "role_audits": role_audits,
        "g01_g18_rollup": {"status": rollup, "gates": gates, "pass_count": states.count("PASS"), "review_required_count": states.count("REVIEW_REQUIRED"), "fail_closed_count": states.count("FAIL_CLOSED"), "not_applicable_count": states.count("NOT_APPLICABLE")},
        "duplicate_reflection_count": reflection_count, "cross_id_collision_nucleus_count": collision_count, "unknown_mapping_nucleus_count": unknown_count,
        "hard_block_hits": blocks, "review_hits": reviews, "active_match_evidence_pass": False,
        "row_nucleus_is_canonical_event": False, "base_event_admission_allowed": False, "validated_event_identity": False, "validated_team_identity": False, "validated_player_identity": False, "validated_cross_role_equivalence": False,
        "aggregate_definition_truth": False, "metric_value_output_allowed": False, "comparison_allowed": False, "claim_allowed": False, "sequence_truth": False, "possession_truth": False, "phase_truth": False, "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT, "production_release": False, "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {"safe_statement": "Visible same-role CSV/XML row candidates were assembled into row-nucleus candidates with source lineage and semantic-review status. They are not canonical events, validated identities or tactical truth."},
    }


def render_summary(p: dict[str, Any]) -> str:
    return "\n".join(["HPFA ROW NUCLEUS INVENTORY LITE V1", f"status={p.get('status')}", f"row_nucleus_candidate_count={p.get('row_nucleus_candidate_count')}", f"row_nucleus_review_required_count={p.get('row_nucleus_review_required_count')}", f"g01_g18_status={(p.get('g01_g18_rollup') or {}).get('status')}", f"hard_block_hits={p.get('hard_block_hits')}", "canonical_event_count=UNKNOWN", "production_release=false", ""])


def write_outputs(p: dict[str, Any], out_dir: str | Path) -> None:
    out = validate_out(out_dir); out.mkdir(parents=True, exist_ok=True); roll = p.get("g01_g18_rollup") or {}
    (out / OUT["main"]).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / OUT["summary"]).write_text(render_summary(p), encoding="utf-8")
    (out / OUT["analyst"]).write_text((p.get("analyst_evidence") or {}).get("safe_statement", "") + "\ncanonical_event_count=UNKNOWN\nproduction_release=false\n", encoding="utf-8")
    (out / OUT["rollup"]).write_text(json.dumps(roll, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / OUT["rollup_txt"]).write_text("\n".join(["HPFA G01-G18 DATA QUALITY ROLLUP V1", f"status={roll.get('status')}", *(f"{g.get('gate_id')}={g.get('status')}" for g in roll.get("gates", []) or []), "canonical_event_count=UNKNOWN", "production_release=false", ""]), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    for name in ("input-root", "inventory", "csv-audit", "xml-audit", "field-semantics", "label-semantics", "reconciliation", "aggregate-alignment", "metric-dictionary", "xml-group-registry", "out"):
        ap.add_argument(f"--{name}", required=True)
    a = ap.parse_args()
    p = build_inventory(a.input_root, load_json(a.inventory), load_json(a.csv_audit), load_json(a.xml_audit), load_json(a.field_semantics), load_json(a.label_semantics), load_json(a.reconciliation), load_json(a.aggregate_alignment), load_json(a.metric_dictionary), load_json(a.xml_group_registry))
    write_outputs(p, a.out)
    print(json.dumps({k: p.get(k) for k in ("status", "row_nucleus_candidate_count", "row_nucleus_review_required_count", "cross_id_collision_nucleus_count", "canonical_event_count", "production_release")}, ensure_ascii=False, indent=2))
    return 2 if p["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())

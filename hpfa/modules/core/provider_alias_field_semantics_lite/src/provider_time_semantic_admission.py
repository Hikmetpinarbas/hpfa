from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "provider_time_semantic_admission_lite_v1"
CLAIM_SAFETY = "PROVIDER_TIME_SEMANTIC_CANDIDATE_ONLY"
RULE_ID = "sportsbase_like_start_end_absolute_seconds_v1"
ABSOLUTE_SECONDS = "ABSOLUTE_MATCH_SECONDS"
SECOND = "SECOND"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
ADMITTED = "ADMITTED"
TOLERANCE = 0.02

CSV_REQUIRED = {"start", "end", "half"}
XML_REQUIRED = {"start", "end"}
ROW_NUCLEUS_MODULE_ID = "row_nucleus_inventory_lite_v1"


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _num(value: Any) -> float | None:
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number


def _delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    first = (sample.splitlines() or [""])[0]
    if first.count(";") >= first.count(",") and first.count(";") >= first.count("\t"):
        return ";"
    if first.count("\t") > first.count(","):
        return "\t"
    return ","


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=_delimiter(path))
        for index, row in enumerate(reader):
            payload = dict(row)
            payload["_source_file"] = path.name
            payload["_source_format"] = "csv"
            payload["_source_row_index"] = index
            rows.append(payload)
    return rows


def _local_tag(tag: Any) -> str:
    return str(tag).split("}")[-1].strip().casefold()


def _read_xml_instance_rows(path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    instances = [elem for elem in root.iter() if _local_tag(elem.tag) == "instance"]
    rows: list[dict[str, Any]] = []
    for index, elem in enumerate(instances):
        payload: dict[str, Any] = dict(elem.attrib)
        for child in elem.iter():
            if child is elem:
                continue
            text = (child.text or "").strip()
            if text:
                payload.setdefault(_local_tag(child.tag), text)
            for key, value in child.attrib.items():
                if value:
                    payload.setdefault(_local_tag(key), value)
        payload["_source_file"] = path.name
        payload["_source_format"] = "xml"
        payload["_source_row_index"] = index
        rows.append(payload)
    return rows


def _visible_columns(rows: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for row in rows[:100]:
        keys.update(_norm(k) for k in row if not str(k).startswith("_"))
    return keys


def _values(rows: list[dict[str, Any]], field: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        lower = {_norm(k): v for k, v in row.items()}
        value = _num(lower.get(field))
        if value is not None:
            out.append(value)
    return out


def _pairs_valid(rows: list[dict[str, Any]]) -> bool:
    visible = 0
    for row in rows:
        lower = {_norm(k): v for k, v in row.items()}
        start = _num(lower.get("start"))
        end = _num(lower.get("end"))
        if start is None and end is None:
            continue
        visible += 1
        if start is None or end is None or start < 0 or end < start:
            return False
    return visible > 0


def _rounded_counter(values: list[float]) -> Counter[float]:
    return Counter(round(value, 2) for value in values)


def _cross_format_equal(csv_values: list[float], xml_values: list[float]) -> bool:
    return bool(csv_values) and _rounded_counter(csv_values) == _rounded_counter(xml_values)


def _half_ranges(csv_rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    by_half: dict[str, list[float]] = defaultdict(list)
    for row in csv_rows:
        lower = {_norm(k): v for k, v in row.items()}
        half = str(lower.get("half") or lower.get("period") or "UNKNOWN").strip()
        start = _num(lower.get("start"))
        if start is not None:
            by_half[half].append(start)
    result: dict[str, dict[str, float | int | None]] = {}
    for half, values in sorted(by_half.items()):
        result[half] = {
            "count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return result


def build_time_admission(input_root: str | Path) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    csv_files = sorted(path for path in root.glob("*.csv") if path.is_file())
    xml_files = sorted(path for path in root.glob("*.xml") if path.is_file())
    csv_rows = [row for path in csv_files for row in _read_csv_rows(path)]
    xml_rows = [row for path in xml_files for row in _read_xml_instance_rows(path)]

    csv_columns = _visible_columns(csv_rows)
    xml_columns = _visible_columns(xml_rows)
    schema_ready = CSV_REQUIRED <= csv_columns and XML_REQUIRED <= xml_columns
    pairs_valid = _pairs_valid(csv_rows) and _pairs_valid(xml_rows)

    csv_start = _values(csv_rows, "start")
    csv_end = _values(csv_rows, "end")
    xml_start = _values(xml_rows, "start")
    xml_end = _values(xml_rows, "end")
    cross_start = _cross_format_equal(csv_start, xml_start)
    cross_end = _cross_format_equal(csv_end, xml_end)

    halves = _half_ranges(csv_rows)
    h1 = halves.get("1") or {}
    h2 = halves.get("2") or {}
    h1_max = h1.get("max")
    h2_min = h2.get("min")
    absolute_continuation = (
        isinstance(h1_max, (int, float))
        and isinstance(h2_min, (int, float))
        and float(h2_min) > float(h1_max)
    )

    reasons: list[str] = []
    if not schema_ready:
        reasons.append("provider_time_schema_not_admitted")
    if not pairs_valid:
        reasons.append("start_end_pair_invalid")
    if not cross_start:
        reasons.append("csv_xml_start_surface_mismatch")
    if not cross_end:
        reasons.append("csv_xml_end_surface_mismatch")
    if not absolute_continuation:
        reasons.append("absolute_match_time_basis_not_demonstrated")

    status = ADMITTED if not reasons else REVIEW_REQUIRED
    return {
        "module_id": MODULE_ID,
        "status": status,
        "rule_id": RULE_ID,
        "claim_safety": CLAIM_SAFETY,
        "source_surface_candidate": "SPORTSBASE_LIKE",
        "unit_candidate": SECOND,
        "unit_admission_status": status,
        "time_basis_candidate": ABSOLUTE_SECONDS if absolute_continuation else "UNKNOWN",
        "time_basis_admission_status": status if absolute_continuation else REVIEW_REQUIRED,
        "runtime_checks": {
            "csv_file_count": len(csv_files),
            "xml_file_count": len(xml_files),
            "csv_surface_row_count": len(csv_rows),
            "xml_instance_surface_count": len(xml_rows),
            "schema_ready": schema_ready,
            "start_end_pairs_valid": pairs_valid,
            "csv_xml_start_multiset_equal": cross_start,
            "csv_xml_end_multiset_equal": cross_end,
            "half_start_ranges": halves,
            "absolute_continuation_across_halves": absolute_continuation,
        },
        "review_reasons": reasons,
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _load_mvc(repo_root: Path):
    src = repo_root / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import minimum_viable_context  # type: ignore

    return minimum_viable_context


def _normalize_rows_for_mvc(
    rows: list[dict[str, Any]],
    admission: dict[str, Any],
) -> list[dict[str, Any]]:
    if admission.get("status") != ADMITTED:
        return rows
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        lower = {_norm(k): v for k, v in row.items()}
        start = _num(lower.get("start"))
        if start is not None:
            item["absolute_time_seconds"] = start
            item["_provider_time_rule_id"] = RULE_ID
            item["_provider_time_basis"] = ABSOLUTE_SECONDS
        normalized.append(item)
    return normalized


def _load_row_nucleus_payload(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("row_nucleus_binding_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("row_nucleus_binding_malformed") from exc

    if not isinstance(payload, dict):
        raise ValueError("row_nucleus_binding_not_object")
    if payload.get("module_id") != ROW_NUCLEUS_MODULE_ID:
        raise ValueError("row_nucleus_binding_module_mismatch")
    if payload.get("status") == "FAIL_CLOSED":
        raise ValueError("row_nucleus_binding_fail_closed")
    if payload.get("content_source_role_bridge_status") != "PASS":
        raise ValueError("row_nucleus_source_role_bridge_not_pass")
    if payload.get("canonical_event_count") != "UNKNOWN":
        raise ValueError("row_nucleus_canonical_event_count_claimed")
    if payload.get("true_action_count") not in (None, "UNKNOWN"):
        raise ValueError("row_nucleus_true_action_count_claimed")
    if payload.get("production_release") is True:
        raise ValueError("row_nucleus_production_release_claimed")

    nuclei = payload.get("row_nuclei")
    if not isinstance(nuclei, list) or not nuclei:
        raise ValueError("row_nucleus_binding_empty")
    if payload.get("row_nucleus_candidate_count") != len(nuclei):
        raise ValueError("row_nucleus_binding_count_mismatch")
    return payload


def _row_nucleus_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, nucleus in enumerate(payload.get("row_nuclei") or []):
        if not isinstance(nucleus, dict):
            raise ValueError(f"row_nucleus_record_invalid:{index}")
        resolved = nucleus.get("resolved_visible_fields") or {}
        if not isinstance(resolved, dict):
            raise ValueError(f"row_nucleus_resolved_fields_invalid:{index}")

        row = {
            "start": resolved.get("start"),
            "end": resolved.get("end"),
            "code": resolved.get("code"),
            "team": resolved.get("team"),
            "action": resolved.get("action"),
            "half": resolved.get("half"),
            "pos_x": resolved.get("pos_x"),
            "pos_y": resolved.get("pos_y"),
            "_source_file": str(nucleus.get("row_nucleus_candidate_id") or f"row_nucleus_{index}"),
            "_source_format": "row_nucleus",
            "_source_row_index": index,
            "_preserved_unmapped": {
                "row_nucleus_candidate_id": nucleus.get("row_nucleus_candidate_id"),
                "row_nucleus_status": nucleus.get("status"),
                "row_nucleus_source_role": nucleus.get("source_role"),
                "serialization_relation_candidate": nucleus.get(
                    "serialization_relation_candidate"
                ),
                "lineage_admission_status": nucleus.get("lineage_admission_status"),
                "review_reasons": list(nucleus.get("review_reasons") or []),
                "lineage_review_reasons": list(
                    nucleus.get("lineage_review_reasons") or []
                ),
                "source_refs": list(nucleus.get("source_refs") or []),
                "independent_source_vote_allowed": False,
                "row_nucleus_is_canonical_event": False,
            },
        }
        rows.append(row)
    return rows


def build_minimum_context_report(
    input_root: str | Path,
    repo_root: str | Path,
    row_nucleus_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    repo = Path(repo_root).resolve()
    mvc = _load_mvc(repo)
    admission = build_time_admission(root)

    row_nucleus_payload: dict[str, Any] | None = None
    reflection_inflation_prevented = False
    row_nucleus_candidate_count: int | None = None

    if row_nucleus_path is not None:
        row_nucleus_payload = _load_row_nucleus_payload(row_nucleus_path)
        rows = _row_nucleus_rows(row_nucleus_payload)
        rows = _normalize_rows_for_mvc(rows, admission)
        input_scope = "provider_time_admitted_row_nucleus_surface"
        reflection_inflation_prevented = True
        row_nucleus_candidate_count = len(rows)
    elif admission.get("status") == ADMITTED:
        csv_rows = [
            row for path in sorted(root.glob("*.csv")) for row in _read_csv_rows(path)
        ]
        xml_rows = [
            row
            for path in sorted(root.glob("*.xml"))
            for row in _read_xml_instance_rows(path)
        ]
        rows = _normalize_rows_for_mvc(csv_rows + xml_rows, admission)
        input_scope = "provider_time_admitted_csv_xml_surface"
    else:
        rows = mvc.discover_rows(root)
        rows = _normalize_rows_for_mvc(rows, admission)
        input_scope = "generic_surface_review_fallback"

    candidates = mvc.build_context_candidates(rows)
    summary = mvc.summarize(candidates)
    admitted = bool(candidates) and all(
        row.get("time_admission_status") == "ADMITTED" for row in candidates
    )

    row_nucleus_review_count = None
    if row_nucleus_payload is not None:
        row_nucleus_review_count = int(
            row_nucleus_payload.get("row_nucleus_review_required_count") or 0
        )

    return {
        "module_id": mvc.MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "CONTEXT_CANDIDATES_ONLY",
        "claim_safety": mvc.CLAIM_SAFETY,
        "surface_row_count": len(rows),
        "context_candidate_count": len(candidates),
        "context_candidates": candidates,
        "context_candidates_sample": candidates[:200],
        "context_summary": summary,
        "time_admission_status": "ADMITTED" if admitted else "REVIEW_REQUIRED",
        "provider_time_semantic_admission": admission,
        "context_input_scope": input_scope,
        "context_occurrence_basis": (
            "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT"
            if row_nucleus_payload is not None
            else "RAW_SURFACE_CONTEXT_CANDIDATE"
        ),
        "row_nucleus_context_binding": {
            "enabled": row_nucleus_payload is not None,
            "module_id": ROW_NUCLEUS_MODULE_ID if row_nucleus_payload is not None else None,
            "row_nucleus_candidate_count": row_nucleus_candidate_count,
            "row_nucleus_review_required_count": row_nucleus_review_count,
            "reflection_inflation_prevented": reflection_inflation_prevented,
            "dependent_reflection_adds_context_candidate": False
            if row_nucleus_payload is not None
            else None,
            "xlsx_creates_occurrence_context": False,
        },
        "reflection_inflation_prevented": reflection_inflation_prevented,
        "ordering_authority": mvc.ORDERING_AUTHORITY,
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "analyst_sentence_allowed": False,
        "claim_allowed": False,
        "production_release": False,
        "repo_root": str(repo),
    }


def write_minimum_context_with_provider_time(
    input_root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path,
    row_nucleus_path: str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    mvc = _load_mvc(repo)
    spine = mvc.spine_runner_module(repo)
    out = spine.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_minimum_context_report(
        input_root,
        repo,
        row_nucleus_path=row_nucleus_path,
    )
    json_out = out / mvc.OUTPUT_JSON
    txt_out = out / mvc.OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    txt_out.write_text(mvc.render_txt(report), encoding="utf-8")
    return report

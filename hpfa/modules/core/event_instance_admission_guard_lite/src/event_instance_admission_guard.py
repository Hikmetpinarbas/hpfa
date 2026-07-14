from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "event_instance_admission_guard_lite_v1"
OUTPUT_JSON = "event_instance_admission_guard_lite_v1.json"
OUTPUT_TXT = "event_instance_admission_guard_lite_v1.txt"

EVENT_GENERATOR_ROLE = "CSV_PRIMARY_CANONICAL_ACTION_SURFACE"
SUPPORT_ONLY_ROLES = {
    "CSV_SECONDARY_SUPPORT_SURFACE",
    "XML_CONFORMANCE_SURFACE",
    "XML_QUALIFIER_SUPPORT_SURFACE",
    "XLSX_AGGREGATE_VALIDATION_SURFACE",
    "XLSX_DERIVED_OUTPUT_SURFACE",
    "DERIVED_RUNTIME_OUTPUT",
    "REPORT_OR_VISUAL",
}
DERIVED_ROLES = {"XLSX_DERIVED_OUTPUT_SURFACE", "DERIVED_RUNTIME_OUTPUT"}
BOUNDARY_LABELS = {
    "start of the 1st half",
    "halftime",
    "start of the 2nd half",
    "end of the match",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _norm_label(value: Any) -> str:
    text = _clean(value).lower()
    out = []
    for char in text:
        out.append(char if char.isalnum() else "_")
    return "_".join(part for part in "".join(out).split("_") if part)


def _sha256(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
    return [row for row in rows if isinstance(row, dict)]


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    entries = payload.get("sources", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("invalid_source_manifest")
    return [entry for entry in entries if isinstance(entry, dict)]


def _raw_label(row: dict[str, Any]) -> str:
    return _clean(row.get("event_type_raw") or row.get("code_raw") or row.get("event_family"))


def _canonical_family(row: dict[str, Any]) -> str:
    return _clean(row.get("event_family") or "UNKNOWN_OR_OTHER")


def _team(row: dict[str, Any]) -> str:
    value = _clean(row.get("team_normalized") or row.get("team_raw"))
    if value.lower() in {"", "none", "null", "nan"}:
        return "UNKNOWN_TEAM"
    return value


def _player(row: dict[str, Any]) -> str:
    value = _clean(row.get("player_normalized") or row.get("player_raw"))
    if value.lower() in {"", "none", "null", "nan"}:
        return ""
    return value


def _period(row: dict[str, Any]) -> str:
    return _clean(row.get("period_candidate")) or "UNKNOWN_PERIOD"


def _source_row_index(row: dict[str, Any]) -> int | None:
    value = row.get("source_row_index")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_boundary_marker(row: dict[str, Any]) -> bool:
    return _raw_label(row).lower() in BOUNDARY_LABELS


def _validate_manifest(entries: list[dict[str, Any]]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    failures: list[str] = []
    by_file: dict[str, dict[str, Any]] = {}
    generators = []
    hash_to_files: dict[str, list[str]] = defaultdict(list)

    for entry in entries:
        source_file_id = _clean(entry.get("source_file_id"))
        source_file = _clean(entry.get("source_file"))
        role = _clean(entry.get("source_role"))
        match_binding = _clean(entry.get("match_binding_id"))
        target_status = _clean(entry.get("target_match_status"))
        content_hash = _clean(entry.get("source_content_hash"))
        allowed = bool(entry.get("event_generation_allowed"))

        if not source_file_id or not source_file or not role or not match_binding:
            failures.append("manifest_required_field_missing")
            continue
        if source_file in by_file:
            failures.append("duplicate_manifest_source_file")
        by_file[source_file] = entry
        if target_status != "TARGET_MATCH_CONFIRMED":
            failures.append("non_target_or_unresolved_match_binding")
        if role in DERIVED_ROLES and allowed:
            failures.append("derived_output_reingestion_attempt")
        if allowed:
            generators.append(entry)
            if role != EVENT_GENERATOR_ROLE:
                failures.append("invalid_event_generator_role")
        if content_hash:
            hash_to_files[content_hash].append(source_file)

    if len(generators) == 0:
        failures.append("no_event_generation_surface")
    elif len(generators) > 1:
        failures.append("multiple_event_generation_surfaces")

    for files in hash_to_files.values():
        if len(files) > 1:
            failures.append("duplicate_source_hash")

    return sorted(set(failures)), by_file


def build_report(canonical_json: str | Path, source_manifest_json: str | Path) -> dict[str, Any]:
    rows = load_rows(canonical_json)
    manifest = load_manifest(source_manifest_json)
    failures, manifest_by_file = _validate_manifest(manifest)

    labels: dict[tuple[str, str], dict[str, Any]] = {}
    provisional_event_candidates: list[dict[str, Any]] = []
    event_candidates: list[dict[str, Any]] = []
    support_records: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    duplicate_row_candidates: list[dict[str, Any]] = []
    fingerprint_index: dict[str, list[str]] = defaultdict(list)
    source_counts = Counter()
    unknown_label_audit_only_count = 0
    primary_identity_missing_player_count = 0
    primary_generator_row_count = 0

    for row in rows:
        source_file = _clean(row.get("source_file"))
        source_counts[source_file] += 1
        entry = manifest_by_file.get(source_file)
        raw_label = _raw_label(row)
        normalized_label = _norm_label(raw_label)
        family = _canonical_family(row)
        label_key = (_clean(entry.get("provider")) if entry else "UNKNOWN_PROVIDER", raw_label)
        reg = labels.setdefault(label_key, {
            "label_registry_id": _sha256([label_key[0], raw_label])[:24],
            "provider": label_key[0],
            "raw_label": raw_label,
            "normalized_label": normalized_label,
            "canonical_family_candidate": family,
            "qualifier_family_candidate": None,
            "event_generation_allowed": False,
            "downstream_eligibility": [],
            "source_files_seen_in": [],
            "frequency_by_source": {},
            "audit_status": "MAPPED" if family != "UNKNOWN_OR_OTHER" else "AUDIT_ONLY",
        })
        if source_file not in reg["source_files_seen_in"]:
            reg["source_files_seen_in"].append(source_file)
        reg["frequency_by_source"][source_file] = reg["frequency_by_source"].get(source_file, 0) + 1

        if entry is None:
            quarantined.append({"reason": "SOURCE_MANIFEST_MISSING", "source_file": source_file, "source_row_index": row.get("source_row_index")})
            continue

        role = _clean(entry.get("source_role"))
        if _clean(entry.get("target_match_status")) != "TARGET_MATCH_CONFIRMED":
            quarantined.append({"reason": "NON_TARGET_OR_UNRESOLVED_MATCH", "source_file": source_file, "source_row_index": row.get("source_row_index")})
            continue
        if role in DERIVED_ROLES:
            quarantined.append({"reason": "DERIVED_RAW_REINGESTION_BLOCKED", "source_file": source_file, "source_row_index": row.get("source_row_index")})
            continue
        if _is_boundary_marker(row):
            support_records.append({"support_type": "MATCH_BOUNDARY_MARKER", "source_file": source_file, "source_row_index": row.get("source_row_index"), "raw_event_label": raw_label})
            continue
        if not bool(entry.get("event_generation_allowed")):
            support_records.append({"support_type": role or "SUPPORT_ONLY", "source_file": source_file, "source_row_index": row.get("source_row_index"), "raw_event_label": raw_label, "canonical_family_candidate": family})
            continue
        if family == "UNKNOWN_OR_OTHER":
            unknown_label_audit_only_count += 1
            support_records.append({
                "support_type": "UNKNOWN_LABEL_AUDIT_ONLY",
                "source_file": source_file,
                "source_row_index": row.get("source_row_index"),
                "raw_event_label": raw_label,
                "canonical_family_candidate": family,
            })
            continue

        primary_generator_row_count += 1
        source_file_id = _clean(entry.get("source_file_id"))
        match_binding_id = _clean(entry.get("match_binding_id"))
        row_index = _source_row_index(row)
        if not source_file_id or not match_binding_id or row_index is None:
            quarantined.append({"reason": "EVENT_INSTANCE_IDENTITY_INCOMPLETE", "source_file": source_file, "source_row_index": row.get("source_row_index")})
            continue

        player = _player(row)
        if _clean(row.get("source_role")).lower() == "players" and not player:
            primary_identity_missing_player_count += 1

        candidate_id = _sha256([match_binding_id, source_file_id, str(row_index)])[:32]
        fingerprint = _sha256([
            match_binding_id,
            _team(row),
            _period(row),
            _clean(row.get("start_raw") or row.get("source_event_id_raw") or row_index),
            family,
            player,
            _clean(row.get("x_meters")),
            _clean(row.get("y_meters")),
            _clean(row.get("outcome_candidate")),
        ])
        fingerprint_index[fingerprint].append(candidate_id)
        provisional_event_candidates.append({
            "event_candidate_id": candidate_id,
            "match_binding_id": match_binding_id,
            "source_file_id": source_file_id,
            "source_file": source_file,
            "source_row_index": row_index,
            "team_or_side": _team(row),
            "player_candidate": player or None,
            "period": _period(row),
            "timestamp_or_order": row.get("start_raw") or row.get("source_event_id_raw") or row_index,
            "raw_event_label": raw_label,
            "normalized_event_label": normalized_label,
            "canonical_family_candidate": family,
            "row_fingerprint": fingerprint,
            "primary_source_role": role,
            "supporting_surfaces": [],
            "claim_safety": "PROVISIONAL_EVENT_INSTANCE_CANDIDATE_ONLY",
        })

    for fingerprint, candidate_ids in fingerprint_index.items():
        if len(candidate_ids) > 1:
            duplicate_row_candidates.append({
                "row_fingerprint": fingerprint,
                "candidate_ids": candidate_ids,
                "decision": "POSSIBLE_COLLISION_REVIEW_REQUIRED",
            })

    collision_ids = {
        candidate_id
        for item in duplicate_row_candidates
        for candidate_id in item["candidate_ids"]
    }
    collision_row_count = len(collision_ids)
    provisional_count = len(provisional_event_candidates)
    collision_ratio = round(collision_row_count / provisional_count, 6) if provisional_count else 0.0
    missing_player_ratio = (
        round(primary_identity_missing_player_count / primary_generator_row_count, 6)
        if primary_generator_row_count
        else 0.0
    )

    atomicity_reasons: list[str] = []
    if duplicate_row_candidates:
        atomicity_reasons.append("ROW_FINGERPRINT_COLLISIONS")
    if primary_identity_missing_player_count:
        atomicity_reasons.append("PRIMARY_PLAYER_BINDING_MISSING")

    manifest_decision = "PASS_EVENT_INSTANCE_ADMISSION"
    primary_surface_atomicity_status = "PASS"
    if failures:
        primary_surface_atomicity_status = "NOT_EVALUATED"
        if "multiple_event_generation_surfaces" in failures:
            manifest_decision = "BLOCK_MULTIPLE_EVENT_GENERATORS"
        elif "duplicate_source_hash" in failures:
            manifest_decision = "BLOCK_DUPLICATE_SOURCE"
        elif "derived_output_reingestion_attempt" in failures:
            manifest_decision = "BLOCK_DERIVED_RAW_REINGESTION"
        elif "non_target_or_unresolved_match_binding" in failures:
            manifest_decision = "BLOCK_NON_TARGET_MATCH"
        else:
            manifest_decision = "FAIL_CLOSED"
    elif atomicity_reasons:
        manifest_decision = "REVIEW_REQUIRED_PRIMARY_SURFACE_NOT_ATOMIC"
        primary_surface_atomicity_status = "REVIEW_REQUIRED"
    else:
        event_candidates = list(provisional_event_candidates)

    return {
        "module_id": MODULE_ID,
        "decision_state": manifest_decision,
        "manifest_failures": failures,
        "source_manifest_count": len(manifest),
        "visible_surface_row_count": len(rows),
        "primary_generator_row_count": primary_generator_row_count,
        "provisional_event_candidate_count": provisional_count,
        "admitted_event_candidate_count": len(event_candidates),
        "support_only_row_count": len(support_records),
        "quarantined_row_count": len(quarantined),
        "label_registry_count": len(labels),
        "unknown_label_audit_only_count": unknown_label_audit_only_count,
        "primary_surface_atomicity_status": primary_surface_atomicity_status,
        "primary_surface_atomicity_reasons": atomicity_reasons,
        "primary_identity_missing_player_count": primary_identity_missing_player_count,
        "primary_identity_missing_player_ratio": missing_player_ratio,
        "fingerprint_collision_group_count": len(duplicate_row_candidates),
        "fingerprint_collision_row_count": collision_row_count,
        "fingerprint_collision_row_ratio": collision_ratio,
        "event_instance_candidates": event_candidates,
        "provisional_event_instance_candidates": provisional_event_candidates,
        "label_registry": list(labels.values()),
        "support_surface_records": support_records,
        "quarantined_records": quarantined,
        "duplicate_row_candidates": duplicate_row_candidates,
        "duplicate_source_hits": [failure for failure in failures if failure == "duplicate_source_hash"],
        "source_row_counts": dict(source_counts),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "claim_boundary": "EVENT_INSTANCE_ADMISSION_AND_PRIMARY_ATOMICITY_GATE",
    }


def render_txt(report: dict[str, Any]) -> str:
    keys = [
        "decision_state",
        "source_manifest_count",
        "visible_surface_row_count",
        "primary_generator_row_count",
        "provisional_event_candidate_count",
        "admitted_event_candidate_count",
        "support_only_row_count",
        "quarantined_row_count",
        "label_registry_count",
        "unknown_label_audit_only_count",
        "primary_surface_atomicity_status",
        "primary_identity_missing_player_count",
        "primary_identity_missing_player_ratio",
        "fingerprint_collision_group_count",
        "fingerprint_collision_row_count",
        "fingerprint_collision_row_ratio",
        "canonical_event_count",
        "production_release",
    ]
    lines = ["HPFA EVENT INSTANCE ADMISSION GUARD LITE V1"]
    lines.extend(f"{key}={report[key]}" for key in keys)
    lines.append(f"manifest_failures={report['manifest_failures']}")
    lines.append(f"primary_surface_atomicity_reasons={report['primary_surface_atomicity_reasons']}")
    return "\n".join(lines) + "\n"


def write_outputs(canonical_json: str | Path, source_manifest_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if out.name != "HPFA" or out.parent.name != "Download":
        raise ValueError("nested_phone_output_directory_rejected")
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(canonical_json, source_manifest_json)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / OUTPUT_TXT).write_text(render_txt(report), encoding="utf-8")
    return report

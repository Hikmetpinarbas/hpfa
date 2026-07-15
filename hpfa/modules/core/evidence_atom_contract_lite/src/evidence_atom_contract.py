from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "evidence_atom_contract_lite_v1"
OUTPUT_JSON = "evidence_atom_contract_lite_v1.json"
OUTPUT_TXT = "evidence_atom_contract_lite_v1.txt"

BOUNDARY_LABELS = {
    "start of the 1st half",
    "halftime",
    "start of the 2nd half",
    "end of the match",
}
DERIVED_ROLES = {"DERIVED_RUNTIME_OUTPUT", "REPORT_OR_VISUAL", "XLSX_DERIVED_OUTPUT_SURFACE"}


def _raw(value: Any) -> str:
    return "" if value is None else str(value)


def _clean(value: Any) -> str:
    return " ".join(_raw(value).split()).strip()


def _normalize(value: Any) -> str:
    text = _clean(value).lower()
    tokenized = "".join(char if char.isalnum() else "_" for char in text)
    return "_".join(part for part in tokenized.split("_") if part)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _raw_label(row: dict[str, Any]) -> str:
    for key in ("event_type_raw", "action_label_candidate", "code_raw"):
        value = row.get(key)
        if _clean(value):
            return _raw(value)
    return ""


def _parse_seconds(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    parts = text.split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    if any(number < 0 for number in numbers):
        return None
    if len(numbers) == 2:
        minutes, seconds = numbers
        if seconds >= 60:
            return None
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    if minutes >= 60 or seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _time_candidate(row: dict[str, Any], explicit_key: str, raw_key: str) -> float | None:
    explicit = _parse_seconds(row.get(explicit_key))
    if explicit is not None:
        return explicit
    return _parse_seconds(row.get(raw_key))


def _stable_atom_id(match_binding_id: str, row: dict[str, Any]) -> str:
    seed = "|".join(
        [
            match_binding_id,
            _clean(row.get("source_file")),
            _clean(row.get("source_format")),
            _clean(row.get("source_role")),
            _clean(row.get("source_row_index")),
            _clean(row.get("source_event_id_raw")),
            _clean(row.get("period_candidate") or row.get("period_raw")),
            _clean(row.get("start_seconds_candidate") or row.get("start_raw")),
            _raw_label(row),
        ]
    )
    return "ea_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _atom_class(row: dict[str, Any]) -> str:
    role = _clean(row.get("source_role")).upper()
    source_format = _clean(row.get("source_format")).lower()
    row_surface_class = _clean(row.get("row_surface_class")).upper()
    raw_label = _clean(_raw_label(row)).lower()

    if role in DERIVED_ROLES:
        return "QUARANTINED_DERIVED_OUTPUT_ATOM"
    if raw_label in BOUNDARY_LABELS:
        return "MATCH_BOUNDARY_ATOM"
    if source_format == "xlsx" or row_surface_class == "AGGREGATE_VALIDATION":
        return "AGGREGATE_OUTCOME_ATOM"
    if source_format in {"csv", "xml"}:
        return "EXPLANATORY_EVIDENCE_ATOM"
    return "SUPPORT_EVIDENCE_ATOM"


def build_evidence_atom_contract(
    canonical_payload: dict[str, Any],
    *,
    match_binding_id: str = "active_single_match_current",
) -> dict[str, Any]:
    rows = canonical_payload.get("rows") or canonical_payload.get("canonical_rows") or []
    evidence_atoms: list[dict[str, Any]] = []
    missing_provenance_rows: list[int] = []
    unparsed_time_rows: list[int] = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        provenance_complete = bool(
            _clean(row.get("source_file"))
            and _clean(row.get("source_format"))
            and _clean(row.get("source_role"))
            and row.get("source_row_index") is not None
        )
        if not provenance_complete:
            missing_provenance_rows.append(index)

        start_seconds = _time_candidate(row, "start_seconds_candidate", "start_raw")
        end_seconds = _time_candidate(row, "end_seconds_candidate", "end_raw")
        atom_class = _atom_class(row)
        if atom_class == "EXPLANATORY_EVIDENCE_ATOM" and (
            (_clean(row.get("start_raw")) and start_seconds is None)
            or (_clean(row.get("end_raw")) and end_seconds is None)
        ):
            unparsed_time_rows.append(index)

        raw_label = _raw_label(row)
        evidence_atoms.append(
            {
                "evidence_atom_id": _stable_atom_id(match_binding_id, row),
                "match_binding_id": match_binding_id,
                "source_file": row.get("source_file"),
                "source_format": row.get("source_format"),
                "source_role": row.get("source_role"),
                "source_row_index": row.get("source_row_index"),
                "source_event_id_raw": row.get("source_event_id_raw"),
                "atom_class": atom_class,
                "raw_label": raw_label,
                "normalized_label": _normalize(raw_label),
                "period_raw": row.get("period_raw"),
                "period_candidate": row.get("period_candidate"),
                "start_raw": row.get("start_raw"),
                "end_raw": row.get("end_raw"),
                "start_seconds_candidate": start_seconds,
                "end_seconds_candidate": end_seconds,
                "duration_seconds_candidate": row.get("duration_seconds_candidate"),
                "x_meters": row.get("x_meters"),
                "y_meters": row.get("y_meters"),
                "team_raw": row.get("team_raw"),
                "player_raw": row.get("player_raw"),
                "code_raw": row.get("code_raw"),
                "source_labels_raw": row.get("source_labels_raw"),
                "source_extra_fields": row.get("source_extra_fields"),
                "event_instance_allowed": False,
                "claim_ceiling": "EVIDENCE_ATOM_ONLY",
            }
        )

    atom_class_counts = Counter(atom["atom_class"] for atom in evidence_atoms)
    decision_state = "PASS_EVIDENCE_ATOM_CONTRACT"
    if missing_provenance_rows:
        decision_state = "REVIEW_REQUIRED_PROVENANCE_GAP"
    elif unparsed_time_rows:
        decision_state = "REVIEW_REQUIRED_TIME_PARSE_GAP"
    return {
        "module_id": MODULE_ID,
        "input_sha256": _canonical_sha256(canonical_payload),
        "decision_state": decision_state,
        "evidence_atoms": evidence_atoms,
        "evidence_atom_count": len(evidence_atoms),
        "identity_bound_atom_count": 0,
        "semantic_role_counts": {},
        "action_bundle_candidate_count": 0,
        "unresolved_atom_count": len(evidence_atoms),
        "source_provenance_complete": not missing_provenance_rows,
        "missing_provenance_rows": missing_provenance_rows,
        "unparsed_time_rows": unparsed_time_rows,
        "atom_class_counts": dict(sorted(atom_class_counts.items())),
        "event_instance_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def write_outputs(canonical_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(out_dir)
    if output_dir.name != "HPFA" or "HPFA" in output_dir.parts[:-1]:
        raise ValueError("nested_phone_output_directory_rejected")
    payload = json.loads(Path(canonical_json).read_text(encoding="utf-8"))
    result = build_evidence_atom_contract(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / OUTPUT_TXT).write_text(
        "\n".join(
            [
                "HPFA EVIDENCE ATOM CONTRACT LITE V1",
                f"decision_state={result['decision_state']}",
                f"input_sha256={result['input_sha256']}",
                f"evidence_atom_count={result['evidence_atom_count']}",
                f"unparsed_time_row_count={len(result['unparsed_time_rows'])}",
                "event_instance_count=0",
                "canonical_event_count=UNKNOWN",
                "production_release=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return result

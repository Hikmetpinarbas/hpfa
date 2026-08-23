from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hpfa.modules.core.triangulated_event_reflection_resolver_lite.src import (
    triangulated_event_reflection_resolver as reflection,
)

MODULE_ID = "row_nucleus_inventory_lite_v1"
CLAIM_SAFETY = "ROW_NUCLEUS_LINEAGE_CANDIDATE_ONLY"
OUTPUT_JSON = "row_nucleus_inventory_lite_v1.json"
OUTPUT_TXT = "row_nucleus_inventory_lite_v1.txt"
ANALYST_TXT = "row_nucleus_inventory_analyst_audit_v1.txt"
ROLLUP_JSON = "g01_g18_data_quality_rollup_v1.json"
ROLLUP_TXT = "g01_g18_data_quality_rollup_v1.txt"

VISIBLE_FIELDS = ("start", "end", "code", "team", "action", "half", "pos_x", "pos_y")
REQUIRED_VISIBLE_FIELDS = ("start", "end", "action", "half")
COORDINATE_FIELDS = ("pos_x", "pos_y")
ROLE_PROJECTION = {
    "PLAYER": "PLAYER_ACTOR_CANDIDATE",
    "GOALKEEPER": "GOALKEEPER_REACTION_ACTOR_CANDIDATE",
    "TEAM": "TEAM_CONTEXT_CANDIDATE",
}
BLOCKED_CLAIMS = (
    "canonical event identity",
    "physical action identity",
    "same upstream origin truth",
    "independent CSV/XML vote",
    "true action count",
    "sequence truth",
    "possession truth",
    "phase truth",
    "tactical truth",
)


def stable_id(*parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _format(row: dict[str, Any]) -> str:
    return str(row.get("_source_format") or "").casefold()


def _source_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_file": row.get("_source_file"),
        "source_format": _format(row),
        "source_role": row.get("_source_role"),
        "source_row_index": row.get("_source_row_index"),
    }


def _candidate_values(rows: list[dict[str, Any]], field: str) -> list[str]:
    return sorted({str(row.get(field, "")) for row in rows if str(row.get(field, "")) != ""})


def _resolved(rows: list[dict[str, Any]], field: str) -> str | None:
    values = _candidate_values(rows, field)
    return values[0] if len(values) == 1 else None


def _missing_key(row: dict[str, Any]) -> str:
    return "__MISSING__:" + stable_id(
        row.get("_source_role"),
        row.get("_source_format"),
        row.get("_source_file"),
        row.get("_source_row_index"),
    )[:20]


def _mismatch_fields(csv_row: dict[str, Any], xml_row: dict[str, Any]) -> list[str]:
    fields = ("provider_row_id", *VISIBLE_FIELDS)
    return [field for field in fields if str(csv_row.get(field, "")) != str(xml_row.get(field, ""))]


def _lineage_for(rows: list[dict[str, Any]]) -> tuple[str, str, list[str], list[str]]:
    by_format: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_format[_format(row)].append(row)

    reasons: list[str] = []
    mismatch_fields: list[str] = []
    csv_rows = by_format.get("csv", []) + by_format.get("tsv", [])
    xml_rows = by_format.get("xml", [])

    duplicate_serializations = {
        fmt: len(items) for fmt, items in by_format.items() if len(items) > 1
    }
    if duplicate_serializations:
        reasons.append("duplicate_provider_row_id_within_serialization")

    if len(csv_rows) == 1 and len(xml_rows) == 1:
        mismatch_fields = _mismatch_fields(csv_rows[0], xml_rows[0])
        if not mismatch_fields and not duplicate_serializations:
            return (
                "REFLECTION_CANDIDATE_EXACT",
                "CANDIDATE_EXACT_VISIBLE_FIELDS",
                reasons,
                mismatch_fields,
            )
        reasons.append("visible_field_serialization_discrepancy")
        return (
            "REFLECTION_CANDIDATE_DISCREPANCY",
            "LINEAGE_REVIEW_REQUIRED",
            sorted(set(reasons)),
            mismatch_fields,
        )

    if not csv_rows or not xml_rows:
        reasons.append("single_serialization_only")
    else:
        reasons.append("serialization_pairing_not_one_to_one")
    return (
        "REFLECTION_CANDIDATE_UNRESOLVED",
        "LINEAGE_REVIEW_REQUIRED",
        sorted(set(reasons)),
        mismatch_fields,
    )


def build_nuclei(input_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    unique_files, duplicate_reflections = reflection.discover_unique_surface_files(input_dir)
    surface_rows = [row for path in unique_files for row in reflection.read_surface(path)]

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_provider_id_rows = 0
    for row in surface_rows:
        role = str(row.get("_source_role") or "UNKNOWN")
        provider_id = str(row.get("provider_row_id") or "")
        if not provider_id:
            missing_provider_id_rows += 1
            provider_id = _missing_key(row)
        grouped[(role, provider_id)].append(row)

    nuclei: list[dict[str, Any]] = []
    for (role, provider_id), rows in sorted(grouped.items()):
        relation, lineage_admission, lineage_reasons, mismatch_fields = _lineage_for(rows)
        visible_candidates = {
            field: _candidate_values(rows, field) for field in VISIBLE_FIELDS
        }
        resolved_fields = {
            field: _resolved(rows, field) for field in VISIBLE_FIELDS
        }

        review_reasons = list(lineage_reasons)
        if provider_id.startswith("__MISSING__:"):
            review_reasons.append("provider_row_id_missing")

        missing_required = [
            field for field in REQUIRED_VISIBLE_FIELDS if resolved_fields[field] is None
        ]
        if missing_required:
            review_reasons.append("required_visible_field_unresolved")

        missing_coordinates = [
            field for field in COORDINATE_FIELDS if resolved_fields[field] is None
        ]
        if missing_coordinates:
            # No current reviewed semantic-role producer is stacked here. Therefore no
            # administrative coordinate exemption may be inferred at this layer.
            review_reasons.append("coordinate_surface_unresolved_no_explicit_admin_exemption")

        projection = ROLE_PROJECTION.get(role, "UNKNOWN_ROLE_CANDIDATE")
        if role not in ROLE_PROJECTION:
            review_reasons.append("source_role_unrecognized")

        status = "REVIEW_REQUIRED" if review_reasons else "PASS"
        source_formats = sorted({_format(row) for row in rows})
        nuclei.append(
            {
                "row_nucleus_candidate_id": stable_id(
                    "row_nucleus_candidate_v1", role, provider_id
                ),
                "status": status,
                "source_role": role,
                "role_projection_candidate": projection,
                "provider_row_id_candidate": provider_id,
                "provider_row_id_is_validated_identity": False,
                "serialization_family_candidates": source_formats,
                "serialization_relation_candidate": relation,
                "independence_status": "INDEPENDENCE_UNRESOLVED",
                "lineage_admission_status": lineage_admission,
                "lineage_review_reasons": sorted(set(lineage_reasons)),
                "review_reasons": sorted(set(review_reasons)),
                "mismatch_fields": mismatch_fields,
                "visible_field_candidates": visible_candidates,
                "resolved_visible_fields": resolved_fields,
                "missing_required_visible_fields": missing_required,
                "missing_coordinate_fields": missing_coordinates,
                "source_refs": [_source_ref(row) for row in rows],
                "source_timeline_evidence_only": True,
                "row_nucleus_is_canonical_event": False,
                "physical_action_identity_truth": False,
                "validated_event_identity": False,
                "independent_source_vote_allowed": False,
            }
        )

    root = Path(input_dir).expanduser().resolve(strict=False)
    xlsx_file_count = sum(
        1 for path in (root.iterdir() if root.exists() else []) if path.suffix.casefold() == ".xlsx"
    )
    stats = {
        "unique_surface_file_count": len(unique_files),
        "duplicate_surface_file_reflection_count": len(duplicate_reflections),
        "surface_row_count": len(surface_rows),
        "missing_provider_id_surface_row_count": missing_provider_id_rows,
        "xlsx_file_count": xlsx_file_count,
        "xlsx_used_for_row_nucleus_identity": False,
    }
    return nuclei, stats


def build_rollup(nuclei: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    missing_ids = sum(
        1 for item in nuclei if "provider_row_id_missing" in item.get("review_reasons", [])
    )
    required_unresolved = sum(
        1 for item in nuclei if item.get("missing_required_visible_fields")
    )
    coordinate_unresolved = sum(
        1 for item in nuclei if item.get("missing_coordinate_fields")
    )
    lineage_review = sum(
        1 for item in nuclei if item.get("lineage_admission_status") == "LINEAGE_REVIEW_REQUIRED"
    )
    unknown_roles = sum(
        1 for item in nuclei if item.get("source_role") not in ROLE_PROJECTION
    )
    duplicate_id_review = sum(
        1
        for item in nuclei
        if "duplicate_provider_row_id_within_serialization" in item.get("review_reasons", [])
    )

    def gate(gate_id: str, name: str, status: str, evidence: dict[str, Any], message: str) -> dict[str, Any]:
        return {
            "gate_id": gate_id,
            "name": name,
            "status": status,
            "evidence": evidence,
            "message": message,
        }

    gates = [
        gate("G01", "surface_lineage_presence", "PASS" if nuclei else "FAIL_CLOSED",
             {"row_nucleus_candidate_count": len(nuclei)}, "Visible row-nucleus candidate surface exists."),
        gate("G02", "provider_row_id_candidate_integrity", "REVIEW_REQUIRED" if (missing_ids or duplicate_id_review) else "PASS",
             {"missing_id_nucleus_count": missing_ids, "duplicate_id_review_nucleus_count": duplicate_id_review},
             "Provider row IDs remain representation-preserving match-local candidates."),
        gate("G03", "required_visible_field_readiness", "REVIEW_REQUIRED" if required_unresolved else "PASS",
             {"required_field_unresolved_nucleus_count": required_unresolved},
             "Required visible fields are checked without creating event truth."),
        gate("G04", "source_timeline_surface", "REVIEW_REQUIRED" if required_unresolved else "PASS",
             {"physical_action_duration_truth": False},
             "start/end remain source-timeline evidence, not physical action duration."),
        gate("G05", "source_role_isolation", "FAIL_CLOSED" if unknown_roles else "PASS",
             {"unknown_source_role_nucleus_count": unknown_roles},
             "PLAYER/GOALKEEPER/TEAM roles are projected asymmetrically and never fused here."),
        gate("G06", "duplicate_reflection_control", "PASS",
             {"duplicate_surface_file_reflection_count": stats["duplicate_surface_file_reflection_count"]},
             "Exact duplicate file reflections do not create additional surface rows or nuclei."),
        gate("G07", "coordinate_surface_eligibility", "REVIEW_REQUIRED" if coordinate_unresolved else "PASS",
             {"coordinate_unresolved_nucleus_count": coordinate_unresolved, "admin_exemption_admitted": False},
             "No coordinate exemption is inferred without an explicit reviewed administrative semantic role."),
        gate("G08", "physical_action_identity", "NOT_APPLICABLE",
             {"physical_action_identity_truth": False}, "Physical action identity belongs to a later bundle layer."),
        gate("G09", "serialization_lineage_readiness", "REVIEW_REQUIRED" if lineage_review else "PASS",
             {"lineage_review_nucleus_count": lineage_review},
             "CSV/XML discrepancy or incomplete pairing remains review-required."),
        gate("G10", "role_asymmetric_projection", "FAIL_CLOSED" if unknown_roles else "PASS",
             {"typed_projection_count": len(nuclei) - unknown_roles},
             "TEAM is context; PLAYER and GOALKEEPER remain distinct actor/reaction candidates."),
        gate("G11", "provider_semantic_admission", "NOT_APPLICABLE", {},
             "Provider semantic admission is not performed by Row Nucleus."),
        gate("G12", "semantic_role_readiness", "NOT_APPLICABLE", {},
             "Semantic-role routing is downstream and cannot be inferred here."),
        gate("G13", "action_family_ambiguity", "NOT_APPLICABLE", {},
             "Action-family resolution is downstream."),
        gate("G14", "action_bundle_readiness", "NOT_APPLICABLE", {},
             "Multi-label on-ball action bundling is downstream."),
        gate("G15", "xlsx_identity_exclusion", "PASS",
             {"xlsx_file_count": stats["xlsx_file_count"], "xlsx_used_for_row_nucleus_identity": False},
             "XLSX remains aggregate/reconciliation support and never row identity."),
        gate("G16", "aggregate_definition_dependency", "NOT_APPLICABLE", {},
             "Aggregate-definition admission is not required to construct row-nucleus candidates."),
        gate("G17", "canonical_event_admission", "NOT_APPLICABLE",
             {"canonical_event_count": "UNKNOWN"}, "Row nuclei do not admit canonical events."),
        gate("G18", "claim_release", "NOT_APPLICABLE",
             {"production_release": False}, "No football claim or production release is opened."),
    ]
    states = [item["status"] for item in gates]
    overall = (
        "FAIL_CLOSED"
        if "FAIL_CLOSED" in states
        else ("REVIEW_REQUIRED" if "REVIEW_REQUIRED" in states else "PASS")
    )
    return {
        "status": overall,
        "gates": gates,
        "pass_count": states.count("PASS"),
        "review_required_count": states.count("REVIEW_REQUIRED"),
        "fail_closed_count": states.count("FAIL_CLOSED"),
        "not_applicable_count": states.count("NOT_APPLICABLE"),
    }


def build_report(input_dir: str | Path) -> dict[str, Any]:
    nuclei, stats = build_nuclei(input_dir)
    rollup = build_rollup(nuclei, stats)
    pass_count = sum(1 for item in nuclei if item["status"] == "PASS")
    review_count = sum(1 for item in nuclei if item["status"] == "REVIEW_REQUIRED")
    relation_counts = Counter(item["serialization_relation_candidate"] for item in nuclei)
    role_counts = Counter(item["source_role"] for item in nuclei)

    return {
        "module_id": MODULE_ID,
        "status": rollup["status"],
        "module_status": rollup["status"],
        "claim_safety": CLAIM_SAFETY,
        **stats,
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_pass_count": pass_count,
        "row_nucleus_review_required_count": review_count,
        "source_role_candidate_counts": dict(sorted(role_counts.items())),
        "serialization_relation_candidate_counts": dict(sorted(relation_counts.items())),
        "g01_g18_rollup": rollup,
        "row_nuclei": nuclei,
        "blocked_claims": list(BLOCKED_CLAIMS),
        "provider_row_id_policy": "TEXT_CANDIDATE_NO_NUMERIC_CANONICALIZATION",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "row_nucleus_is_canonical_event": False,
        "physical_action_identity_truth": False,
        "same_upstream_origin_truth": False,
        "independent_source_vote_allowed": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "production_release": False,
    }


def _rollup_text(rollup: dict[str, Any]) -> str:
    lines = [
        f"status={rollup.get('status')}",
        f"pass_count={rollup.get('pass_count')}",
        f"review_required_count={rollup.get('review_required_count')}",
        f"fail_closed_count={rollup.get('fail_closed_count')}",
        f"not_applicable_count={rollup.get('not_applicable_count')}",
        "",
    ]
    for item in rollup.get("gates", []):
        lines.append(f"{item['gate_id']}\t{item['status']}\t{item['name']}\t{item['message']}")
    return "\n".join(lines) + "\n"


def _summary_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"module_id={report['module_id']}",
            f"status={report['status']}",
            f"row_nucleus_candidate_count={report['row_nucleus_candidate_count']}",
            f"row_nucleus_pass_count={report['row_nucleus_pass_count']}",
            f"row_nucleus_review_required_count={report['row_nucleus_review_required_count']}",
            f"surface_row_count={report['surface_row_count']}",
            f"duplicate_surface_file_reflection_count={report['duplicate_surface_file_reflection_count']}",
            f"provider_row_id_policy={report['provider_row_id_policy']}",
            f"canonical_event_count={report['canonical_event_count']}",
            f"true_action_count={report['true_action_count']}",
            "production_release=false",
            "",
        ]
    )


def _analyst_text(report: dict[str, Any]) -> str:
    relation = report.get("serialization_relation_candidate_counts", {})
    roles = report.get("source_role_candidate_counts", {})
    return "\n".join(
        [
            "HPFA Row Nucleus Analyst Audit V1",
            "=================================",
            f"visible row-nucleus candidates={report['row_nucleus_candidate_count']}",
            f"role projection candidates={json.dumps(roles, ensure_ascii=False, sort_keys=True)}",
            f"serialization relation candidates={json.dumps(relation, ensure_ascii=False, sort_keys=True)}",
            "",
            "Safe meaning:",
            "Rows are grouped only as match-local same-role provider-row candidates.",
            "CSV/XML support is not an independent vote and does not establish a physical action.",
            "TEAM rows remain context candidates; PLAYER and GOALKEEPER routes remain distinct.",
            "start/end remain source-timeline evidence only.",
            "XLSX is excluded from row identity.",
            "canonical_event_count=UNKNOWN",
            "",
        ]
    )


def write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir)
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
        "rollup_json": str(output / ROLLUP_JSON),
        "rollup_txt": str(output / ROLLUP_TXT),
    }
    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / OUTPUT_TXT).write_text(_summary_text(report), encoding="utf-8")
    (output / ANALYST_TXT).write_text(_analyst_text(report), encoding="utf-8")
    rollup = report["g01_g18_rollup"]
    (output / ROLLUP_JSON).write_text(
        json.dumps(rollup, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / ROLLUP_TXT).write_text(_rollup_text(rollup), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "row_nucleus_candidate_count": report["row_nucleus_candidate_count"],
                "row_nucleus_pass_count": report["row_nucleus_pass_count"],
                "row_nucleus_review_required_count": report["row_nucleus_review_required_count"],
                "canonical_event_count": report["canonical_event_count"],
                "production_release": report["production_release"],
                "outputs": report["outputs"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

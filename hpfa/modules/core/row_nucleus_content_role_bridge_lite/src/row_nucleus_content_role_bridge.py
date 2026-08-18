from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as role_resolver,
)
from hpfa.modules.core.row_nucleus_inventory_lite.src import (
    row_nucleus_inventory as nucleus,
)
from hpfa.modules.core.triangulated_event_reflection_resolver_lite.src import (
    triangulated_event_reflection_resolver as reflection,
)

MODULE_ID = "row_nucleus_content_role_bridge_lite_v1"
CLAIM_SAFETY = "CONTENT_RESOLVED_ROW_NUCLEUS_CANDIDATE_ONLY"
OUTPUT_JSON = "role_resolved_row_nucleus_inventory_lite_v1.json"
OUTPUT_TXT = "role_resolved_row_nucleus_inventory_lite_v1.txt"
ANALYST_TXT = "role_resolved_row_nucleus_analyst_audit_v1.txt"
ROW_EXTENSIONS = frozenset({".csv", ".tsv", ".xml"})


def role_map_from_report(report: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    role_map: dict[str, str] = {}
    applicable: list[str] = []
    for record in report.get("files", []) or []:
        extension = str(record.get("extension") or "").casefold()
        if extension not in ROW_EXTENSIONS:
            continue
        relative_path = str(record.get("relative_path") or "")
        applicable.append(relative_path)
        resolution = record.get("resolution") or {}
        role = str(resolution.get("resolved_short_role") or "")
        if (
            resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED"
            and role in nucleus.ROLE_PROJECTION
        ):
            role_map[relative_path] = role
    missing = sorted(set(applicable) - set(role_map))
    return role_map, missing


def _role_resolved_surface_rows(
    input_dir: str | Path,
    role_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    unique_files, duplicate_reflections = reflection.discover_unique_surface_files(root)
    surface_rows: list[dict[str, Any]] = []
    missing_role_files: list[str] = []
    override_files = 0

    for path in unique_files:
        if path.suffix.casefold() not in ROW_EXTENSIONS:
            continue
        relative_path = path.relative_to(root).as_posix()
        role = role_map.get(relative_path)
        if role not in nucleus.ROLE_PROJECTION:
            missing_role_files.append(relative_path)
            continue
        override_files += 1
        for raw in reflection.read_surface(path):
            row = dict(raw)
            row["_source_role"] = role
            row["_source_role_resolution_authority"] = role_resolver.MODULE_ID
            row["_filename_role_used_for_nucleus_grouping"] = False
            surface_rows.append(row)

    xlsx_file_count = sum(
        1
        for path in (root.iterdir() if root.exists() else [])
        if path.suffix.casefold() == ".xlsx"
    )
    stats = {
        "unique_surface_file_count": len(unique_files),
        "duplicate_surface_file_reflection_count": len(duplicate_reflections),
        "surface_row_count": len(surface_rows),
        "xlsx_file_count": xlsx_file_count,
        "xlsx_used_for_row_nucleus_identity": False,
        "source_role_override_applied_surface_file_count": override_files,
        "source_role_override_missing_surface_file_count": len(missing_role_files),
        "filename_role_used_for_nucleus_grouping": False,
    }
    return surface_rows, stats, sorted(missing_role_files)


def _build_nuclei_from_rows(
    surface_rows: list[dict[str, Any]],
    stats: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_provider_id_rows = 0
    for row in surface_rows:
        role = str(row.get("_source_role") or "UNKNOWN")
        provider_id = str(row.get("provider_row_id") or "")
        if not provider_id:
            missing_provider_id_rows += 1
            provider_id = nucleus._missing_key(row)
        grouped[(role, provider_id)].append(row)

    nuclei: list[dict[str, Any]] = []
    for (role, provider_id), rows in sorted(grouped.items()):
        relation, lineage_admission, lineage_reasons, mismatch_fields = nucleus._lineage_for(rows)
        visible_candidates = {
            field: nucleus._candidate_values(rows, field)
            for field in nucleus.VISIBLE_FIELDS
        }
        resolved_fields = {
            field: nucleus._resolved(rows, field)
            for field in nucleus.VISIBLE_FIELDS
        }

        review_reasons = list(lineage_reasons)
        if provider_id.startswith("__MISSING__:"):
            review_reasons.append("provider_row_id_missing")

        missing_required = [
            field
            for field in nucleus.REQUIRED_VISIBLE_FIELDS
            if resolved_fields[field] is None
        ]
        if missing_required:
            review_reasons.append("required_visible_field_unresolved")

        missing_coordinates = [
            field
            for field in nucleus.COORDINATE_FIELDS
            if resolved_fields[field] is None
        ]
        if missing_coordinates:
            review_reasons.append(
                "coordinate_surface_unresolved_no_explicit_admin_exemption"
            )

        projection = nucleus.ROLE_PROJECTION.get(role, "UNKNOWN_ROLE_CANDIDATE")
        if role not in nucleus.ROLE_PROJECTION:
            review_reasons.append("source_role_unrecognized")

        status = "REVIEW_REQUIRED" if review_reasons else "PASS"
        nuclei.append(
            {
                "row_nucleus_candidate_id": nucleus.stable_id(
                    "content_role_row_nucleus_candidate_v1", role, provider_id
                ),
                "status": status,
                "source_role": role,
                "role_projection_candidate": projection,
                "provider_row_id_candidate": provider_id,
                "provider_row_id_is_validated_identity": False,
                "serialization_family_candidates": sorted(
                    {nucleus._format(row) for row in rows}
                ),
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
                "source_refs": [nucleus._source_ref(row) for row in rows],
                "source_role_resolution_authority": role_resolver.MODULE_ID,
                "filename_role_used_for_nucleus_grouping": False,
                "source_timeline_evidence_only": True,
                "row_nucleus_is_canonical_event": False,
                "physical_action_identity_truth": False,
                "validated_event_identity": False,
                "independent_source_vote_allowed": False,
            }
        )

    result_stats = dict(stats)
    result_stats["missing_provider_id_surface_row_count"] = missing_provider_id_rows
    return nuclei, result_stats


def build_report(
    input_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    role_report = role_resolver.build_report(input_dir, root=root)
    role_map, unresolved_role_files = role_map_from_report(role_report)

    if role_report.get("status") == "FAIL_CLOSED":
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "content_role_resolution_status": role_report.get("status"),
            "hard_block_hits": list(role_report.get("hard_block_hits") or []),
            "row_nuclei": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    if role_report.get("status") != "PASS" or unresolved_role_files:
        return {
            "module_id": MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "module_status": "REVIEW_REQUIRED",
            "content_role_resolution_status": role_report.get("status"),
            "unresolved_role_files": unresolved_role_files,
            "hard_block_hits": [],
            "row_nuclei": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "filename_role_used_for_nucleus_grouping": False,
            "production_release": False,
        }

    surface_rows, stats, missing_role_files = _role_resolved_surface_rows(
        input_dir, role_map
    )
    if missing_role_files:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "content_role_resolution_status": role_report.get("status"),
            "hard_block_hits": ["resolved_role_map_runtime_drift"],
            "missing_role_files": missing_role_files,
            "row_nuclei": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    nuclei, stats = _build_nuclei_from_rows(surface_rows, stats)
    rollup = nucleus.build_rollup(nuclei, stats)
    relation_counts = Counter(
        item["serialization_relation_candidate"] for item in nuclei
    )
    role_counts = Counter(item["source_role"] for item in nuclei)

    return {
        "module_id": MODULE_ID,
        "status": rollup["status"],
        "module_status": rollup["status"],
        "claim_safety": CLAIM_SAFETY,
        "content_role_resolution_status": role_report.get("status"),
        "content_role_resolution_module": role_resolver.MODULE_ID,
        **stats,
        "resolved_role_override_file_count": len(role_map),
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_pass_count": sum(
            item["status"] == "PASS" for item in nuclei
        ),
        "row_nucleus_review_required_count": sum(
            item["status"] == "REVIEW_REQUIRED" for item in nuclei
        ),
        "source_role_candidate_counts": dict(sorted(role_counts.items())),
        "serialization_relation_candidate_counts": dict(sorted(relation_counts.items())),
        "g01_g18_rollup": rollup,
        "row_nuclei": nuclei,
        "hard_block_hits": [],
        "filename_role_used_for_nucleus_grouping": False,
        "provider_row_id_policy": "TEXT_CANDIDATE_NO_NUMERIC_CANONICALIZATION",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "row_nucleus_is_canonical_event": False,
        "physical_action_identity_truth": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "production_release": False,
    }


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    output = nucleus.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=root)
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
    }
    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "HPFA ROW NUCLEUS CONTENT ROLE BRIDGE LITE V1",
        f"status={report.get('status')}",
        f"content_role_resolution_status={report.get('content_role_resolution_status')}",
        f"row_nucleus_candidate_count={report.get('row_nucleus_candidate_count', 0)}",
        f"row_nucleus_pass_count={report.get('row_nucleus_pass_count', 0)}",
        f"row_nucleus_review_required_count={report.get('row_nucleus_review_required_count', 0)}",
        f"filename_role_used_for_nucleus_grouping={report.get('filename_role_used_for_nucleus_grouping', False)}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    (output / OUTPUT_TXT).write_text("\n".join(summary) + "\n", encoding="utf-8")
    analyst = [
        "HPFA ROW NUCLEUS CONTENT ROLE ANALYST AUDIT V1",
        f"status={report.get('status')}",
        "Content-admitted source-role candidates override filename-derived role hints before row-nucleus grouping.",
        "TEAM remains context; PLAYER and GOALKEEPER remain distinct candidate routes.",
        "No row nucleus is promoted to a canonical event or physical action.",
        "canonical_event_count=UNKNOWN",
    ]
    (output / ANALYST_TXT).write_text("\n".join(analyst) + "\n", encoding="utf-8")
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
                "status": report.get("status"),
                "row_nucleus_candidate_count": report.get(
                    "row_nucleus_candidate_count", 0
                ),
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

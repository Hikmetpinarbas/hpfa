from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

import cross_format_reconciliation as core
from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as role_resolver,
)

_CORE_NORM_FIELD = core.norm_field
_CORE_BUILD_RECONCILIATION = core.build_reconciliation
_MISSING_IDENTIFIER_TOKENS = {"none", "null", "nan", "n/a", "na", "-"}
_SUPERSEDED_INTERMEDIATE_ROLE_REASONS = {"CONTENT_ROLE_EVIDENCE_INSUFFICIENT"}
_POSITIVE_RELATIONAL_ROLE_REASONS = {
    "AGGREGATE_SEMANTIC_UNIQUE_BEST_SUPPORT",
    "CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT",
}


def normalize_identifier_candidate(value: Any) -> str | None:
    """Preserve provider identifier representation until namespace semantics are admitted."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in _MISSING_IDENTIFIER_TOKENS:
        return None
    return text


def runtime_norm_field(field: str, value: Any) -> str | None:
    if field == "id":
        return normalize_identifier_candidate(value)
    return _CORE_NORM_FIELD(field, value)


def admitted_role_reasons(resolution: dict[str, Any]) -> list[str]:
    """Drop only superseded intermediate insufficiency after positive relational admission."""
    reasons = {str(value) for value in resolution.get("resolution_reasons", []) or []}
    if (
        resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED"
        and reasons & _POSITIVE_RELATIONAL_ROLE_REASONS
    ):
        reasons -= _SUPERSEDED_INTERMEDIATE_ROLE_REASONS
    return sorted(reasons)


def _role_resolution_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for record in report.get("files", []) or []:
        resolution = record.get("resolution") or {}
        relative = str(record.get("relative_path") or "")
        if (
            relative
            and resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED"
            and resolution.get("resolved_source_role")
        ):
            resolved[relative] = resolution
    return resolved


def _overlay_resolved_roles(
    payload: dict[str, Any],
    role_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    for row in result.get("files", []) or []:
        relative = str(row.get("relative_path") or row.get("file_name") or "")
        resolution = role_index.get(relative)
        if not resolution:
            continue
        row["inventory_source_role"] = row.get("source_role")
        row["source_role"] = resolution.get("resolved_source_role")
        row["source_role_resolution_status"] = resolution.get("resolution_status")
        row["source_role_resolution_reasons"] = admitted_role_reasons(resolution)
        row["filename_support_used_for_role_admission"] = False
    return result


def _attach_role_bridge_audit(
    result: dict[str, Any],
    report: dict[str, Any] | None,
    *,
    bridge_status: str,
    hard_block: str | None = None,
) -> dict[str, Any]:
    report = report or {}
    result["content_source_role_bridge"] = {
        "module_id": "content_source_role_resolver_lite_v1",
        "status": bridge_status,
        "role_resolution_applicable_file_count": report.get(
            "role_resolution_applicable_file_count"
        ),
        "role_candidate_admitted_file_count": report.get(
            "role_candidate_admitted_file_count"
        ),
        "unresolved_role_file_count": report.get("unresolved_role_file_count"),
        "resolved_role_counts": report.get("resolved_role_counts") or {},
        "filename_support_used_for_admission": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": "SOURCE_ROLE_CANDIDATE_ONLY",
    }
    if hard_block:
        blocks = list(result.get("hard_block_hits") or [])
        blocks.append(hard_block)
        result["hard_block_hits"] = sorted(set(str(value) for value in blocks))
        result["status"] = "FAIL_CLOSED"
        result["module_status"] = "FAIL_CLOSED"
        result["fusion_admissibility"] = "BLOCKED"
        result["active_match_evidence_pass"] = False
        result["runtime_evidence_status"] = "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"
    return result


def runtime_build_reconciliation(
    input_root: str | Path,
    inventory: dict[str, Any],
    csv_payload: dict[str, Any],
    xlsx_payload: dict[str, Any],
    xml_payload: dict[str, Any],
    field_semantics_payload: dict[str, Any],
    label_semantics_payload: dict[str, Any],
    xml_group_registry: dict[str, Any],
) -> dict[str, Any]:
    try:
        role_report = role_resolver.build_report(input_root, root=ROOT)
    except Exception:
        result = _CORE_BUILD_RECONCILIATION(
            input_root,
            inventory,
            csv_payload,
            xlsx_payload,
            xml_payload,
            field_semantics_payload,
            label_semantics_payload,
            xml_group_registry,
        )
        return _attach_role_bridge_audit(
            result,
            None,
            bridge_status="FAIL_CLOSED",
            hard_block="content_source_role_resolution_bridge_failed",
        )

    applicable = int(role_report.get("role_resolution_applicable_file_count") or 0)
    admitted = int(role_report.get("role_candidate_admitted_file_count") or 0)
    unresolved = int(role_report.get("unresolved_role_file_count") or 0)
    bridge_pass = (
        role_report.get("status") == "PASS"
        and not (role_report.get("hard_block_hits") or [])
        and applicable > 0
        and admitted == applicable
        and unresolved == 0
    )
    if not bridge_pass:
        result = _CORE_BUILD_RECONCILIATION(
            input_root,
            inventory,
            csv_payload,
            xlsx_payload,
            xml_payload,
            field_semantics_payload,
            label_semantics_payload,
            xml_group_registry,
        )
        return _attach_role_bridge_audit(
            result,
            role_report,
            bridge_status="FAIL_CLOSED",
            hard_block="content_source_role_resolution_gate_not_pass",
        )

    role_index = _role_resolution_index(role_report)
    resolved_inventory = role_resolver.resolved_inventory(role_report, inventory)
    resolved_csv = _overlay_resolved_roles(csv_payload, role_index)
    resolved_xlsx = _overlay_resolved_roles(xlsx_payload, role_index)
    resolved_xml = _overlay_resolved_roles(xml_payload, role_index)

    result = _CORE_BUILD_RECONCILIATION(
        input_root,
        resolved_inventory,
        resolved_csv,
        resolved_xlsx,
        resolved_xml,
        field_semantics_payload,
        label_semantics_payload,
        xml_group_registry,
    )
    return _attach_role_bridge_audit(
        result,
        role_report,
        bridge_status="PASS",
    )


# Runtime adaptations for the reconstructed historical capability:
# 1) identifiers remain representation-sensitive candidates;
# 2) content-admitted source-role candidates are applied before role pairing.
# Neither adaptation promotes provider identity, physical event identity or tactical truth.
core.norm_field = runtime_norm_field
core.build_reconciliation = runtime_build_reconciliation

from research_hardening import guarded_main

if __name__ == "__main__":
    raise SystemExit(guarded_main())

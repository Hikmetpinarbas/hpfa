from __future__ import annotations

from typing import Any

from hpfa.modules.core.row_nucleus_inventory_lite.src import (
    row_nucleus_inventory_hardened as _impl,
)

# Row-nucleus clearance evaluates the CSV/XML row-surface semantic record.
# XLSX aggregate-label records may support the same label, but they are not
# event semantics and therefore must not force an otherwise reviewed row
# candidate into semantic review.
_NON_ACTION_ROLE_ELIGIBILITY: dict[str, set[str]] = {
    "CONTEXT_INTERVAL": {"CONTEXT_ONLY"},
    "PARTICIPATION_INTERVAL": {"PARTICIPATION_ONLY"},
    "DERIVED_CONSEQUENCE_CANDIDATE": {"DERIVED_ONLY"},
    "TERMINAL_OUTCOME_CANDIDATE": {"TERMINAL_OUTCOME_ONLY"},
    "PERIOD_OR_META": {"ADMIN_ONLY"},
    "MATCH_BOUNDARY": {"ADMIN_ONLY"},
    "ADMINISTRATIVE": {"ADMIN_ONLY"},
    "ADMINISTRATIVE_MARKER": {"ADMIN_ONLY"},
    "OPPONENT_ACTION_REFERENCE": {"REFERENCE_ONLY"},
    "RECEIVED_ACTION_REFERENCE": {"REFERENCE_ONLY"},
}

_COORDINATE_EXEMPT_ADMIN_ROLES = {
    "PERIOD_OR_META",
    "MATCH_BOUNDARY",
    "ADMINISTRATIVE",
    "ADMINISTRATIVE_MARKER",
}


def semantic_clearance(
    records: list[dict[str, Any]],
) -> tuple[bool, list[str], list[str], list[str], list[str]]:
    """Return row-surface semantic clearance without promoting semantic truth.

    Exact-reviewed non-action roles are valid row-nucleus routes even when they
    intentionally carry no action family. Action anchors still require one and
    only one action family. Unknown roles and review-status mappings remain
    fail-closed at REVIEW_REQUIRED.
    """

    statuses = sorted({str(row.get("mapping_status") or "UNKNOWN") for row in records})
    roles = sorted(
        {
            str(row.get("semantic_role_candidate"))
            for row in records
            if row.get("semantic_role_candidate")
        }
    )
    families = sorted(
        {
            str(row.get("action_family_candidate"))
            for row in records
            if row.get("action_family_candidate")
        }
    )
    eligibilities = sorted(
        {
            str(row.get("downstream_eligibility"))
            for row in records
            if row.get("downstream_eligibility")
        }
    )

    primary_records = [
        row
        for row in records
        if str(row.get("source_format") or "").casefold() != "xlsx"
        and row.get("semantic_role_candidate") != "AGGREGATE_METRIC_LABEL"
    ]
    primary_statuses = {
        str(row.get("mapping_status") or "UNKNOWN") for row in primary_records
    }
    primary_roles = {
        str(row.get("semantic_role_candidate"))
        for row in primary_records
        if row.get("semantic_role_candidate")
    }
    primary_families = {
        str(row.get("action_family_candidate"))
        for row in primary_records
        if row.get("action_family_candidate")
    }
    primary_eligibilities = {
        str(row.get("downstream_eligibility"))
        for row in primary_records
        if row.get("downstream_eligibility")
    }

    cleared = False
    if (
        primary_records
        and not any(
            status in _impl.REVIEW_MAPPING_STATUSES for status in primary_statuses
        )
        and len(primary_roles) == 1
    ):
        role = next(iter(primary_roles))
        if role == "ACTION_ANCHOR":
            cleared = len(primary_families) == 1
        elif role in _NON_ACTION_ROLE_ELIGIBILITY:
            allowed = _NON_ACTION_ROLE_ELIGIBILITY[role]
            cleared = bool(primary_eligibilities) and primary_eligibilities <= allowed
        else:
            # A new semantic role must be added to the explicit contract before
            # it can clear a row nucleus.
            cleared = False

    return cleared, statuses, roles, families, eligibilities


def coordinate_is_required(record: dict[str, Any]) -> bool:
    """Return whether G07 must require coordinates for this row nucleus.

    Only an explicitly administrative row nucleus can be exempt. A record with
    an unknown, mixed or action-bearing semantic route remains coordinate-
    required so this correction cannot become a permissive spatial shortcut.
    """

    roles = {
        str(value)
        for value in (record.get("semantic_role_candidates") or [])
        if value
    }
    eligibilities = {
        str(value)
        for value in (record.get("downstream_eligibility_candidates") or [])
        if value
    }
    return not (
        bool(roles)
        and roles <= _COORDINATE_EXEMPT_ADMIN_ROLES
        and eligibilities == {"ADMIN_ONLY"}
    )


def apply_coordinate_eligibility_rollup(report: dict[str, Any]) -> dict[str, Any]:
    """Correct G07 denominator while preserving all other gate decisions.

    Missing-coordinate administrative/meta rows remain visible evidence and
    are counted separately; they simply do not create a spatial-readiness
    review when their explicit semantic contract says coordinates do not apply.
    """

    nuclei = report.get("row_nuclei") or []
    missing = [
        record
        for record in nuclei
        if record.get("pos_x_candidate") is None
        or record.get("pos_y_candidate") is None
    ]
    exempt = [record for record in missing if not coordinate_is_required(record)]
    required_missing = [record for record in missing if coordinate_is_required(record)]

    report["coordinate_missing_nucleus_count"] = len(missing)
    report["coordinate_missing_exempt_nucleus_count"] = len(exempt)
    report["coordinate_missing_required_nucleus_count"] = len(required_missing)

    rollup = report.get("g01_g18_rollup")
    if not isinstance(rollup, dict):
        return report
    gates = rollup.get("gates") or []
    if not isinstance(gates, list):
        return report

    for gate_record in gates:
        if not isinstance(gate_record, dict) or gate_record.get("gate_id") != "G07":
            continue
        gate_record["status"] = "REVIEW_REQUIRED" if required_missing else "PASS"
        gate_record["message"] = (
            "Coordinate surface checked with eligibility-aware coverage."
        )
        gate_record["evidence"] = {
            "coordinate_missing_nucleus_count": len(missing),
            "coordinate_missing_exempt_nucleus_count": len(exempt),
            "coordinate_missing_required_nucleus_count": len(required_missing),
            "coordinate_exemption_rule": (
                "ADMIN_ONLY_AND_EXPLICIT_ADMINISTRATIVE_SEMANTIC_ROLE"
            ),
        }
        break

    states = [
        str(record.get("status") or "UNKNOWN")
        for record in gates
        if isinstance(record, dict)
    ]
    rollup["fail_closed_count"] = states.count("FAIL_CLOSED")
    rollup["review_required_count"] = states.count("REVIEW_REQUIRED")
    rollup["pass_count"] = states.count("PASS")
    rollup["not_applicable_count"] = states.count("NOT_APPLICABLE")
    rollup["status"] = (
        "FAIL_CLOSED"
        if "FAIL_CLOSED" in states
        else ("REVIEW_REQUIRED" if "REVIEW_REQUIRED" in states else "PASS")
    )

    hard_blocks = report.get("hard_block_hits") or []
    upstream_reviews = report.get("review_hits") or []
    row_reviews = int(report.get("row_nucleus_review_required_count") or 0)
    corrected_status = (
        "FAIL_CLOSED"
        if hard_blocks or rollup["status"] == "FAIL_CLOSED"
        else (
            "REVIEW_REQUIRED"
            if upstream_reviews or row_reviews or rollup["status"] == "REVIEW_REQUIRED"
            else "PASS"
        )
    )
    report["status"] = corrected_status
    report["module_status"] = corrected_status
    return report


# build_inventory/main are defined in the hardened implementation and resolve
# semantic_clearance and build_inventory from that module's globals at runtime.
# Bind the corrected contracts before/after re-exporting the public API.
_impl.semantic_clearance = semantic_clearance

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory_hardened import *  # noqa: E402,F401,F403

_original_build_inventory = _impl.build_inventory


def build_inventory(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return apply_coordinate_eligibility_rollup(
        _original_build_inventory(*args, **kwargs)
    )


_impl.build_inventory = build_inventory

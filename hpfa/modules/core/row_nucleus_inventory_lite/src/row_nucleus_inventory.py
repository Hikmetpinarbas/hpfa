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


# build_inventory/main are defined in the hardened implementation and resolve
# semantic_clearance from that module's globals at runtime. Bind the corrected
# contract before re-exporting the public API.
_impl.semantic_clearance = semantic_clearance

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory_hardened import *  # noqa: E402,F401,F403

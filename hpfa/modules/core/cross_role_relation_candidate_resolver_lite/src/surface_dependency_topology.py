from __future__ import annotations

from collections import Counter
from typing import Any

MODULE_ID = "surface_dependency_topology_v1"
CROSS_FORMAT_MODULE_ID = "cross_format_reconciliation_lite_v1"
CROSS_ROLE_MODULE_ID = "cross_role_relation_candidate_resolver_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "DEPENDENCY_DESCRIPTION_ONLY"

SERIALIZATION_REFLECTION = "SERIALIZATION_REFLECTION"
PARTIAL_SEMANTIC_PROJECTION = "PARTIAL_SEMANTIC_PROJECTION"
ROLE_TRANSFORMATION = "ROLE_TRANSFORMATION"
AGGREGATE_DERIVATION_UNRESOLVED = "AGGREGATE_DERIVATION_UNRESOLVED"
UNRESOLVED = "UNRESOLVED"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dependency_record(
    *,
    source_kind: str,
    source_ref: str,
    dependency_type: str,
    source_roles: list[str],
    review_required: bool,
    rationale: str,
) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "source_ref": source_ref,
        "dependency_type": dependency_type,
        "source_roles": sorted({_text(value) for value in source_roles if _text(value)}),
        "review_required": review_required,
        "rationale": rationale,
        "independent_support_allowed": False,
        "event_instance_allowed": False,
        "occurrence_identity_created": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_surface_dependency_topology(
    reconciliation_payload: dict[str, Any],
    cross_role_payload: dict[str, Any],
) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if reconciliation_payload.get("module_id") != CROSS_FORMAT_MODULE_ID:
        hard_blocks.append("cross_format_input_module_id_mismatch")
    if cross_role_payload.get("module_id") != CROSS_ROLE_MODULE_ID:
        hard_blocks.append("cross_role_input_module_id_mismatch")

    for prefix, payload in (("cross_format", reconciliation_payload), ("cross_role", cross_role_payload)):
        if payload.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            hard_blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            hard_blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            hard_blocks.append(f"{prefix}_hard_blocks_present")
        status = _text(payload.get("status"))
        if status == "FAIL_CLOSED":
            hard_blocks.append(f"{prefix}_fail_closed")
        elif status and status not in {"PASS", "SMOKE_PASS"}:
            review_hits.append(f"{prefix}_review_required:{status}")

    records: list[dict[str, Any]] = []
    seen_refs: set[tuple[str, str]] = set()

    if not hard_blocks:
        for index, pair in enumerate(reconciliation_payload.get("pair_reports") or []):
            if not isinstance(pair, dict):
                hard_blocks.append(f"pair_report_invalid:{index}")
                continue
            source_role = _text(pair.get("source_role")) or "UNKNOWN"
            pair_ref = _text(pair.get("pair_id")) or f"pair_report:{index}"
            decision = _text(pair.get("decision"))
            exact_count = int(pair.get("exact_surface_alignment_candidate_count") or 0)
            mismatch_count = int(pair.get("required_field_mismatch_candidate_count") or 0)

            if decision == "PASS_ALIGNMENT_CANDIDATE" and exact_count > 0 and mismatch_count == 0:
                dependency_type = SERIALIZATION_REFLECTION
                review_required = False
                rationale = "CSV/XML exact surface alignment candidate; one upstream observation reflected across serializations."
            else:
                dependency_type = UNRESOLVED
                review_required = True
                rationale = "Cross-format alignment is incomplete or contradictory; dependency remains unresolved."

            key = ("CROSS_FORMAT", pair_ref)
            if key in seen_refs:
                hard_blocks.append(f"duplicate_dependency_source_ref:{pair_ref}")
                continue
            seen_refs.add(key)
            records.append(
                _dependency_record(
                    source_kind="CROSS_FORMAT",
                    source_ref=pair_ref,
                    dependency_type=dependency_type,
                    source_roles=[source_role],
                    review_required=review_required,
                    rationale=rationale,
                )
            )

            xlsx_support = pair.get("xlsx_support") or {}
            if isinstance(xlsx_support, dict):
                dep_status = _text(xlsx_support.get("source_dependency_status"))
                if dep_status:
                    xlsx_ref = f"{pair_ref}:xlsx_support"
                    xlsx_type = (
                        AGGREGATE_DERIVATION_UNRESOLVED
                        if dep_status == "DERIVATION_DEPENDENCY_UNRESOLVED"
                        else UNRESOLVED
                    )
                    records.append(
                        _dependency_record(
                            source_kind="AGGREGATE_SUPPORT",
                            source_ref=xlsx_ref,
                            dependency_type=xlsx_type,
                            source_roles=[source_role],
                            review_required=True,
                            rationale="Aggregate/tabular support does not establish action identity or independent confirmation.",
                        )
                    )

        for index, relation in enumerate(cross_role_payload.get("resolved_relation_candidates") or []):
            if not isinstance(relation, dict):
                hard_blocks.append(f"cross_role_relation_invalid:{index}")
                continue
            relation_ref = _text(relation.get("resolved_relation_candidate_id")) or f"cross_role:{index}"
            roles = sorted({_text(value) for value in (relation.get("source_roles") or []) if _text(value)})
            role_set = set(roles)
            record_status = _text(relation.get("relation_record_status"))
            if role_set == {"PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"}:
                dependency_type = PARTIAL_SEMANTIC_PROJECTION
                rationale = "PLAYER surface preserves actor-specific semantics while TEAM surface is an identity-stripped partial projection; exact overlap is not independent evidence."
            elif role_set == {"GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"}:
                dependency_type = ROLE_TRANSFORMATION
                rationale = "GOALKEEPER surface may encode goalkeeper/opponent-action role-transformed semantics; exact overlap cannot be generalized as a filtered PLAYER reflection."
            else:
                dependency_type = UNRESOLVED
                rationale = "Cross-role dependency type is not allowlisted."

            review_required = record_status != "PASS_CANDIDATE_CLASSIFICATION" or dependency_type == UNRESOLVED
            records.append(
                _dependency_record(
                    source_kind="CROSS_ROLE",
                    source_ref=relation_ref,
                    dependency_type=dependency_type,
                    source_roles=roles,
                    review_required=review_required,
                    rationale=rationale,
                )
            )

    if hard_blocks:
        records = []

    dependency_counts = Counter(row["dependency_type"] for row in records)
    review_count = sum(row["review_required"] for row in records)
    if review_count:
        review_hits.append("dependency_records_require_review")

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "surface_dependency_records": records,
        "surface_dependency_record_count": len(records),
        "dependency_type_counts": dict(sorted(dependency_counts.items())),
        "review_required_dependency_record_count": review_count,
        "independent_support_created": False,
        "occurrence_identity_created": False,
        "cross_format_alignment_is_independent_evidence": False,
        "cross_role_overlap_is_independent_evidence": False,
        "aggregate_is_action_identity": False,
        "goalkeeper_surface_is_player_filtered_subset_truth": False,
        "claim_ceiling": CLAIM_CEILING,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

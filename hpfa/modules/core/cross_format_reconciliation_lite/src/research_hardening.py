from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

from cross_format_reconciliation import main as core_main

MAIN_OUTPUT = "cross_format_reconciliation_lite_v1.json"
SUMMARY_OUTPUT = "cross_format_reconciliation_lite_v1.txt"
ANALYST_OUTPUT = "cross_format_reconciliation_analyst_audit_v1.txt"


def _count(pair: dict[str, Any], key: str) -> int:
    try:
        return int(pair.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _replace_status_line(text: str, key: str, value: Any) -> str:
    prefix = f"{key}="
    lines = text.splitlines()
    replaced = False
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            lines[idx] = f"{prefix}{value}"
            replaced = True
    if not replaced:
        lines.append(f"{prefix}{value}")
    return "\n".join(lines) + "\n"


def apply_research_hardening(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply #177 research guards without promoting candidate evidence to truth."""
    result = copy.deepcopy(payload)
    existing_blocks = list(result.get("hard_block_hits") or [])
    added_blocks: list[str] = []
    review_reasons: list[str] = []

    # R16 — pairwise agreement cannot bootstrap itself into canonical identity.
    promoted_truth_fields = (
        "validated_cross_format_equivalence",
        "validated_team_identity",
        "validated_player_identity",
        "sequence_truth",
        "phase_truth",
        "tactical_truth",
    )
    for field in promoted_truth_fields:
        if result.get(field) is True:
            added_blocks.append(f"transitive_promotion_without_direct_evidence:{field}")

    pair_reports = result.get("pair_reports") or []
    namespace_records: list[dict[str, Any]] = []
    counterpart_states: list[dict[str, Any]] = []
    conflict_states: list[dict[str, Any]] = []

    for index, pair in enumerate(pair_reports):
        source_role = str(pair.get("source_role") or "UNKNOWN_ROLE")
        csv_role = str(pair.get("csv_source_role") or source_role)
        xml_role = str(pair.get("xml_source_role") or source_role)
        csv_surface = str(pair.get("csv_relative_path") or "UNKNOWN_CSV_SURFACE")
        xml_surface = str(pair.get("xml_relative_path") or "UNKNOWN_XML_SURFACE")
        cross_id_collisions = _count(pair, "cross_id_collision_count")
        local_duplicates = _count(pair, "local_duplicate_candidate_count")
        same_role = csv_role == xml_role == source_role
        uniqueness_evidence = local_duplicates == 0 and cross_id_collisions == 0
        namespace_compatible = same_role
        linkage_eligible = namespace_compatible and uniqueness_evidence

        # R26 — bare provider IDs are never global event identity.
        namespace_record = {
            "pair_index": index,
            "provider_candidate": "SPORTSBASE_PROVIDER_CANDIDATE",
            "provider_version": result.get("label_semantics_version") or "VERSION_UNRESOLVED",
            "match_scope": "ACTIVE_MATCH_LOCAL_ONLY",
            "source_role": source_role,
            "csv_surface": csv_surface,
            "xml_surface": xml_surface,
            "identifier_semantics": "PROVIDER_SURFACE_ROW_ID_CANDIDATE",
            "namespace_compatibility": namespace_compatible,
            "uniqueness_evidence": uniqueness_evidence,
            "collision_or_reuse_policy": "BLOCK_OR_REVIEW_NEVER_GLOBALIZE",
            "serialization_normalization": "REPRESENTATION_NORMALIZATION_ONLY",
            "linkage_eligibility": "SAME_ROLE_CANDIDATE_ONLY" if linkage_eligible else "BLOCKED",
            "global_event_identity_allowed": False,
            "claim_ceiling": "MATCH_LOCAL_SAME_ROLE_SHARED_ID_CANDIDATE_ONLY",
        }
        namespace_records.append(namespace_record)
        if not same_role:
            added_blocks.append(f"cross_role_identifier_join_forbidden:pair_{index}")
        if cross_id_collisions:
            added_blocks.append(f"identifier_namespace_collision_unresolved:pair_{index}")

        # R21 — absence of a counterpart is not contradiction unless a counterpart was expected.
        csv_only = _count(pair, "csv_only_id_candidate_count")
        xml_only = _count(pair, "xml_only_id_candidate_count")
        unmatched = csv_only + xml_only
        counterpart_state = {
            "pair_index": index,
            "missing_counterpart_candidate_count": unmatched,
            "counterpart_expectation_established": False,
            "missing_counterpart_is_contradiction": False,
            "state": (
                "MISSING_COUNTERPART_EXPECTATION_UNRESOLVED"
                if unmatched
                else "NO_MISSING_COUNTERPART_SIGNAL"
            ),
            "claim_ceiling": "EXPECTATION_UNRESOLVED_NO_NEGATIVE_CLAIM",
        }
        counterpart_states.append(counterpart_state)
        if unmatched:
            review_reasons.append(f"counterpart_expectation_unresolved:pair_{index}")

        # R24 — disagreement is unresolved evidence; no CSV/XML precedence or majority vote.
        required_mismatch = _count(pair, "required_field_mismatch_candidate_count")
        supporting_mismatch = _count(pair, "supporting_field_mismatch_candidate_count")
        conflict_count = required_mismatch + supporting_mismatch
        conflict_state = {
            "pair_index": index,
            "conflict_candidate_count": conflict_count,
            "authority_precedence": "NONE",
            "majority_vote_allowed": False,
            "automatic_resolution_allowed": False,
            "state": "UNRESOLVED_REVIEW_REQUIRED" if conflict_count else "NO_CONFLICT_SIGNAL",
            "claim_ceiling": "CONFLICT_UNRESOLVED_CANDIDATE_ONLY",
        }
        conflict_states.append(conflict_state)
        if conflict_count:
            review_reasons.append(f"cross_format_conflict_unresolved:pair_{index}")

        pair["identifier_namespace_guard"] = namespace_record
        pair["counterpart_expectation_guard"] = counterpart_state
        pair["conflict_authority_guard"] = conflict_state
        pair["temporal_attachment_guard"] = {
            "start_end_role": "SOURCE_TIMELINE_EVIDENCE_ONLY",
            "football_order_truth": False,
            "same_time_simultaneity_truth": False,
            "sequence_attachment_allowed": False,
            "claim_ceiling": "TEMPORAL_ATTACHMENT_CANDIDATE_ONLY",
        }
        pair["measurement_resolution_guard"] = {
            "numeric_comparison_mode": "EXACT_NORMALIZED_CANDIDATE_ONLY",
            "arbitrary_epsilon_allowed": False,
            "epsilon": None,
            "numeric_equality_is_semantic_equivalence_truth": False,
            "claim_ceiling": "REPRESENTATION_EQUALITY_CANDIDATE_ONLY",
        }
        pair["transitive_promotion_guard"] = {
            "pairwise_link_is_canonical_identity": False,
            "pairwise_link_can_promote_other_links": False,
            "claim_ceiling": "DIRECT_PAIRWISE_EVIDENCE_ONLY",
        }

    hard_blocks = sorted(set(existing_blocks + added_blocks))
    result["hard_block_hits"] = hard_blocks
    result["research_hardening"] = {
        "status": "FAIL_CLOSED" if added_blocks else "PASS",
        "R16_no_transitive_promotion": {
            "status": "PASS" if not any(x.startswith("transitive_promotion_without_direct_evidence") for x in added_blocks) else "FAIL_CLOSED",
            "canonical_identity_from_pairwise_links_allowed": False,
        },
        "R20_temporal_attachment": {
            "status": "PASS",
            "start_end_role": "SOURCE_TIMELINE_EVIDENCE_ONLY",
            "football_order_truth": False,
        },
        "R21_counterpart_expectation": {
            "status": "PASS",
            "missing_counterpart_without_expectation_is_contradiction": False,
            "records": counterpart_states,
        },
        "R23_measurement_resolution": {
            "status": "PASS",
            "comparison": "EXACT_NORMALIZED_CANDIDATE_ONLY",
            "arbitrary_epsilon_allowed": False,
        },
        "R24_conflict_authority": {
            "status": "PASS",
            "format_precedence": "NONE",
            "majority_vote_allowed": False,
            "records": conflict_states,
        },
        "R26_identifier_namespace": {
            "status": "PASS" if not any(x.startswith(("cross_role_identifier_join_forbidden", "identifier_namespace_collision_unresolved")) for x in added_blocks) else "FAIL_CLOSED",
            "bare_id_is_global_event_identity": False,
            "records": namespace_records,
        },
        "review_reasons": sorted(set(review_reasons)),
    }

    if added_blocks:
        result["status"] = "FAIL_CLOSED"
        result["module_status"] = "FAIL_CLOSED"
        result["fusion_admissibility"] = "BLOCKED"
        result["active_match_evidence_pass"] = False
        result["runtime_evidence_status"] = "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"
    elif review_reasons and result.get("status") == "PASS":
        result["status"] = "REVIEW_REQUIRED"
        result["module_status"] = "REVIEW_REQUIRED"
        result["fusion_admissibility"] = "CANDIDATE_ONLY"
        result["active_match_evidence_pass"] = False
        result["runtime_evidence_status"] = "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"

    result["validated_cross_format_equivalence"] = False
    result["validated_team_identity"] = False
    result["validated_player_identity"] = False
    result["canonical_event_count"] = "UNKNOWN"
    result["production_release"] = False
    return result


def harden_written_outputs(out_dir: str | Path) -> dict[str, Any] | None:
    out = Path(out_dir).expanduser().resolve(strict=False)
    main_path = out / MAIN_OUTPUT
    if not main_path.is_file():
        return None
    payload = json.loads(main_path.read_text(encoding="utf-8"))
    payload = apply_research_hardening(payload)
    main_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for name in (SUMMARY_OUTPUT, ANALYST_OUTPUT):
        path = out / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for key in ("status", "module_status", "runtime_evidence_status"):
            text = _replace_status_line(text, key, payload.get(key))
        text += (
            "research_hardening_status="
            f"{(payload.get('research_hardening') or {}).get('status')}\n"
            "identifier_namespace_global_event_identity=false\n"
            "missing_counterpart_without_expectation_is_contradiction=false\n"
            "numeric_equality_semantic_truth=false\n"
            "conflict_format_precedence=NONE\n"
            "canonical_event_count=UNKNOWN\n"
            "production_release=false\n"
        )
        path.write_text(text, encoding="utf-8")
    return payload


def _argument_value(argv: list[str], flag: str) -> str | None:
    try:
        return argv[argv.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def guarded_main() -> int:
    core_rc = core_main()
    out_dir = _argument_value(sys.argv, "--out")
    if out_dir is None:
        return 2
    try:
        payload = harden_written_outputs(out_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "hard_block_hits": [f"research_hardening_failed:{exc}"]}, ensure_ascii=False))
        return 2
    if payload is None:
        return core_rc
    print(json.dumps({
        "research_hardening_status": (payload.get("research_hardening") or {}).get("status"),
        "status": payload.get("status"),
        "active_match_evidence_pass": payload.get("active_match_evidence_pass"),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2))
    return 2 if payload.get("status") == "FAIL_CLOSED" else core_rc

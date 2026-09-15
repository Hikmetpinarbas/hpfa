from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_full_system_match_diagnostic_v1"
OUTPUT_JSON = "active_match_full_system_match_diagnostic_v1.json"
OUTPUT_TXT = "active_match_full_system_match_diagnostic_v1.txt"
UNKNOWN = "UNKNOWN"


def _load_json(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _status(payload: dict[str, Any], default: str = "UNKNOWN") -> str:
    return str(
        payload.get("status")
        or payload.get("module_status")
        or payload.get("decision")
        or default
    ).upper()


def _artifact_ledger(full_spine: dict[str, Any]) -> set[str]:
    values = full_spine.get("current_invocation_artifacts")
    if not isinstance(values, list):
        return set()
    return {Path(str(value)).name for value in values if value}


def _count(payload: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _component_from_artifact(
    root: Path,
    ledger: set[str],
    *,
    component: str,
    artifact: str,
    purpose: str,
    prerequisite: str,
    downstream: str,
    count_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = _load_json(root, artifact)
    exists = bool(payload)
    current = artifact in ledger
    raw_status = _status(payload) if exists else "MISSING"
    if current:
        invoked = True
        status = (
            "PASS"
            if raw_status in {"PASS", "SMOKE_PASS"}
            else raw_status
            if raw_status in {"REVIEW_REQUIRED", "FAIL_CLOSED"}
            else "EXECUTED"
        )
        degraded = (
            "producer_status_not_pass"
            if status == "REVIEW_REQUIRED"
            else None
        )
        blocked = (
            (payload.get("hard_block_hits") or [None])[0]
            if status == "FAIL_CLOSED"
            else None
        )
    elif exists:
        invoked = False
        status = "REVIEW_REQUIRED"
        degraded = "artifact_present_but_not_declared_in_current_invocation_ledger"
        blocked = None
    else:
        invoked = False
        status = "NOT_REACHED"
        degraded = "current_invocation_artifact_not_present"
        blocked = None

    meaningful_count = _count(payload, *count_keys) if count_keys else None
    return {
        "component": component,
        "purpose": purpose,
        "invoked": invoked,
        "status": status,
        "producer_status": raw_status,
        "required_prerequisite": prerequisite,
        "available_prerequisite": exists if not current else True,
        "output_artifact": artifact if exists else None,
        "current_invocation_artifact": current,
        "meaningful_object_count": meaningful_count,
        "degraded_reason": degraded,
        "fail_closed_reason": blocked,
        "downstream_consumer_reached": downstream,
    }


def _stage_component(
    chains: list[dict[str, Any]],
    stage: str,
    purpose: str,
    downstream: str,
) -> dict[str, Any]:
    records = [
        chain.get(stage)
        for chain in chains
        if isinstance(chain, dict) and isinstance(chain.get(stage), dict)
    ]
    status_counts = Counter(
        str(row.get("status") or "NO_EXPLICIT_STATUS").upper() for row in records
    )
    decision_counts = Counter(
        str(row.get("decision") or "NO_EXPLICIT_DECISION").upper()
        for row in records
    )
    fail = sum(
        value
        for key, value in status_counts.items()
        if key in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"}
    )
    review = sum(value for key, value in status_counts.items() if "REVIEW" in key)
    if not records:
        status = "NOT_REACHED"
    elif fail:
        status = "FAIL_CLOSED"
    elif review:
        status = "REVIEW_REQUIRED"
    elif set(status_counts) == {"NO_EXPLICIT_STATUS"}:
        status = "EXECUTED"
    else:
        status = "PASS"

    return {
        "component": f"c4_{stage}",
        "purpose": purpose,
        "invoked": bool(records),
        "status": status,
        "required_prerequisite": "upstream_c4_stage_output",
        "available_prerequisite": bool(records),
        "output_artifact": "active_match_full_spine_v1.json:intelligence_chains",
        "current_invocation_artifact": True if records else False,
        "meaningful_object_count": len(records),
        "status_counts": dict(status_counts),
        "decision_counts": dict(decision_counts),
        "degraded_reason": "explicit_review_required" if review else None,
        "fail_closed_reason": "one_or_more_chain_stage_failures" if fail else None,
        "downstream_consumer_reached": downstream,
    }


def _surface_match_candidate(report: dict[str, Any]) -> str:
    inventory = report.get("surface_inventory")
    if not isinstance(inventory, list):
        return UNKNOWN
    for row in inventory:
        if not isinstance(row, dict):
            continue
        name = str(row.get("source_file") or "")
        if name:
            return re.sub(r"\s*\(\d+\)(?=\.[^.]+$)", "", name)
    return UNKNOWN


def _human_report_scalar(root: Path, key: str) -> str | None:
    path = root / "HPFA_ANALYST_REPORT.txt"
    if not path.is_file():
        return None
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _top_mechanism_candidates(
    root: Path, limit: int = 5
) -> list[dict[str, Any]]:
    delta = _load_json(root, "grammar_stable_variant_feature_delta_projection_v1.json")
    records = delta.get("grammar_stable_variant_feature_delta_records")
    if not isinstance(records, list):
        return []

    candidates: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        resolved = int(record.get("resolved_variant_count") or 0)
        success_n = int(record.get("success_resolved_variant_count") or 0)
        failure_n = int(record.get("failure_resolved_variant_count") or 0)
        process_diffs = [
            row
            for row in (record.get("process_context_feature_difference_candidates") or [])
            if isinstance(row, dict)
        ]
        process_family_diffs = [
            row
            for row in process_diffs
            if "process_family_candidate:" in str(row.get("feature_token") or "")
        ]
        best_process = (
            max(
                process_family_diffs,
                key=lambda row: abs(
                    float(
                        row.get("descriptive_rate_delta_success_minus_failure")
                        or 0.0
                    )
                ),
            )
            if process_family_diffs
            else None
        )
        consequence_diffs = [
            row
            for row in (record.get("consequence_feature_difference_candidates") or [])
            if isinstance(row, dict)
        ]
        candidates.append(
            {
                "candidate_id": record.get(
                    "grammar_stable_variant_feature_delta_id"
                ),
                "team_identity_candidate_ids": record.get(
                    "team_identity_candidate_ids"
                )
                or [],
                "period_candidates": record.get("period_candidates") or [],
                "grammar_signature_tokens": record.get(
                    "grammar_signature_tokens"
                )
                or [],
                "resolved_variant_count": resolved,
                "success_variant_count": success_n,
                "failure_variant_count": failure_n,
                "visible_support": (
                    f"{success_n + failure_n}/{resolved}" if resolved else "0/0"
                ),
                "first_supported_context_difference_layer_candidate": record.get(
                    "first_supported_context_difference_layer_candidate"
                ),
                "first_supported_consequence_difference_layer_candidate": record.get(
                    "first_supported_consequence_difference_layer_candidate"
                ),
                "best_provider_reviewed_process_context_difference": best_process,
                "visible_consequence_difference_candidate_count": len(
                    consequence_diffs
                ),
                "counterevidence": (
                    "failure/deviant variants retained in same grammar family"
                ),
                "recurrence": "match_local_family_recurrence_candidate_only",
                "evidence_sufficiency": "REVIEW_REQUIRED",
                "claim_ceiling": record.get("claim_ceiling")
                or "ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
                "dependency_independence_proven": (
                    record.get("dependency_independence_proven") is True
                ),
                "statistical_independence_proven": (
                    record.get("statistical_independence_proven") is True
                ),
                "forbidden_inference": [
                    "tactical_plan",
                    "causality",
                    "player_quality_from_actor_locator",
                    "physical_geometry_from_provider_semantics",
                ],
                "analyst_meaning": (
                    "Use as a video/match-review locator for matched "
                    "success-vs-failure variants; do not publish as mechanism truth."
                ),
            }
        )
    candidates.sort(
        key=lambda row: (
            row["resolved_variant_count"],
            row["failure_variant_count"],
        ),
        reverse=True,
    )
    return [
        row for row in candidates if row["resolved_variant_count"] > 3
    ][:limit]


def _safe_finding_accounting(
    *,
    safe: dict[str, Any],
    claim: dict[str, Any],
    ledger: set[str],
) -> dict[str, Any]:
    safe_artifact = "safe_finding_admission_projection_v1.json"
    claim_artifact = "analyst_output_claim_contract_projection_v1.json"
    safe_current = bool(safe) and safe_artifact in ledger
    claim_current = bool(claim) and claim_artifact in ledger

    safe_decision_count = (
        int(safe.get("safe_finding_admission_decision_count") or 0)
        if safe_current
        else None
    )
    safe_counts = (
        dict(
            safe.get("finding_status_counts")
            or safe.get("safe_finding_admission_decision_counts")
            or {}
        )
        if safe_current
        else None
    )
    claim_counts = (
        dict(claim.get("safe_finding_admission_decision_counts") or {})
        if claim_current
        else None
    )
    claim_contract_count = (
        int(claim.get("analyst_output_contract_count") or 0)
        if claim_current
        else None
    )
    consumed = (
        claim.get("safe_finding_admission_consumed") is True
        if claim_current
        else None
    )

    if safe_current:
        finding_state = "EXECUTED"
    else:
        finding_state = "NOT_BOUND_CURRENT_RUN"

    if claim_current and consumed is True:
        claim_state = "EVALUATED_WITH_SAFE_FINDING"
    elif claim_current:
        claim_state = "EXECUTED_SAFE_FINDING_NOT_EVALUATED"
    else:
        claim_state = "NOT_BOUND_CURRENT_RUN"

    if safe_current:
        consistent = (
            claim_current
            and consumed is True
            and claim_contract_count == safe_decision_count
        )
        reason = (
            None
            if consistent
            else "current Safe Finding decisions are not fully consumed by the current claim contract"
        )
    elif claim_current:
        non_not_evaluated = sum(
            int(value or 0)
            for key, value in (claim_counts or {}).items()
            if str(key).upper() != "NOT_EVALUATED"
        )
        not_evaluated = int((claim_counts or {}).get("NOT_EVALUATED") or 0)
        consistent = (
            consumed is False
            and non_not_evaluated == 0
            and claim_contract_count == not_evaluated
        )
        reason = (
            None
            if consistent
            else "claim contract must preserve NOT_EVALUATED when Safe Finding is not current-run evaluated"
        )
    else:
        consistent = True
        reason = None

    return {
        "safe_current": safe_current,
        "claim_current": claim_current,
        "finding_evaluation_state": finding_state,
        "claim_evaluation_state": claim_state,
        "safe_decision_count": safe_decision_count,
        "safe_status_counts": safe_counts,
        "professional_finding_emitted_count": (
            int(safe.get("professional_finding_emitted_count") or 0)
            if safe_current
            else None
        ),
        "professional_emit_allowed": False if safe_current else None,
        "claim_contract_count": claim_contract_count,
        "claim_safe_finding_consumed": consumed,
        "claim_decision_counts": claim_counts,
        "claim_professional_emit_allowed_count": (
            int(claim.get("professional_emit_allowed_count") or 0)
            if claim_current
            else None
        ),
        "consistency_status": "PASS" if consistent else "REVIEW_REQUIRED",
        "consistency_reason": reason,
    }


def build_diagnostic(
    root: Path,
    *,
    repository: str | None = None,
    branch: str | None = None,
    pr: str | None = None,
    head: str | None = None,
) -> dict[str, Any]:
    full = _load_json(root, "active_match_full_spine_v1.json")
    exact = _load_json(root, "active_match_exact_head_run_v1.json")
    report = _load_json(root, "active_match_analyst_report_lite_v1.json")
    ledger = _artifact_ledger(full)
    chains = [
        row
        for row in (full.get("intelligence_chains") or [])
        if isinstance(row, dict)
    ]

    specs = [
        ("multiformat_inventory", "multiformat_file_inventory_lite_v1.json", "enumerate admitted input surfaces", "ACTIVE_MATCH files", "surface readers", ("supported_file_count",)),
        ("csv_surface_reader", "csv_surface_audit_lite_v1.json", "read CSV event-like surfaces", "CSV surfaces", "row nucleus", ("csv_file_count",)),
        ("xml_surface_reader", "xml_surface_audit_lite_v1.json", "read XML event-like surfaces", "XML surfaces", "cross-format reconciliation", ("xml_file_count",)),
        ("xlsx_surface_reader", "xlsx_surface_audit_lite_v1.json", "read aggregate/tabular XLSX surfaces", "XLSX surfaces", "aggregate projection", ("xlsx_file_count",)),
        ("cross_format_reconciliation", "cross_format_reconciliation_lite_v1.json", "reconcile reflections without inventing independence", "multi-format surfaces", "row nucleus", ("role_pair_count",)),
        ("row_nucleus_inventory", "row_nucleus_inventory_lite_v1.json", "build row-level observation nuclei", "admitted surfaces", "evidence atoms", ("row_nucleus_candidate_count",)),
        ("provider_alias_field_semantics", "provider_alias_field_semantics_lite_v1.json", "admit provider field semantics", "provider fields", "context semantics", ("field_record_count",)),
        ("provider_label_value_semantics", "provider_label_value_semantics_lite_v1.json", "review provider label semantics", "provider labels", "context semantics", ("provider_label_record_count",)),
        ("minimum_viable_context", "minimum_viable_context_lite_v1.json", "bind minimal row context", "row nuclei", "semantic rebind", ("context_candidate_count",)),
        ("evidence_atom_inventory", "evidence_atom_inventory_lite_v1.json", "materialize evidence atoms", "row nuclei", "identity/relation", ("evidence_atom_count",)),
        ("match_local_identity", "match_local_identity_candidates_lite_v1.json", "bind match-local actor/team identity candidates", "evidence atoms", "relations/episodes", ("identity_binding_record_count",)),
        ("context_action_semantics_rebind", "context_action_semantics_rebind_lite_v1.json", "bind action semantics to context", "context + reviewed semantics", "action bundles", ("context_action_semantic_record_count",)),
        ("semantic_role_action_bundles", "semantic_role_action_bundle_candidates_lite_v1.json", "form semantic action bundles", "semantic routes", "relations/occurrences", ("action_bundle_candidate_count",)),
        ("cross_role_relation_resolver", "cross_role_relation_candidate_resolver_lite_v1.json", "resolve cross-role relation candidates", "action bundles", "occurrence admission", ("resolved_relation_candidate_count",)),
        ("multi_family_review_taxonomy", "action_bundle_multi_family_review_taxonomy_lite_v1.json", "classify ambiguous multi-family bundles", "action bundles", "occurrence admission", ("classified_candidate_core_count",)),
        ("action_occurrence_admission", "action_occurrence_admission_lite_v1.json", "admit action occurrence candidates", "bundles + relations", "trace/consequence/sequence", ("action_occurrence_candidate_count",)),
        ("trackable_action_trace", "trackable_action_trace_candidates_lite_v1.json", "bind visible traces to admitted occurrences", "occurrences", "consequence/spatial", ("occurrence_trace_binding_record_count",)),
        ("trackable_action_consequence", "trackable_action_consequence_candidates_lite_v1.json", "bind visible consequences", "occurrences", "occurrence consequence", ("occurrence_with_any_consequence_visible_count",)),
        ("event_window_builder", "event_window_builder_lite_v1.json", "build temporal windows with same-time safeguards", "context timestamps", "episode lane", ("event_window_count",)),
        ("time_scale_router", "time_scale_router_lite_v1.json", "route admitted temporal scale", "event windows", "episode locator", ("routed_window_count",)),
        ("analyst_episode_locator", "analyst_episode_locator_lite_v1.json", "locate analyst-review episode candidates", "temporal windows + semantics", "episode features", ("episode_candidate_count",)),
        ("episode_feature_vector", "episode_feature_vector_lite_v1.json", "derive episode feature candidates", "episodes", "temporal signatures/report", ("episode_feature_vector_count",)),
        ("temporal_episode_signature", "temporal_episode_signature_lite_v1.json", "compare temporal episode signatures", "episode features", "episode intelligence", ("temporal_episode_signature_count",)),
        ("process_participation_projection", "analyst_episode_process_participation_projection_v1.json", "bind provider-reviewed process participation", "evidence+identity+episode", "variant context", ("process_participation_candidate_count",)),
        ("spatial_transition_candidate", "spatial_transition_candidate_lite_v1.json", "derive bounded spatial transition candidates", "trace+evidence", "state transition", ("spatial_transition_candidate_count",)),
        ("state_transition_dynamics", "state_transition_dynamics_lite_v1.json", "derive bounded state-transition dynamics", "spatial+consequence", "occurrence state", ("state_transition_dynamics_candidate_count",)),
        ("occurrence_consequence_projection", "occurrence_consequence_projection_v1.json", "project admitted follow-up and censoring", "trace+consequence+episode boundary", "occurrence state/sequence", ("occurrence_consequence_projection_count",)),
        ("occurrence_state_transition_projection", "occurrence_state_transition_projection_v1.json", "join occurrence to bounded state transition", "spatial+occurrence consequence", "feature delta", ("occurrence_state_transition_projection_count",)),
        ("visible_action_sequence", "visible_action_sequence_candidates_lite_v1.json", "build partial-order sequence/branch candidates", "occurrences+temporal admission", "grammar/process variants", ("occurrence_temporal_sequence_candidate_count",)),
        ("supported_sequence_grammar_alignment", "supported_sequence_grammar_alignment_projection_v1.json", "establish comparison-eligible sequence grammar", "visible sequences", "process variant binding", ("supported_sequence_grammar_alignment_count",)),
        ("observable_process_variant_binding", "observable_process_variant_binding_projection_v1.json", "bind success/failure observable process variants", "grammar alignment", "feature delta", ("observable_process_variant_family_count",)),
        ("grammar_stable_variant_feature_delta", "grammar_stable_variant_feature_delta_projection_v1.json", "compare matched variant features", "process variants+occurrence state+consequence", "challenge/safe finding", ("grammar_stable_variant_feature_delta_record_count",)),
        ("variant_feature_challenge", "variant_feature_challenge_projection_v1.json", "challenge feature differences without creating evidence", "feature deltas", "safe finding admission", ("variant_feature_challenge_record_count",)),
        ("rich_multiformat_analysis_lattice", "rich_multiformat_analysis_lattice_v1.json", "join event-like and aggregate surfaces under claim guards", "shared surface snapshot+XLSX semantics", "construct/C4", ("xlsx_projected_row_count",)),
        ("metric_anatomy_bridge", "active_match_metric_anatomy_bridge_v1.json", "bind metric anatomy candidates", "aggregate semantics", "metric governance", ("metric_anatomy_candidate_count",)),
        ("metric_governance_bridge", "active_match_metric_governance_bridge_v1.json", "govern construct/metric promotion", "metric anatomy+provider semantics", "rich construct gate", ("metric_anatomy_candidate_count",)),
        ("reconstruction_packet_adapter", "reconstruction_intelligence_packet_adapter_lite_v1.json", "adapt sequence candidates into C4 packet inputs", "visible sequences", "composite packets", ("packet_input_candidate_count",)),
        ("reconstruction_packet_bridge", "reconstruction_intelligence_packet_bridge_current_v1.json", "bridge current reconstruction to intelligence spine", "current surface snapshot", "composite packets", ("composite_packet_count",)),
        ("composite_evidence_packets", "composite_evidence_packet_builder_lite_v1.json", "build evidence packets for C4", "reconstruction inputs", "C4 fusion", ("packet_count",)),
        ("safe_finding_admission", "safe_finding_admission_projection_v1.json", "apply professional finding admission gate", "challenge+spread+counterevidence", "analyst claim contract", ("safe_finding_admission_decision_count",)),
        ("analyst_output_claim_contract", "analyst_output_claim_contract_projection_v1.json", "bound analyst wording to admitted claim ceiling", "safe finding admission", "human analyst output", ("analyst_output_contract_count",)),
    ]
    components = [
        _component_from_artifact(
            root,
            ledger,
            component=component,
            artifact=artifact,
            purpose=purpose,
            prerequisite=prerequisite,
            downstream=downstream,
            count_keys=count_keys,
        )
        for component, artifact, purpose, prerequisite, downstream, count_keys in specs
    ]

    c4_specs = [
        ("packet", "carry composite packet into C4", "fusion"),
        ("fusion", "fuse signals without treating reflections as independent votes", "argument"),
        ("argument", "build defeasible argument candidate", "route"),
        ("route", "route defeasible argument", "graph"),
        ("graph", "build evidence graph", "lens"),
        ("lens", "evaluate evidence-lens coverage", "safe_sentence"),
        ("safe_sentence", "route bounded Turkish safe sentence", "report_block"),
        ("report_block", "compose analyst report block candidate", "output_contract"),
        ("output_contract", "enforce report output contract", "assembly"),
        ("assembly", "gate final report assembly candidate", "analyst output"),
    ]
    components.extend(
        _stage_component(chains, stage, purpose, downstream)
        for stage, purpose, downstream in c4_specs
    )

    runtime_binding = (
        full.get("variant_feature_challenge_runtime_binding")
        if isinstance(full.get("variant_feature_challenge_runtime_binding"), dict)
        else {}
    )
    for component_row in components:
        if (
            component_row.get("component") == "variant_feature_challenge"
            and runtime_binding.get("artifact_materialized") is True
        ):
            component_row["invoked"] = True
            component_row["status"] = str(
                runtime_binding.get("status") or "EXECUTED"
            ).upper()
            component_row["available_prerequisite"] = True
            component_row["meaningful_object_count"] = runtime_binding.get(
                "variant_feature_challenge_record_count"
            )
            component_row["degraded_reason"] = (
                "runtime_binding_proves_materialization_but_current_invocation_ledger_omits_artifact"
                if not component_row.get("current_invocation_artifact")
                else None
            )

    sidecars = (
        full.get("orphan_capability_sidecars")
        if isinstance(full.get("orphan_capability_sidecars"), dict)
        else {}
    )
    triplex_status = str(
        sidecars.get("triplex_source_alignment_status") or "NOT_REACHED"
    )
    components.extend(
        [
            {
                "component": "triplex_source_alignment",
                "purpose": (
                    "align source mapping surfaces when mapping contract exists"
                ),
                "invoked": False if "NOT_APPLICABLE" in triplex_status else True,
                "status": (
                    "BLOCKED_BY_PREREQUISITE"
                    if "PREREQUISITE_MISSING" in triplex_status
                    else triplex_status
                ),
                "required_prerequisite": "source_mapping_contract_or_audit",
                "available_prerequisite": bool(
                    sidecars.get("triplex_source_alignment_prerequisite_present")
                ),
                "output_artifact": None,
                "meaningful_object_count": None,
                "degraded_reason": (
                    sidecars.get("triplex_source_alignment", {}).get("reason")
                    if isinstance(sidecars.get("triplex_source_alignment"), dict)
                    else None
                ),
                "fail_closed_reason": None,
                "downstream_consumer_reached": "not required for current admitted path",
            },
            {
                "component": "external_context_pipeline",
                "purpose": "bind admitted external context",
                "invoked": False,
                "status": "BLOCKED_BY_PREREQUISITE",
                "required_prerequisite": "admitted external context surface",
                "available_prerequisite": False,
                "output_artifact": None,
                "meaningful_object_count": None,
                "degraded_reason": (
                    "no external context surface in current ACTIVE_MATCH"
                ),
                "fail_closed_reason": None,
                "downstream_consumer_reached": False,
            },
            {
                "component": "tracking_video_pipeline",
                "purpose": "support physical geometry/off-ball/video claims",
                "invoked": False,
                "status": "NOT_APPLICABLE",
                "required_prerequisite": (
                    "tracking/video observation surface and implemented pipeline"
                ),
                "available_prerequisite": False,
                "output_artifact": None,
                "meaningful_object_count": None,
                "degraded_reason": (
                    "tracking/video absent and current implementation not established"
                ),
                "fail_closed_reason": None,
                "downstream_consumer_reached": False,
            },
        ]
    )

    for component_row in components:
        component_status = str(
            component_row.get("status") or "UNKNOWN"
        ).upper()
        if component_status == "BLOCKED_BY_PREREQUISITE":
            runtime_state = "BLOCKED_BY_PREREQUISITE"
        elif component_status == "NOT_APPLICABLE":
            runtime_state = "NOT_APPLICABLE"
        elif component_row.get("invoked") is True:
            runtime_state = "EXECUTED"
        else:
            runtime_state = "NOT_BOUND_CURRENT_RUN"
        component_row["runtime_execution_state"] = runtime_state
        component_row["engineering_test_state"] = "UNKNOWN"
        component_row["result_state"] = (
            component_status
            if component_status in {"PASS", "REVIEW_REQUIRED", "FAIL_CLOSED"}
            else "UNKNOWN"
        )

    occurrence = _load_json(root, "occurrence_consequence_projection_v1.json")
    sequence = _load_json(root, "visible_action_sequence_candidates_lite_v1.json")
    process = _load_json(root, "observable_process_variant_binding_projection_v1.json")
    delta = _load_json(root, "grammar_stable_variant_feature_delta_projection_v1.json")
    safe = _load_json(root, "safe_finding_admission_projection_v1.json")
    claim = _load_json(root, "analyst_output_claim_contract_projection_v1.json")
    semantics = _load_json(root, "context_action_semantics_rebind_lite_v1.json")
    identity = _load_json(root, "match_local_identity_candidates_lite_v1.json")
    relation = _load_json(root, "cross_role_relation_candidate_resolver_lite_v1.json")
    windows = _load_json(root, "event_window_builder_lite_v1.json")
    spatial = _load_json(root, "spatial_transition_candidate_lite_v1.json")
    participation = _load_json(
        root, "analyst_episode_process_participation_projection_v1.json"
    )
    xlsx = _load_json(root, "xlsx_entity_metric_row_projection_lite_v1.json")
    evidence = _load_json(root, "evidence_atom_inventory_lite_v1.json")
    occurrences = _load_json(root, "action_occurrence_admission_lite_v1.json")
    finding_accounting = _safe_finding_accounting(
        safe=safe,
        claim=claim,
        ledger=ledger,
    )

    capabilities = [
        {"family":"ACTION/EVENT","status":"ADMITTED","support":"action_occurrence_candidate_count","count":occurrences.get("action_occurrence_candidate_count"),"ceiling":"ACTION_OCCURRENCE_CANDIDATE_ONLY; canonical_event_count remains UNKNOWN"},
        {"family":"ENTITY/ACTOR","status":"DEGRADED","support":"match-local identity candidates","count":identity.get("actor_identity_candidate_count"),"ceiling":"MATCH_LOCAL_IDENTITY_CANDIDATE_ONLY"},
        {"family":"TEMPORAL","status":"ADMITTED","support":"event windows + partial-order sequence","count":windows.get("event_window_count"),"ceiling":"SAME_TIME_UNORDERED preserved; no total order from row order"},
        {"family":"SPATIAL","status":"DEGRADED","support":"coordinate/provider-semantic spatial candidates","count":spatial.get("spatial_transition_candidate_count"),"ceiling":"COORDINATE_NOT_TRACKING; no physical geometry truth"},
        {"family":"OUTCOME/QUALIFIER","status":"ADMITTED","support":"visible outcome partition/consequence surfaces","count":sequence.get("comparison_eligible_outcome_record_count"),"ceiling":"provider/visible outcome partition only"},
        {"family":"RELATIONAL","status":"DEGRADED","support":"cross-role relation candidates","count":relation.get("resolved_relation_candidate_count"),"ceiling":"relation candidate, not causal relation"},
        {"family":"PROCESS/PARTICIPATION","status":"DEGRADED","support":"provider-reviewed process participation","count":participation.get("process_participation_candidate_count"),"ceiling":"provider-reviewed annotation context, not tactical plan"},
        {"family":"AGGREGATE/TABULAR","status":"ADMITTED","support":"XLSX aggregate projection","count":xlsx.get("row_projection_count"),"ceiling":"aggregate surface does not create action identity"},
        {"family":"EXTERNAL CONTEXT","status":"ABSENT","support":None,"count":0,"ceiling":"no external-context claim"},
        {"family":"TRACKING/VIDEO","status":"ABSENT","support":None,"count":0,"ceiling":"no tracking/video physical claim"},
        {"family":"HPFA-DERIVED INTELLIGENCE","status":"DEGRADED","support":"partial-order/process/feature/finding chain","count":sequence.get("occurrence_temporal_sequence_candidate_count"),"ceiling":"ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY; professional EMIT may remain zero"},
    ]

    evidence_spine = [
        {"node":"SOURCE","reached":True,"meaningful_object_count":report.get("match_snapshot",{}).get("surface_file_count"),"major_censoring":None,"unresolved_burden":"provider surfaces share upstream dependence","dependency_burden":"multiformat reflection != independence","next_barrier":"none for current source inventory"},
        {"node":"SURFACE","reached":True,"meaningful_object_count":report.get("match_snapshot",{}).get("surface_file_count"),"major_censoring":None,"unresolved_burden":None,"dependency_burden":"CSV/XML reflection; XLSX aggregate separate role","next_barrier":"source-role/semantic admission"},
        {"node":"OBSERVATION","reached":bool(evidence),"meaningful_object_count":evidence.get("evidence_atom_count"),"major_censoring":None,"unresolved_burden":evidence.get("evidence_atom_review_required_count"),"dependency_burden":"row != event truth","next_barrier":"semantics/identity"},
        {"node":"SEMANTICS","reached":bool(semantics),"meaningful_object_count":semantics.get("context_action_semantic_record_count"),"major_censoring":None,"unresolved_burden":semantics.get("provider_semantics_unresolved_or_review_required_count"),"dependency_burden":"provider label != football truth","next_barrier":"identity/dependency"},
        {"node":"IDENTITY/DEPENDENCY","reached":bool(identity),"meaningful_object_count":identity.get("identity_binding_record_count"),"major_censoring":None,"unresolved_burden":identity.get("unbound_atom_count"),"dependency_burden":"independence not proven","next_barrier":"time/space admission"},
        {"node":"TIME/SPACE ADMISSION","reached":bool(windows and spatial),"meaningful_object_count":{"event_windows":windows.get("event_window_count"),"spatial_candidates":spatial.get("spatial_transition_candidate_count")} ,"major_censoring":"same-time peers remain unordered","unresolved_burden":windows.get("same_time_unordered_bucket_count"),"dependency_burden":"coordinate != tracking","next_barrier":"relation/episode"},
        {"node":"RELATION","reached":bool(relation),"meaningful_object_count":relation.get("resolved_relation_candidate_count"),"major_censoring":None,"unresolved_burden":relation.get("review_required_relation_count"),"dependency_burden":"candidate relation only","next_barrier":"episode/process"},
        {"node":"EPISODE/PROCESS","reached":bool(full.get("episode_candidate_count")),"meaningful_object_count":{"episodes":full.get("episode_candidate_count"),"process_participation":participation.get("process_participation_candidate_count"),"process_variant_families":process.get("observable_process_variant_family_count")} ,"major_censoring":None,"unresolved_burden":full.get("review_hits") or [],"dependency_burden":"process annotation not intention","next_barrier":"feature comparison"},
        {"node":"FEATURE","reached":bool(delta),"meaningful_object_count":{"episode_vectors":full.get("episode_feature_vector_count"),"variant_feature_delta_records":delta.get("grammar_stable_variant_feature_delta_record_count")} ,"major_censoring":delta.get("admitted_followup_horizon_sensitive_family_count"),"unresolved_burden":delta.get("base_context_feature_provenance_unresolved_count"),"dependency_burden":"feature rows are not independent votes","next_barrier":"metric/model/signal"},
        {"node":"METRIC/MODEL","reached":True,"meaningful_object_count":{"primitive_metrics":full.get("primitive_metric_count"),"construct_C01":1},"major_censoring":None,"unresolved_burden":"C01 REVIEW_REQUIRED","dependency_burden":"same-provider support non-independent","next_barrier":"occurrence progression semantics admission"},
        {"node":"SIGNAL","reached":bool(process),"meaningful_object_count":process.get("observable_process_variant_binding_count"),"major_censoring":None,"unresolved_burden":None,"dependency_burden":"signal != finding","next_barrier":"hypothesis/challenge"},
        {"node":"HYPOTHESIS","reached":bool(delta),"meaningful_object_count":delta.get("grammar_stable_variant_feature_delta_record_count"),"major_censoring":None,"unresolved_burden":delta.get("review_hits"),"dependency_burden":"descriptive difference != explanation","next_barrier":"counterevidence"},
        {"node":"COUNTEREVIDENCE","reached":bool(sequence),"meaningful_object_count":sequence.get("comparable_counterevidence_candidate_count"),"major_censoring":occurrence.get("right_censored_occurrence_count"),"unresolved_burden":(occurrence.get("followup_observation_status_counts") or {}).get("FOLLOWUP_UNRESOLVED"),"dependency_burden":"counterexample pair is not independent evidence count","next_barrier":"safe finding sufficiency"},
        {
            "node":"FINDING",
            "reached":finding_accounting["safe_current"],
            "evaluation_state":finding_accounting["finding_evaluation_state"],
            "meaningful_object_count":finding_accounting["safe_decision_count"],
            "major_censoring":None,
            "unresolved_burden":finding_accounting["safe_status_counts"],
            "dependency_burden":"independent support not proven only when Safe Finding is actually evaluated",
            "next_barrier":"professional EMIT admission",
        },
        {
            "node":"CLAIM",
            "reached":finding_accounting["claim_current"],
            "evaluation_state":finding_accounting["claim_evaluation_state"],
            "meaningful_object_count":finding_accounting["claim_contract_count"],
            "major_censoring":None,
            "unresolved_burden":finding_accounting["claim_decision_counts"],
            "dependency_burden":"claim ceiling enforced; NOT_EVALUATED != DOWNGRADE",
            "next_barrier":"Safe Finding admission or independent/contextual sufficiency",
        },
        {"node":"ANALYST OUTPUT","reached":(root/"HPFA_ANALYST_REPORT.txt").is_file(),"meaningful_object_count":1 if (root/"HPFA_ANALYST_REPORT.txt").is_file() else 0,"major_censoring":None,"unresolved_burden":"report is review output, not evidence","dependency_burden":"human text must remain under machine ceiling","next_barrier":"cross-artifact accounting consistency"},
    ]

    machine_chain_count = full.get("intelligence_chain_count")
    human_chain_raw = _human_report_scalar(root, "intelligence_chain_count")
    try:
        human_chain_count = (
            int(human_chain_raw) if human_chain_raw is not None else None
        )
    except ValueError:
        human_chain_count = None

    challenge = _load_json(root, "variant_feature_challenge_projection_v1.json")
    challenge_current = "variant_feature_challenge_projection_v1.json" in ledger
    artifact_challenge_count = challenge.get(
        "variant_feature_challenge_record_count"
    )
    runtime_challenge_count = runtime_binding.get(
        "variant_feature_challenge_record_count"
    )
    binding_materialized = runtime_binding.get("artifact_materialized") is True
    if binding_materialized:
        variant_consistent = (
            bool(challenge)
            and challenge_current
            and artifact_challenge_count == runtime_challenge_count
        )
    else:
        variant_consistent = not challenge_current and not bool(challenge)

    consistency = [
        {
            "check": "machine_vs_human_intelligence_chain_count",
            "status": (
                "PASS"
                if human_chain_count == machine_chain_count
                else "REVIEW_REQUIRED"
            ),
            "machine_value": machine_chain_count,
            "human_report_value": human_chain_count,
            "reason": (
                None
                if human_chain_count == machine_chain_count
                else "human report accounting disagrees with machine full-spine output"
            ),
        },
        {
            "check": "variant_feature_challenge_current_invocation_accounting",
            "status": "PASS" if variant_consistent else "REVIEW_REQUIRED",
            "artifact_present": bool(challenge),
            "declared_current_invocation": challenge_current,
            "artifact_record_count": artifact_challenge_count,
            "runtime_binding_record_count": runtime_challenge_count,
            "runtime_binding_materialized": binding_materialized,
            "reason": (
                None
                if variant_consistent
                else "challenge ledger/artifact/runtime-binding accounting is not closed"
            ),
        },
        {
            "check": "safe_finding_current_run_accounting",
            "status": finding_accounting["consistency_status"],
            "safe_finding_evaluation_state": finding_accounting[
                "finding_evaluation_state"
            ],
            "claim_evaluation_state": finding_accounting[
                "claim_evaluation_state"
            ],
            "claim_safe_finding_consumed": finding_accounting[
                "claim_safe_finding_consumed"
            ],
            "claim_decision_counts": finding_accounting[
                "claim_decision_counts"
            ],
            "reason": finding_accounting["consistency_reason"],
        },
    ]

    exact_head = head or exact.get("product_code_commit") or UNKNOWN
    run_identity = {
        "repository": repository or "Hikmetpinarbas/hpfa",
        "branch": branch or UNKNOWN,
        "pr": pr or UNKNOWN,
        "head": exact_head,
        "exact_product_commit_verified": (
            exact.get("exact_product_commit_verified") if exact else UNKNOWN
        ),
        "canonical_orchestrator": exact.get("canonical_orchestrator")
        or "active_match_spine_runner.py --full-spine",
        "runtime_authority": full.get("active_match_authority")
        or report.get("match_snapshot", {}).get("match_dir")
        or UNKNOWN,
        "match_identity_candidate": _surface_match_candidate(report),
        "canonical_event_count": UNKNOWN,
        "true_action_count": UNKNOWN,
        "production_release": False,
    }

    match_intelligence = {
        "action_occurrence_structure": {
            "occurrence_candidates": occurrences.get(
                "action_occurrence_candidate_count"
            ),
            "claim_ceiling": "ACTION_OCCURRENCE_CANDIDATE_ONLY",
        },
        "visible_consequence": {
            "occurrence_projection_count": occurrence.get(
                "occurrence_consequence_projection_count"
            ),
            "admitted_visible_followup": (
                occurrence.get("followup_observation_status_counts") or {}
            ).get("VISIBLE_FOLLOWUP"),
            "broader_visible_support": occurrence.get(
                "occurrence_with_visible_consequence_support_count"
            ),
        },
        "censoring": {
            "fully_observed_no_followup": occurrence.get(
                "complete_to_declared_horizon_no_admitted_followup_count"
            ),
            "unresolved": (
                occurrence.get("followup_observation_status_counts") or {}
            ).get("FOLLOWUP_UNRESOLVED"),
            "right_censored": occurrence.get("right_censored_occurrence_count"),
        },
        "partial_order_sequences": {
            "sequence_candidates": sequence.get(
                "occurrence_temporal_sequence_candidate_count"
            ),
            "partial_order_variants": sequence.get(
                "partial_order_occurrence_variant_count"
            ),
            "branch_maps": sequence.get(
                "anchor_centered_sequence_branch_map_count"
            ),
            "first_supported_divergence_candidates": sequence.get(
                "first_supported_branch_divergence_candidate_count"
            ),
            "same_time_total_order_claim": False,
        },
        "comparison": {
            "eligible_outcome_records": sequence.get(
                "comparison_eligible_outcome_record_count"
            ),
            "comparable_counterevidence_candidates": sequence.get(
                "comparable_counterevidence_candidate_count"
            ),
            "process_variant_families": process.get(
                "observable_process_variant_family_count"
            ),
            "grammar_stable_mixed_outcome_families": delta.get(
                "grammar_stable_variant_feature_delta_record_count"
            ),
        },
        "safe_findings": {
            "evaluation_state": finding_accounting[
                "finding_evaluation_state"
            ],
            "decision_count": finding_accounting["safe_decision_count"],
            "status_counts": finding_accounting["safe_status_counts"],
            "professional_finding_emitted_count": finding_accounting[
                "professional_finding_emitted_count"
            ],
            "professional_emit_allowed": finding_accounting[
                "professional_emit_allowed"
            ],
            "claim_contract_current_run": finding_accounting["claim_current"],
            "claim_contract_evaluation_state": finding_accounting[
                "claim_evaluation_state"
            ],
            "claim_contract_safe_finding_consumed": finding_accounting[
                "claim_safe_finding_consumed"
            ],
            "claim_contract_decision_counts": finding_accounting[
                "claim_decision_counts"
            ],
            "claim_contract_count": finding_accounting["claim_contract_count"],
        },
        "claim_ceiling": "ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
    }

    layers = [
        "occurrence admission",
        "partial-order sequence",
        "comparison eligibility",
        "process variant binding",
        "feature delta",
        "counterevidence/challenge",
    ]
    if finding_accounting["safe_current"]:
        layers.append("safe finding admission")
    if finding_accounting["claim_current"]:
        layers.append("claim contract")

    system_value = {
        "raw_provider_data_does_not_directly_state": [
            "which visible occurrences belong to comparison-eligible partial-order grammar families",
            "where matched success/failure variants first expose bounded context/consequence differences",
            "which occurrence consequences are fully observed, horizon-sensitive, unresolved or right-censored",
            "which candidate differences survive claim guards only as analyst-review cues",
        ],
        "layers_creating_incremental_intelligence": layers,
        "highest_current_analyst_value_layer": (
            "matched success/failure process-variant review with exact "
            "video/match locators and explicit claim ceiling"
        ),
        "canonical_full_spine_safe_finding_scope": finding_accounting[
            "finding_evaluation_state"
        ],
        "exact_head_wrapper_may_own_post_sequence_safe_finding": True,
        "duplicate_or_low_incremental_value_candidates": [
            "same-provider multiformat reflections when treated only as repeated coverage",
            "human summary fields that duplicate machine counts without consistency checking",
        ],
    }

    gaps: list[dict[str, Any]] = []
    if consistency[0]["status"] != "PASS":
        gaps.append(
            {
                "priority": "HIGH",
                "current_symptom": (
                    "machine full-spine and human report disagree on "
                    "intelligence_chain_count"
                ),
                "blocked_football_question": (
                    "Which system layers actually ran and produced the "
                    "analyst-facing knowledge?"
                ),
                "missing": "cross-artifact diagnostic accounting contract",
                "rehabilitate": "active_match_spine_runner standard output/accounting",
                "smallest_path": (
                    "cross-check machine and human counts from the same current run"
                ),
                "test_needed": "machine/human count agreement",
                "active_match_needed": True,
                "expected_analyst_gain": (
                    "trustworthy system map and current-run football intelligence"
                ),
            }
        )
    if consistency[1]["status"] != "PASS":
        gaps.append(
            {
                "priority": "HIGH",
                "current_symptom": (
                    "variant challenge current-run ledger/count accounting is open"
                ),
                "blocked_football_question": (
                    "Was the challenge layer actually part of this exact run?"
                ),
                "missing": "current-run challenge ledger closure",
                "rehabilitate": (
                    "existing variant feature challenge runtime binding / producer ledger"
                ),
                "smallest_path": (
                    "declare materialized challenge artifact and verify count equality"
                ),
                "test_needed": "artifact ledger closure and count equality",
                "active_match_needed": True,
                "expected_analyst_gain": (
                    "no stale/current ambiguity immediately before finding admission"
                ),
            }
        )
    if finding_accounting["safe_current"]:
        emitted = finding_accounting["professional_finding_emitted_count"]
        if emitted == 0:
            gaps.append(
                {
                    "priority": "HIGH",
                    "current_symptom": (
                        "Safe Finding was evaluated but no professional finding was emitted"
                    ),
                    "blocked_football_question": (
                        "Which repeated process difference is strong enough to "
                        "become a professional match finding?"
                    ),
                    "missing": (
                        "evidence sufficiency/independence and comparable "
                        "outcome counterevidence admission"
                    ),
                    "rehabilitate": (
                        "existing safe-finding / challenge / support-spread chain"
                    ),
                    "smallest_path": (
                        "make sufficiency coverage and dependency burden explicit before EMIT"
                    ),
                    "test_needed": (
                        "EMIT cannot occur from dependent reflection or raw rates"
                    ),
                    "active_match_needed": True,
                    "expected_analyst_gain": (
                        "first defensible professional finding without lowering claim discipline"
                    ),
                }
            )

    gaps.extend(
        [
            {
                "priority": "MEDIUM",
                "current_symptom": (
                    "non-actor admitted context coverage remains limited across "
                    "matched process-variant families"
                ),
                "blocked_football_question": (
                    "What visible contextual difference distinguishes success "
                    "and failure beyond actor identity?"
                ),
                "missing": (
                    "admitted context coverage compatible with current observations"
                ),
                "rehabilitate": (
                    "existing process participation + occurrence-state context producers"
                ),
                "smallest_path": (
                    "expand admitted non-actor context only where source semantics "
                    "and dependency are explicit"
                ),
                "test_needed": (
                    "provider label never promoted to tactical/causal truth"
                ),
                "active_match_needed": True,
                "expected_analyst_gain": (
                    "better review hypotheses and fewer actor-only locators"
                ),
            },
            {
                "priority": "LOW",
                "current_symptom": "tracking/video absent",
                "blocked_football_question": (
                    "What physical/off-ball geometry caused the observed process difference?"
                ),
                "missing": "tracking/video observation family and implementation",
                "rehabilitate": "none in current single-match product",
                "smallest_path": (
                    "LATER unless project explicitly opens tracking/video capability"
                ),
                "test_needed": "no tracking claim without tracking",
                "active_match_needed": False,
                "expected_analyst_gain": (
                    "potentially high later, but poor current observation fit"
                ),
            },
        ]
    )

    safeguards = {
        "every_intended_stage_enumerated": True,
        "blocked_components_visible": True,
        "unavailable_prerequisites_not_silently_dropped": True,
        "fail_closed_never_pass": all(
            component["status"] != "PASS"
            for component in components
            if component.get("producer_status") == "FAIL_CLOSED"
        ),
        "repository_presence_is_execution": False,
        "artifact_presence_is_current_run_execution": False,
        "test_pass_is_runtime_execution": False,
        "same_time_unordered_preserved": bool(
            windows.get("same_time_unordered_bucket_count", 0)
        )
        or sequence.get(
            "same_timestamp_internal_ordering_used_for_first_difference"
        )
        is False,
        "tracking_video_claims_without_surface_allowed": False,
        "provider_process_annotation_is_tactical_truth": False,
        "percentages_require_numerator_denominator": True,
        "reflection_dependency_is_independence": False,
        "absence_is_counterevidence": False,
        "not_evaluated_is_downgrade": False,
        "zero_professional_emit_is_valid": True,
        "human_report_may_exceed_machine_claim_ceiling": False,
        "diagnostic_creates_new_evidence": False,
    }

    return {
        "module_id": MODULE_ID,
        "status": (
            "REVIEW_REQUIRED"
            if any(row["status"] == "REVIEW_REQUIRED" for row in consistency)
            or str(full.get("status") or "").upper() == "REVIEW_REQUIRED"
            else "PASS"
        ),
        "decision": "FULL_SYSTEM_MATCH_DIAGNOSTIC_ACCOUNTED",
        "run_identity": run_identity,
        "component_coverage": components,
        "component_status_counts": dict(
            Counter(component["status"] for component in components)
        ),
        "runtime_execution_state_counts": dict(
            Counter(
                component["runtime_execution_state"] for component in components
            )
        ),
        "engineering_test_state_counts": dict(
            Counter(
                component["engineering_test_state"] for component in components
            )
        ),
        "result_state_counts": dict(
            Counter(component["result_state"] for component in components)
        ),
        "engineering_test_evidence": {
            "state": "UNKNOWN",
            "reason": (
                "runtime diagnostic does not convert repository presence or CI "
                "history into per-component engineering test proof"
            ),
        },
        "observation_capability_coverage": capabilities,
        "evidence_spine_coverage": evidence_spine,
        "cross_artifact_consistency": consistency,
        "match_football_intelligence": match_intelligence,
        "top_defensible_process_mechanism_candidates": _top_mechanism_candidates(
            root
        ),
        "system_value_report": system_value,
        "gap_report": gaps,
        "diagnostic_safeguards": safeguards,
        "canonical_event_count": UNKNOWN,
        "true_action_count": UNKNOWN,
        "production_release": False,
    }


def _render_text(diagnostic: dict[str, Any]) -> str:
    run_identity = diagnostic["run_identity"]
    match_intelligence = diagnostic["match_football_intelligence"]
    safe_findings = match_intelligence["safe_findings"]
    lines = [
        "HPFA FULL SYSTEM MATCH DIAGNOSTIC V1",
        "====================================",
        f"status={diagnostic['status']}",
        f"head={run_identity['head']}",
        f"branch={run_identity['branch']}",
        f"pr={run_identity['pr']}",
        f"runtime_authority={run_identity['runtime_authority']}",
        f"match_identity_candidate={run_identity['match_identity_candidate']}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
        "[1] NE YAPILDI?",
        (
            "Mevcut full-spine yeni futbol gercegi uretmeden "
            "accounting/coverage acisindan denetlendi. Artifact varligi ile "
            "current-run execution ayrildi."
        ),
        "",
        "[2] SISTEM CALISMA KAPSAMI",
        "runtime_execution_state_counts="
        + json.dumps(
            diagnostic["runtime_execution_state_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "engineering_test_state_counts="
        + json.dumps(
            diagnostic["engineering_test_state_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "result_state_counts="
        + json.dumps(
            diagnostic["result_state_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "",
        "cross_artifact_consistency:",
    ]
    for row in diagnostic["cross_artifact_consistency"]:
        lines.append(
            f"- {row['check']}: {row['status']} | "
            f"{row.get('reason') or 'consistent'}"
        )

    lines.extend(
        [
            "",
            "[3] BU MACTA HPFA NE GORDU?",
            (
                "action_occurrence_candidates="
                f"{match_intelligence['action_occurrence_structure']['occurrence_candidates']}"
            ),
            (
                "visible_followup="
                f"{match_intelligence['visible_consequence']['admitted_visible_followup']}"
            ),
            (
                "broader_visible_consequence_support="
                f"{match_intelligence['visible_consequence']['broader_visible_support']}"
            ),
            (
                "partial_order_sequence_candidates="
                f"{match_intelligence['partial_order_sequences']['sequence_candidates']}"
            ),
            (
                "branch_maps="
                f"{match_intelligence['partial_order_sequences']['branch_maps']}"
            ),
            (
                "first_supported_divergence_candidates="
                f"{match_intelligence['partial_order_sequences']['first_supported_divergence_candidates']}"
            ),
            (
                "comparison_eligible_outcome_records="
                f"{match_intelligence['comparison']['eligible_outcome_records']}"
            ),
            (
                "process_variant_families="
                f"{match_intelligence['comparison']['process_variant_families']}"
            ),
            (
                "grammar_stable_mixed_outcome_families="
                f"{match_intelligence['comparison']['grammar_stable_mixed_outcome_families']}"
            ),
            (
                "safe_finding_evaluation_state="
                f"{safe_findings['evaluation_state']}"
            ),
            "safe_finding_status_counts="
            + json.dumps(
                safe_findings["status_counts"],
                ensure_ascii=False,
                sort_keys=True,
            ),
            (
                "claim_contract_evaluation_state="
                f"{safe_findings['claim_contract_evaluation_state']}"
            ),
            "claim_contract_decision_counts="
            + json.dumps(
                safe_findings["claim_contract_decision_counts"],
                ensure_ascii=False,
                sort_keys=True,
            ),
            (
                "professional_finding_emitted_count="
                f"{safe_findings['professional_finding_emitted_count']}"
            ),
            "",
            "[4] EN GUCLU SAVUNULABILIR REVIEW ADAYLARI",
        ]
    )
    for idx, row in enumerate(
        diagnostic["top_defensible_process_mechanism_candidates"], 1
    ):
        lines.append(
            f"- C{idx}: resolved={row['resolved_variant_count']} "
            f"success={row['success_variant_count']} "
            f"failure={row['failure_variant_count']} "
            f"claim_ceiling={row['claim_ceiling']} "
            f"independence={str(row['dependency_independence_proven']).lower()}"
        )
        provider_context = row.get(
            "best_provider_reviewed_process_context_difference"
        )
        if isinstance(provider_context, dict):
            lines.append(
                "  provider_reviewed_context="
                + str(provider_context.get("feature_token"))
                + (
                    f" success={provider_context.get('success_visible_numerator')}/"
                    f"{provider_context.get('success_eligible_denominator')}"
                )
                + (
                    f" failure={provider_context.get('failure_visible_numerator')}/"
                    f"{provider_context.get('failure_eligible_denominator')}"
                )
                + " tactical_truth=false causal_truth=false"
            )

    lines.extend(
        [
            "",
            "[5] SISTEM NEREDE KOR?",
            (
                "- Tracking/video yok: physical geometry, off-ball structure, "
                "body orientation, scanning, true pressure geometry ve coach "
                "intention kanitlanamaz."
            ),
            (
                "- External context surface yok: mevcut context "
                "provider-reviewed/derived sinirinda."
            ),
        ]
    )
    if safe_findings["evaluation_state"] == "EXECUTED":
        lines.append(
            "- Safe Finding bu kosuda degerlendirildi; EMIT/DOWNGRADE sonucu "
            "yalniz current-run admission evidence ile yorumlanir."
        )
    else:
        lines.append(
            "- Safe Finding admission bu canonical run'da NOT_BOUND_CURRENT_RUN; "
            "NOT_EVALUATED bir DOWNGRADE sonucu degildir."
        )

    lines.extend(["", "[6] EN DEGERLI SONRAKI GELISTIRME"])
    for gap in diagnostic["gap_report"][:4]:
        lines.append(
            f"- {gap['priority']}: {gap['current_symptom']} -> "
            f"{gap['smallest_path']}"
        )
    lines.extend(
        [
            "",
            "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
            "diagnostic_creates_new_evidence=false",
            "END OF DIAGNOSTIC",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(
    root: Path, diagnostic: dict[str, Any]
) -> tuple[Path, Path]:
    out_json = root / OUTPUT_JSON
    out_txt = root / OUTPUT_TXT
    out_json.write_text(
        json.dumps(
            diagnostic,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    out_txt.write_text(_render_text(diagnostic), encoding="utf-8")
    return out_json, out_txt


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Account for the current HPFA ACTIVE_MATCH full-spine run "
            "without creating new evidence."
        )
    )
    parser.add_argument("out_dir")
    parser.add_argument("--repository", default="Hikmetpinarbas/hpfa")
    parser.add_argument("--branch")
    parser.add_argument("--pr")
    parser.add_argument("--head")
    args = parser.parse_args()
    root = Path(args.out_dir).expanduser().resolve(strict=False)
    full = _load_json(root, "active_match_full_spine_v1.json")
    if not full:
        raise SystemExit("active_match_full_spine_v1.json missing or unreadable")
    diagnostic = build_diagnostic(
        root,
        repository=args.repository,
        branch=args.branch,
        pr=args.pr,
        head=args.head,
    )
    out_json, out_txt = write_outputs(root, diagnostic)
    print(
        json.dumps(
            {
                "status": diagnostic["status"],
                "out_json": str(out_json),
                "out_txt": str(out_txt),
                "production_release": False,
            },
            ensure_ascii=False,
        )
    )
    return 0 if diagnostic["status"] in {"PASS", "REVIEW_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

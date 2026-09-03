from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

MODULE_ID = "reciprocal_full_spine_packet_bridge_v1"
OUTPUT_JSON = "reciprocal_full_spine_packet_bridge_v1.json"
OUTPUT_TXT = "reciprocal_full_spine_packet_bridge_v1.txt"
EXPECTED_COUNTER_SEARCH_SCOPE = "SAME_ADMITTED_PROCESS_FAMILY_SIGNATURE_ONLY"
EXPECTED_COUNTER_SEARCH_EVALUATED_FAMILIES = ["DIRECT_VISIBLE_OUTCOME_CONTRAST"]
EXPECTED_COUNTER_SEARCH_PENDING_FAMILIES = [
    "CONTEXT_DEPENDENCE",
    "SEGMENT_ONLY",
    "PLAYER_OUTLIER",
    "THRESHOLD_SENSITIVITY",
    "OPPONENT_SYMMETRY",
    "FAILED_TRACE_SUPPORT",
    "DUPLICATE_REFLECTION_RISK",
    "ALTERNATIVE_EXPLANATION",
]
ALLOWED_COUNTER_SEARCH_SCOPE_STATES = {
    "PARTIAL_SCOPE_EVALUATED",
    "PARTIAL_SCOPE_EVALUATED_NO_ANALOGUE",
}
CLAIM_SAFETY_REQUIRED_KEYS = {
    "counter_search_scope",
    "counter_search_scope_state",
    "counter_search_peer_count",
    "counter_search_evaluated_families",
    "counter_search_pending_families",
    "counter_search_complete_for_final_finding",
    "alternative_explanation_search_state",
    "alternative_explanation_required",
    "falsifier_coverage_state",
    "falsifier_families_evaluated",
    "falsifier_families_pending",
    "no_visible_counterexample_is_confirmation",
    "support_links_are_independent_votes",
    "counterevidence_links_are_independent_votes",
    "withdrawal_condition",
    "finding_emitted",
    "claim_safety_metadata_is_truth_claim",
}
CLAIM_SAFETY_STAGE_NAMES = (
    "fusion",
    "argument",
    "route",
    "graph",
    "lens",
    "safe_sentence",
    "report_block",
    "output_contract",
    "assembly",
)


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _same_members(value: Any, expected: list[str]) -> bool:
    if not isinstance(value, list) or len(value) != len(expected):
        return False
    cleaned = [str(item) for item in value]
    return len(set(cleaned)) == len(cleaned) and sorted(cleaned) == sorted(expected)


def _claim_safety_metadata(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    raw = candidate.get("claim_safety_metadata")
    if not isinstance(raw, dict):
        return None, ["reciprocal_claim_safety_metadata_missing_or_invalid"]
    missing = sorted(key for key in CLAIM_SAFETY_REQUIRED_KEYS if key not in raw)
    errors = [f"reciprocal_claim_safety_metadata_missing:{key}" for key in missing]

    scope = str(raw.get("counter_search_scope") or "")
    scope_state = str(raw.get("counter_search_scope_state") or "")
    peer_count = raw.get("counter_search_peer_count")
    if scope != EXPECTED_COUNTER_SEARCH_SCOPE:
        errors.append("reciprocal_counter_search_scope_promoted_or_invalid")
    if scope_state not in ALLOWED_COUNTER_SEARCH_SCOPE_STATES:
        errors.append("reciprocal_counter_search_scope_state_promoted_or_invalid")
    if isinstance(peer_count, bool) or not isinstance(peer_count, int) or peer_count < 0:
        errors.append("reciprocal_counter_search_peer_count_invalid")
    elif scope_state == "PARTIAL_SCOPE_EVALUATED_NO_ANALOGUE" and peer_count != 0:
        errors.append("reciprocal_counter_search_no_analogue_peer_count_mismatch")
    elif scope_state == "PARTIAL_SCOPE_EVALUATED" and peer_count <= 0:
        errors.append("reciprocal_counter_search_evaluated_peer_count_missing")

    if not _same_members(
        raw.get("counter_search_evaluated_families"),
        EXPECTED_COUNTER_SEARCH_EVALUATED_FAMILIES,
    ):
        errors.append("reciprocal_counter_search_evaluated_families_promoted_or_invalid")
    if not _same_members(
        raw.get("counter_search_pending_families"),
        EXPECTED_COUNTER_SEARCH_PENDING_FAMILIES,
    ):
        errors.append("reciprocal_counter_search_pending_families_promoted_or_invalid")
    if raw.get("counter_search_complete_for_final_finding") is not False:
        errors.append("reciprocal_counter_search_completeness_lock_breached")
    if str(raw.get("alternative_explanation_search_state") or "") != "NOT_EVALUATED":
        errors.append("reciprocal_alternative_explanation_state_promoted")
    if raw.get("alternative_explanation_required") is not True:
        errors.append("reciprocal_alternative_explanation_requirement_removed")
    if str(raw.get("falsifier_coverage_state") or "") != "PARTIAL":
        errors.append("reciprocal_falsifier_coverage_promoted")
    if not _same_members(
        raw.get("falsifier_families_evaluated"),
        EXPECTED_COUNTER_SEARCH_EVALUATED_FAMILIES,
    ):
        errors.append("reciprocal_falsifier_evaluated_families_promoted_or_invalid")
    if not _same_members(
        raw.get("falsifier_families_pending"),
        EXPECTED_COUNTER_SEARCH_PENDING_FAMILIES,
    ):
        errors.append("reciprocal_falsifier_pending_families_promoted_or_invalid")
    if raw.get("no_visible_counterexample_is_confirmation") is not False:
        errors.append("reciprocal_no_counterexample_confirmation_lock_breached")
    if raw.get("support_links_are_independent_votes") is not False:
        errors.append("reciprocal_dependent_support_independence_lock_breached")
    if raw.get("counterevidence_links_are_independent_votes") is not False:
        errors.append("reciprocal_counterevidence_independence_lock_breached")
    if not str(raw.get("withdrawal_condition") or "").strip():
        errors.append("reciprocal_withdrawal_condition_missing")
    if raw.get("finding_emitted") is not False:
        errors.append("reciprocal_final_finding_lock_breached")
    if raw.get("claim_safety_metadata_is_truth_claim") is not False:
        errors.append("reciprocal_claim_safety_metadata_promoted_to_truth")

    if errors:
        return None, sorted(set(errors))
    return json.loads(json.dumps(raw, ensure_ascii=False, sort_keys=True)), []


def _audit_claim_safety_metadata(chain: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    packet = chain.get("packet")
    if not isinstance(packet, dict):
        errors.append("claim_safety_stage_missing_or_invalid:packet")
    elif packet.get("claim_safety_metadata") != metadata:
        errors.append("claim_safety_metadata_not_preserved:packet")
    for stage_name in CLAIM_SAFETY_STAGE_NAMES:
        stage = chain.get(stage_name)
        if not isinstance(stage, dict):
            errors.append(f"claim_safety_stage_missing_or_invalid:{stage_name}")
            continue
        if stage.get("claim_safety_metadata") != metadata:
            errors.append(f"claim_safety_metadata_not_preserved:{stage_name}")
    return sorted(set(errors))


def _build_tomography_coverage(reciprocal: dict[str, Any], chains: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize defeasible reciprocal coverage without producing a finding.

    This is an accounting surface over already-produced finding inputs. It does not
    interpret absence as support, does not count dependent analogues as independent
    votes and does not promote any C4/report claim.
    """
    rows = reciprocal.get("defeasible_process_finding_inputs") or []
    rows = rows if isinstance(rows, list) else []
    states: Counter[str] = Counter()
    search_scope_states: Counter[str] = Counter()
    with_counterevidence = 0
    with_dependent_support = 0
    isolated = 0
    counter_search_complete = 0
    counter_search_incomplete = 0
    alternative_not_evaluated = 0
    partial_falsifier_coverage = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("evidence_balance_state_candidate") or "UNKNOWN")
        states[state] += 1
        search_scope_state = str(row.get("counter_search_scope_state") or "UNKNOWN")
        search_scope_states[search_scope_state] += 1
        counter_ids = row.get("counterevidence_chain_ids") or []
        support_ids = row.get("dependent_support_chain_ids") or []
        if isinstance(counter_ids, list) and counter_ids:
            with_counterevidence += 1
        if isinstance(support_ids, list) and support_ids:
            with_dependent_support += 1
        if not counter_ids and not support_ids:
            isolated += 1
        if row.get("counter_search_complete_for_final_finding") is True:
            counter_search_complete += 1
        else:
            counter_search_incomplete += 1
        if str(row.get("alternative_explanation_search_state") or "UNKNOWN") != "EVALUATED":
            alternative_not_evaluated += 1
        if str(row.get("falsifier_coverage_state") or "UNKNOWN") == "PARTIAL":
            partial_falsifier_coverage += 1

    return {
        "surface_id": "reciprocal_match_tomography_coverage_v1",
        "status": "REVIEW_REQUIRED",
        "finding_input_count": len(rows),
        "finding_inputs_with_counterevidence_count": with_counterevidence,
        "finding_inputs_with_dependent_support_count": with_dependent_support,
        "isolated_finding_input_count": isolated,
        "evidence_balance_state_candidate_counts": dict(sorted(states.items())),
        "counter_search_scope_state_counts": dict(sorted(search_scope_states.items())),
        "counter_search_complete_for_final_finding_count": counter_search_complete,
        "counter_search_incomplete_for_final_finding_count": counter_search_incomplete,
        "alternative_explanation_not_evaluated_count": alternative_not_evaluated,
        "partial_falsifier_coverage_count": partial_falsifier_coverage,
        "existing_intelligence_chain_projection_count": len(chains),
        "absence_of_counterevidence_is_confirmation": False,
        "counter_search_incomplete_never_confirms": True,
        "alternative_explanation_absence_is_not_evidence": True,
        "dependent_support_is_independent_vote": False,
        "coverage_is_team_tendency_truth": False,
        "coverage_is_tactical_truth": False,
        "coverage_is_causal_truth": False,
        "finding_emitted": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def bridge_reciprocal_packets(
    *,
    active_match_dir: str | Path,
    out_dir: str | Path,
    reciprocal_runner: Callable[[str | Path, str | Path], dict[str, Any]],
    packet_builder: Callable[[dict[str, Any]], dict[str, Any]],
    intelligence_runner: Callable[[dict[str, Any]], dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Project current reciprocal C4 candidates through the existing intelligence chain.

    This bridge creates no occurrences, episodes, evidence votes or reasoning engine.
    It only invokes already-existing producers and records whether their candidate
    packets can traverse the current C4 chain without opening claim ceilings.
    """
    output_root = Path(out_dir).expanduser().resolve(strict=False)
    output_root.mkdir(parents=True, exist_ok=True)

    reciprocal = reciprocal_runner(active_match_dir, output_root)
    reciprocal_status = _status(reciprocal.get("status"))
    candidates = reciprocal.get("reciprocal_c4_packet_candidates") or []
    if not isinstance(candidates, list):
        candidates = []

    hard_blocks: list[str] = []
    review_hits: list[str] = []
    chains: list[dict[str, Any]] = []
    packet_count = 0
    safety_metadata_preserved_count = 0

    if reciprocal_status == "FAIL_CLOSED":
        hard_blocks.append("reciprocal_process_chain_fail_closed")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                review_hits.append("non_object_reciprocal_c4_candidate_ignored")
                continue
            safety_metadata, safety_errors = _claim_safety_metadata(candidate)
            if safety_errors or safety_metadata is None:
                hard_blocks.extend(safety_errors or ["reciprocal_claim_safety_metadata_missing_or_invalid"])
                break
            packet = packet_builder(candidate)
            if not isinstance(packet, dict):
                hard_blocks.append("existing_packet_builder_returned_non_object")
                break
            if packet.get("hard_block_hits"):
                review_hits.append("reciprocal_packet_not_admitted_by_existing_packet_builder")
                continue

            packet["claim_safety_metadata"] = json.loads(
                json.dumps(safety_metadata, ensure_ascii=False, sort_keys=True)
            )
            chain = intelligence_runner(packet)
            if not isinstance(chain, dict):
                hard_blocks.append("existing_intelligence_runner_returned_non_object")
                break
            safety_stage_errors = _audit_claim_safety_metadata(chain, safety_metadata)
            if safety_stage_errors:
                hard_blocks.extend(safety_stage_errors)
                break
            chains.append({
                "candidate_id": candidate.get("candidate_id") or candidate.get("finding_input_id"),
                "claim_safety_metadata": safety_metadata,
                "packet": packet,
                "chain": chain,
            })
            packet_count += 1
            safety_metadata_preserved_count += 1

    claim_output_allowed_count = 0
    completed_chain_count = 0
    for row in chains:
        chain = row.get("chain") or {}
        assembly = chain.get("assembly") if isinstance(chain, dict) else None
        output_contract = chain.get("output_contract") if isinstance(chain, dict) else None
        if isinstance(output_contract, dict) and output_contract.get("claim_output_allowed") is True:
            claim_output_allowed_count += 1
        if isinstance(assembly, dict) and _status(assembly.get("status")) not in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"}:
            completed_chain_count += 1

    tomography_coverage = _build_tomography_coverage(reciprocal, chains)
    status = "FAIL_CLOSED" if hard_blocks else "REVIEW_REQUIRED"
    report = {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "BLOCK_MATCH_TOMOGRAPHY_BRIDGE" if hard_blocks else "RECIPROCAL_MATCH_TOMOGRAPHY_CANDIDATES_PROJECTED",
        "reciprocal_process_status": reciprocal.get("status"),
        "reciprocal_process_chain_candidate_count": reciprocal.get("reciprocal_process_chain_candidate_count"),
        "outcome_contrast_candidate_count": reciprocal.get("outcome_contrast_candidate_count"),
        "different_outcome_analogue_link_count": reciprocal.get("different_outcome_analogue_link_count"),
        "defeasible_process_finding_input_count": reciprocal.get("defeasible_process_finding_input_count"),
        "reciprocal_c4_packet_candidate_count": len(candidates),
        "existing_packet_builder_admitted_count": packet_count,
        "existing_intelligence_chain_completed_candidate_count": completed_chain_count,
        "claim_safety_metadata_preserved_candidate_count": safety_metadata_preserved_count,
        "claim_safety_metadata_required_for_reciprocal_c4": True,
        "claim_output_allowed_count": claim_output_allowed_count,
        "match_tomography_coverage": tomography_coverage,
        "chains": chains,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "creates_parallel_engine": False,
        "creates_occurrence": False,
        "creates_episode": False,
        "creates_independent_evidence": False,
        "creates_final_finding": False,
        "active_match_evidence_pass": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    json_path = output_root / OUTPUT_JSON
    txt_path = output_root / OUTPUT_TXT
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join([
        "HPFA RECIPROCAL FULL-SPINE PACKET BRIDGE V1",
        f"status={status}",
        f"reciprocal_c4_packet_candidate_count={len(candidates)}",
        f"existing_packet_builder_admitted_count={packet_count}",
        f"existing_intelligence_chain_completed_candidate_count={completed_chain_count}",
        f"claim_safety_metadata_preserved_candidate_count={safety_metadata_preserved_count}",
        f"claim_output_allowed_count={claim_output_allowed_count}",
        f"tomography_finding_input_count={tomography_coverage.get('finding_input_count', 0)}",
        f"tomography_with_counterevidence_count={tomography_coverage.get('finding_inputs_with_counterevidence_count', 0)}",
        f"tomography_with_dependent_support_count={tomography_coverage.get('finding_inputs_with_dependent_support_count', 0)}",
        f"tomography_isolated_count={tomography_coverage.get('isolated_finding_input_count', 0)}",
        f"tomography_counter_search_incomplete_count={tomography_coverage.get('counter_search_incomplete_for_final_finding_count', 0)}",
        f"tomography_alternative_explanation_not_evaluated_count={tomography_coverage.get('alternative_explanation_not_evaluated_count', 0)}",
        f"tomography_partial_falsifier_coverage_count={tomography_coverage.get('partial_falsifier_coverage_count', 0)}",
        "tomography_claim_output_allowed=false",
        "creates_parallel_engine=false",
        "active_match_evidence_pass=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    report["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return report

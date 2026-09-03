import active_match_spine_runner as active_entrypoint
from hpfa.modules.core.active_match_spine_runner.src import full_spine_runner as full_spine_module
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet
from hpfa.modules.core.reciprocal_process_chain_lite.src.outcome_contrast import (
    build_c4_packet_candidates,
    build_defeasible_process_finding_inputs,
    build_outcome_contrast_candidates,
)


def _chain(chain_id: str, consequence: str, counter_visible: bool) -> dict:
    return {
        "reciprocal_process_chain_candidate_id": chain_id,
        "anchor_action_family_counts": {"RECOVERY": 1},
        "response_action_family_counts": {"PASS": 1},
        "response_consequence_candidate_counts": {consequence: 1},
        "counter_response_consequence_candidate_counts": ({"SHOT_CANDIDATE": 1} if counter_visible else {}),
        "counter_response_visible": counter_visible,
    }


def _payload() -> dict:
    rows = [
        _chain("rpc_support", "SAME_TEAM_CONTINUATION_CANDIDATE", True),
        _chain("rpc_counter", "TURNOVER_CANDIDATE", False),
    ]
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": rows,
        "reciprocal_process_chain_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_reciprocal_counterevidence_can_traverse_existing_match_tomography_chain_without_claim_promotion() -> None:
    contrast = build_outcome_contrast_candidates(_payload())
    finding_inputs = build_defeasible_process_finding_inputs(contrast)
    candidates = build_c4_packet_candidates(finding_inputs)["reciprocal_c4_packet_candidates"]
    assert candidates

    candidate = candidates[0]
    packet = build_composite_packet(candidate)
    assert packet["status"] == "SMOKE_PASS"
    assert packet["independent_support_count"] == 0

    metadata = candidate["claim_safety_metadata"]
    packet["claim_safety_metadata"] = metadata
    active_entrypoint._bind_claim_safety_stage_passthrough()
    chain = full_spine_module.run_intelligence_chain(packet)
    for stage in ("packet", "fusion", "argument", "route", "graph", "lens", "safe_sentence", "report_block", "output_contract", "assembly"):
        assert stage in chain
        assert chain[stage].get("status") not in {"FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED"}
        assert chain[stage].get("claim_safety_metadata") == metadata

    fusion = chain["fusion"]
    assert any(
        relation.get("relation_type") == "CONTRADICTS"
        for relation in fusion.get("relation_records") or []
    )
    assert fusion["claim_output_allowed"] is False

    report_block = chain["report_block"]
    assert report_block.get("production_release") is False
    assert report_block.get("canonical_event_count") == "UNKNOWN"
    assert report_block.get("true_action_count") == "UNKNOWN"

    assembly = chain["assembly"]
    assert assembly.get("production_release") is False


def test_match_tomography_bridge_does_not_create_parallel_reasoning_engine_or_truth_claims() -> None:
    contrast = build_outcome_contrast_candidates(_payload())
    finding_inputs = build_defeasible_process_finding_inputs(contrast)
    candidate = build_c4_packet_candidates(finding_inputs)["reciprocal_c4_packet_candidates"][0]
    assert candidate["finding_emitted"] is False
    assert candidate["claim_output_allowed"] is False
    assert candidate["report_language_allowed"] is False
    assert candidate["dependent_support_only"] is True
    assert candidate["counterevidence_is_dependent_projection"] is True
    assert candidate["claim_safety_metadata"]["counter_search_complete_for_final_finding"] is False
    assert candidate["claim_safety_metadata"]["alternative_explanation_required"] is True
    assert candidate["canonical_event_count"] == "UNKNOWN"
    assert candidate["true_action_count"] == "UNKNOWN"
    assert candidate["production_release"] is False

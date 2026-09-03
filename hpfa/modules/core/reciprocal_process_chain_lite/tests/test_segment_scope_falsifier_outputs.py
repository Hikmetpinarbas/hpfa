from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import (
    bridge_reciprocal_packets,
)
from hpfa.modules.core.reciprocal_process_chain_lite.src.segment_scope_falsifier_outputs import (
    ANALYST_TXT,
    OUTPUT_JSON,
    OUTPUT_TXT,
    write_outputs,
)


def _payload():
    return {
        "segment_only_evaluations": [
            {
                "process_family_signature_candidate": {
                    "anchor_action_families": ["PASS", "TURNOVER"],
                    "response_action_families": ["PASS"],
                },
                "segment_only_evaluation_state": "SINGLE_EPISODE_SCOPE_ONLY_CANDIDATE",
                "segment_only_falsifier_evaluable_from_current_episode_scope": True,
                "segment_only_risk_candidate": True,
                "visible_repeat_count_candidate": 3,
                "unique_episode_scope_count_candidate": 1,
            }
        ],
        "segment_only_falsifier_status": "EVALUATION_SURFACE_READY_REVIEW_REQUIRED",
        "segment_only_falsifier_evaluated_count": 1,
        "segment_only_risk_candidate_count": 1,
        "segment_only_multi_episode_not_observed_count": 0,
        "segment_only_pending_count": 0,
        "segment_only_safety_envelope_propagated": False,
        "counter_search_complete_for_final_finding": False,
        "falsifier_coverage_state": "PARTIAL",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_outputs_are_direct_root_and_preserve_claim_language(tmp_path: Path):
    paths = write_outputs(_payload(), tmp_path)
    assert paths["json"].name == OUTPUT_JSON
    assert paths["summary"].name == OUTPUT_TXT
    assert paths["analyst"].name == ANALYST_TXT
    assert all(path.parent == tmp_path for path in paths.values())
    analyst = paths["analyst"].read_text(encoding="utf-8")
    assert "does not remove SEGMENT_ONLY" in analyst
    assert "Multi-episode spread is not recurrence truth" in analyst
    assert "canonical_event_count=UNKNOWN" in analyst
    assert "true_action_count=UNKNOWN" in analyst
    assert "production_release=false" in analyst


def test_segment_outputs_are_producer_declared_to_parent_bridge_ledger(tmp_path: Path):
    payload = _payload()
    segment_paths = write_outputs(payload, tmp_path)

    def reciprocal_runner(_active_match_dir, _out_dir):
        return {
            "status": "PASS",
            "defeasible_process_finding_inputs": [],
            "reciprocal_c4_packet_candidates": [],
            "segment_only_falsifier_status": payload["segment_only_falsifier_status"],
            "segment_only_falsifier_evaluated_count": 1,
            "segment_only_risk_candidate_count": 1,
            "segment_only_multi_episode_not_observed_count": 0,
            "segment_only_pending_count": 0,
            "outputs": {f"segment_scope_{key}": str(path) for key, path in segment_paths.items()},
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=reciprocal_runner,
        packet_builder=lambda candidate: candidate,
        intelligence_runner=lambda packet: packet,
    )

    declared = {Path(value).name for value in report["current_invocation_artifacts"]}
    assert OUTPUT_JSON in declared
    assert OUTPUT_TXT in declared
    assert ANALYST_TXT in declared
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False

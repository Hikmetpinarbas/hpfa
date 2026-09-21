from __future__ import annotations

import json
from pathlib import Path

import safe_finding_admission_current_v1 as runtime


def test_process_context_is_applied_before_counterevidence_and_safe_finding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    sequence_path.write_text(
        json.dumps({
            "comparable_outcome_counterevidence_status": "PASS",
            "safe_finding_handoff_candidates": [
                {"safe_finding_handoff_candidate_id": "legacy_handoff"}
            ],
            "safe_finding_handoff_candidate_count": 1,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )
    (tmp_path / runtime.PROCESS_PARTICIPATION_NAME).write_text(
        json.dumps({
            "status": "PASS",
            "process_participation_candidates": [{"semantic_role": "CONTEXT_INTERVAL"}],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )
    (tmp_path / runtime.OCCURRENCE_CONSEQUENCE_NAME).write_text(
        json.dumps({
            "status": "PASS",
            "occurrence_consequence_projections": [{}],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )

    def fake_context(payload, process_payload, occurrence_payload, occurrence_state_payload=None):
        result = dict(payload)
        result["process_comparison_context_consumed"] = True
        result["process_comparison_context_binding_state"] = (
            "PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT_APPLIED_DOWNWARD_ONLY"
        )
        result["process_comparison_context_lowered_pair_count"] = 1
        result["process_comparison_context_can_create_new_pair"] = False
        return result

    def fake_counterevidence(payload):
        assert payload["process_comparison_context_consumed"] is True
        return {
            "status": "PASS",
            "comparable_outcome_counterevidence_records": [],
            "comparable_outcome_counterevidence_record_count": 0,
            "comparable_outcome_contrast_state_counts": {},
            "comparison_eligible_record_count": 0,
            "comparable_counterevidence_candidate_count": 0,
            "safe_finding_handoff_candidates": [],
            "safe_finding_handoff_candidate_count": 0,
            "safe_finding_handoff_finding_status_counts": {
                "EMIT": 0,
                "DOWNGRADE": 0,
                "ABSTAIN": 0,
            },
            "professional_finding_emitted_count": 0,
            "safe_finding_handoff_claim_ceiling": (
                "DOWNGRADED_MATCH_LOCAL_SAFE_FINDING_HANDOFF_CANDIDATE_ONLY"
            ),
            "claim_ceiling": (
                "MATCH_LOCAL_COMPARABLE_VISIBLE_OUTCOME_COUNTEREVIDENCE_CANDIDATE_ONLY"
            ),
        }

    monkeypatch.setattr(runtime, "apply_process_context_to_comparison", fake_context)
    monkeypatch.setattr(runtime, "build_comparable_outcome_counterevidence", fake_counterevidence)

    result = runtime.runtime_write_outputs(sequence_path, tmp_path)
    persisted = json.loads(sequence_path.read_text(encoding="utf-8"))

    assert result["process_comparison_context_consumed"] is True
    assert result["process_comparison_context_lowered_pair_count"] == 1
    assert result["process_context_counterevidence_recomputed"] is True
    assert result["process_context_can_create_new_pair"] is False
    assert persisted["safe_finding_handoff_candidate_count"] == 0
    assert persisted["safe_finding_handoff_candidates"] == []
    assert persisted["comparison_eligible_outcome_record_count"] == 0
    assert persisted["canonical_event_count"] == "UNKNOWN"
    assert persisted["true_action_count"] == "UNKNOWN"
    assert persisted["production_release"] is False

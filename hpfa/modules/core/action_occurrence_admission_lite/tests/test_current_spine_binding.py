from __future__ import annotations

from pathlib import Path


def test_current_trace_wrapper_is_occurrence_gated() -> None:
    source = Path("trackable_action_trace_candidates_current_v1.py").read_text(encoding="utf-8")
    assert "import action_occurrence_admission_current_v1 as current_occurrence" in source
    assert "occurrence_payload = current_occurrence.runtime_write_outputs" in source
    assert "current_occurrence_status" in source
    assert "current_occurrence_candidate_count" in source
    assert "current_cross_role_or_required_upstream_output_missing" not in source


def test_occurrence_current_wrapper_preserves_release_boundaries() -> None:
    source = Path("action_occurrence_admission_current_v1.py").read_text(encoding="utf-8")
    assert '"canonical_event_count": "UNKNOWN"' in source
    assert '"true_action_count": "UNKNOWN"' in source
    assert '"production_release": False' in source
    assert 'payload["active_match_evidence_pass"] = False' in source

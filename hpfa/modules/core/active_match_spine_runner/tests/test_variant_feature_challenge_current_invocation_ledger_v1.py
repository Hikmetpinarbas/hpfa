from __future__ import annotations

from pathlib import Path

import active_match_spine_runner as runner


def test_variant_challenge_materialization_closes_current_invocation_ledger(
    tmp_path: Path, monkeypatch
) -> None:
    challenge = tmp_path / "variant_feature_challenge_projection_v1.json"

    def fake_materialize(_out_dir):
        challenge.write_text("{}", encoding="utf-8")
        return {
            "status": "REVIEW_REQUIRED",
            "artifact_materialized": True,
            "output": str(challenge),
            "variant_feature_challenge_record_count": 467,
            "projection_creates_new_evidence": False,
            "professional_finding_emit_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    monkeypatch.setattr(runner, "materialize_variant_feature_challenge", fake_materialize)
    result = {
        "status": "REVIEW_REQUIRED",
        "current_invocation_artifacts": [str(tmp_path / "active_match_full_spine_v1.json")],
        "engineering_evidence": {},
    }

    runner._bind_variant_feature_challenge_runtime(result, tmp_path)

    artifacts = {Path(value).name for value in result["current_invocation_artifacts"]}
    assert "variant_feature_challenge_projection_v1.json" in artifacts
    assert result["variant_feature_challenge_runtime_binding"]["variant_feature_challenge_record_count"] == 467
    assert result["engineering_evidence"]["variant_feature_challenge_current_invocation_materialized"] is True
    assert result["engineering_evidence"]["variant_feature_challenge_creates_new_evidence"] is False
    assert result["engineering_evidence"]["variant_feature_challenge_can_authorize_emit"] is False


def test_variant_challenge_not_materialized_does_not_claim_current_invocation(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_materialize(_out_dir):
        return {
            "status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "artifact_materialized": False,
            "reason": "required_current_invocation_input_missing",
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    monkeypatch.setattr(runner, "materialize_variant_feature_challenge", fake_materialize)
    base = str(tmp_path / "active_match_full_spine_v1.json")
    result = {
        "status": "REVIEW_REQUIRED",
        "current_invocation_artifacts": [base],
        "engineering_evidence": {},
    }

    runner._bind_variant_feature_challenge_runtime(result, tmp_path)

    assert result["current_invocation_artifacts"] == [base]
    assert result["engineering_evidence"]["variant_feature_challenge_current_invocation_materialized"] is False

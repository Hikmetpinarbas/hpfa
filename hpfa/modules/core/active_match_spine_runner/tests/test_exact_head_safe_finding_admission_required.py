import json
from pathlib import Path

import active_match_exact_head_run_v1 as runner


def _admission(count: int) -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decision_count": count,
        "professional_finding_emitted_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _claim(count: int) -> dict:
    return {
        "status": "PASS",
        "analyst_output_contract_count": count,
        "safe_finding_admission_consumed": True,
        "professional_emit_allowed_count": 0,
        "professional_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_exact_head_acceptance_requires_post_sequence_admission_artifacts(tmp_path: Path) -> None:
    sequence = {"safe_finding_handoff_candidate_count": 2}
    admission = _admission(2)
    claim = _claim(2)
    post_sequence = {
        "status": "PASS",
        "safe_finding_admission": admission,
        "analyst_output_claim": claim,
    }

    (tmp_path / runner.SAFE_FINDING_ADMISSION_JSON).write_text("{}", encoding="utf-8")
    (tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON).write_text("{}", encoding="utf-8")

    assert runner._post_sequence_admission_ready(
        out_dir=tmp_path,
        sequence=sequence,
        post_sequence=post_sequence,
    ) is True

    (tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON).unlink()
    assert runner._post_sequence_admission_ready(
        out_dir=tmp_path,
        sequence=sequence,
        post_sequence=post_sequence,
    ) is False


def test_exact_head_acceptance_rejects_admission_count_mismatch(tmp_path: Path) -> None:
    (tmp_path / runner.SAFE_FINDING_ADMISSION_JSON).write_text("{}", encoding="utf-8")
    (tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON).write_text("{}", encoding="utf-8")

    assert runner._post_sequence_admission_ready(
        out_dir=tmp_path,
        sequence={"safe_finding_handoff_candidate_count": 2},
        post_sequence={
            "status": "PASS",
            "safe_finding_admission": _admission(1),
            "analyst_output_claim": _claim(2),
        },
    ) is False


def test_post_sequence_runner_uses_existing_sequence_artifact_only(monkeypatch, tmp_path: Path) -> None:
    sequence_path = tmp_path / runner.SEQUENCE_JSON
    sequence_path.write_text(json.dumps({"safe_finding_handoff_candidate_count": 0}), encoding="utf-8")
    calls = []

    def fake_admission(source, out_dir):
        calls.append(("admission", Path(source), Path(out_dir)))
        payload = _admission(0)
        (tmp_path / runner.SAFE_FINDING_ADMISSION_JSON).write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def fake_claim(sequence, admission, out_dir):
        calls.append(("claim", Path(sequence), Path(admission), Path(out_dir)))
        payload = _claim(0)
        (tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON).write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr(runner.safe_finding_runner, "runtime_write_outputs", fake_admission)
    monkeypatch.setattr(runner.claim_admission_runner, "runtime_write_outputs", fake_claim)

    result = runner._run_post_sequence_admission(tmp_path)

    assert result["status"] == "PASS"
    assert calls[0] == ("admission", sequence_path, tmp_path)
    assert calls[1] == (
        "claim",
        sequence_path,
        tmp_path / runner.SAFE_FINDING_ADMISSION_JSON,
        tmp_path,
    )

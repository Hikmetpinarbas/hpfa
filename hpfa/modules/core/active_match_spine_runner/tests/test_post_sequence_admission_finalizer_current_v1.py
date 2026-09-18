import json
from pathlib import Path

import post_sequence_admission_finalizer_current_v1 as finalizer


def _write_sequence(path: Path, count: int) -> None:
    path.write_text(
        json.dumps({
            "safe_finding_handoff_candidate_count": count,
            "safe_finding_handoff_candidates": [],
        }),
        encoding="utf-8",
    )


def test_finalizer_runs_admission_then_claim(monkeypatch, tmp_path: Path) -> None:
    sequence_path = tmp_path / finalizer.SEQUENCE_JSON
    _write_sequence(sequence_path, 2)
    calls = []

    def fake_admission(source, out_dir):
        calls.append(("admission", Path(source), Path(out_dir)))
        payload = {
            "status": "PASS",
            "safe_finding_admission_decision_count": 2,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
        (tmp_path / finalizer.SAFE_FINDING_ADMISSION_JSON).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return payload

    def fake_claim(sequence, admission, out_dir):
        calls.append(("claim", Path(sequence), Path(admission), Path(out_dir)))
        payload = {
            "status": "PASS",
            "analyst_output_contract_count": 2,
            "safe_finding_admission_consumed": True,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
        (tmp_path / finalizer.ANALYST_OUTPUT_CLAIM_JSON).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return payload

    monkeypatch.setattr(finalizer.safe_finding_runner, "runtime_write_outputs", fake_admission)
    monkeypatch.setattr(finalizer.claim_runner, "runtime_write_outputs", fake_claim)

    result = finalizer.finalize_post_sequence_admission(tmp_path)

    assert result["status"] == "PASS"
    assert result["expected_handoff_count"] == 2
    assert result["admission_count"] == 2
    assert result["claim_count"] == 2
    assert result["safe_finding_admission_consumed"] is True
    assert calls == [
        ("admission", sequence_path, tmp_path),
        (
            "claim",
            sequence_path,
            tmp_path / finalizer.SAFE_FINDING_ADMISSION_JSON,
            tmp_path,
        ),
    ]


def test_finalizer_fails_closed_on_count_mismatch(monkeypatch, tmp_path: Path) -> None:
    sequence_path = tmp_path / finalizer.SEQUENCE_JSON
    _write_sequence(sequence_path, 2)

    def fake_admission(source, out_dir):
        payload = {"status": "PASS", "safe_finding_admission_decision_count": 1}
        (tmp_path / finalizer.SAFE_FINDING_ADMISSION_JSON).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return payload

    def fake_claim(sequence, admission, out_dir):
        payload = {
            "status": "PASS",
            "analyst_output_contract_count": 2,
            "safe_finding_admission_consumed": True,
        }
        (tmp_path / finalizer.ANALYST_OUTPUT_CLAIM_JSON).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return payload

    monkeypatch.setattr(finalizer.safe_finding_runner, "runtime_write_outputs", fake_admission)
    monkeypatch.setattr(finalizer.claim_runner, "runtime_write_outputs", fake_claim)

    result = finalizer.finalize_post_sequence_admission(tmp_path)

    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "post_sequence_admission_count_or_consumption_mismatch"
    assert result["expected_handoff_count"] == 2
    assert result["admission_count"] == 1
    assert result["claim_count"] == 2

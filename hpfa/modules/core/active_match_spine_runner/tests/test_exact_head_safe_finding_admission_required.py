import json
from pathlib import Path

import active_match_exact_head_run_v1 as runner


def _admission(count: int) -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decision_count": count,
        "safe_finding_admission_decisions": [],
        "professional_finding_emitted_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _claim(count: int) -> dict:
    return {
        "status": "PASS",
        "analyst_output_contract_count": count,
        "analyst_output_contracts": [],
        "safe_finding_admission_consumed": True,
        "professional_emit_allowed_count": 0,
        "professional_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _full_spine_with_legacy_sentence() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "engineering_evidence": {
            "current_c4_producers_reused": True,
        },
        "current_invocation_artifacts": [],
        "intelligence_chain_count": 1,
        "intelligence_chains": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "LEGACY C4 SENTENCE MUST NOT BYPASS ADMISSION"
                }
            }
        ],
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


def test_downgraded_finding_removes_legacy_c4_sentence_from_user_output_projection(tmp_path: Path) -> None:
    ref = "sf_1"
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": ref,
                "safe_meaning": "This meaning is not admitted for professional output.",
            }
        ]
    }
    admission = {
        **_admission(1),
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": ref,
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
            }
        ],
    }
    claim = {
        **_claim(1),
        "analyst_output_contracts": [
            {
                "source_safe_finding_handoff_ref": ref,
                "safe_finding_admission_decision": "DOWNGRADE",
                "professional_emit_allowed": False,
            }
        ],
    }

    gated = runner._admission_gated_full_spine_for_user_outputs(
        out_dir=tmp_path,
        full_spine=_full_spine_with_legacy_sentence(),
        sequence=sequence,
        post_sequence={
            "status": "PASS",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
        },
    )

    assert gated["status"] == "PASS"
    projected = gated["full_spine"]
    assert projected["intelligence_chains"] == []
    assert projected["intelligence_chain_count"] == 0
    assert projected["engineering_evidence"]["legacy_c4_safe_sentences_used_for_professional_output"] is False
    assert str(tmp_path / runner.SAFE_FINDING_ADMISSION_JSON) in projected["current_invocation_artifacts"]
    assert str(tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON) in projected["current_invocation_artifacts"]


def test_emit_uses_only_safe_finding_safe_meaning_for_user_output_projection(tmp_path: Path) -> None:
    ref = "sf_emit"
    safe_meaning = "Observed comparable branches support a defeasible match-local finding."
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": ref,
                "safe_meaning": safe_meaning,
            }
        ]
    }
    admission = {
        **_admission(1),
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": ref,
                "decision": "EMIT",
                "claim_output_allowed": True,
            }
        ],
        "professional_finding_emitted_count": 1,
    }
    claim = {
        **_claim(1),
        "analyst_output_contracts": [
            {
                "source_safe_finding_handoff_ref": ref,
                "safe_finding_admission_decision": "EMIT",
                "professional_emit_allowed": True,
            }
        ],
        "professional_emit_allowed_count": 1,
        "professional_emit_allowed": True,
    }

    gated = runner._admission_gated_full_spine_for_user_outputs(
        out_dir=tmp_path,
        full_spine=_full_spine_with_legacy_sentence(),
        sequence=sequence,
        post_sequence={
            "status": "PASS",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
        },
    )

    assert gated["status"] == "PASS"
    projected = gated["full_spine"]
    assert projected["intelligence_chain_count"] == 1
    assert projected["intelligence_chains"][0]["safe_sentence"]["safe_sentence_candidate_tr"] == safe_meaning
    assert "LEGACY C4 SENTENCE" not in json.dumps(projected["intelligence_chains"])


def test_user_output_rewrite_occurs_after_admission_and_is_fail_closed(monkeypatch, tmp_path: Path) -> None:
    ref = "sf_emit"
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": ref,
                "safe_meaning": "Admitted safe meaning.",
            }
        ]
    }
    admission = {
        **_admission(1),
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": ref,
                "decision": "EMIT",
                "claim_output_allowed": True,
            }
        ],
        "professional_finding_emitted_count": 1,
    }
    claim = {
        **_claim(1),
        "analyst_output_contracts": [
            {
                "source_safe_finding_handoff_ref": ref,
                "safe_finding_admission_decision": "EMIT",
                "professional_emit_allowed": True,
            }
        ],
        "professional_emit_allowed_count": 1,
        "professional_emit_allowed": True,
    }
    (tmp_path / runner.SAFE_FINDING_ADMISSION_JSON).write_text(json.dumps(admission), encoding="utf-8")
    (tmp_path / runner.ANALYST_OUTPUT_CLAIM_JSON).write_text(json.dumps(claim), encoding="utf-8")
    seen = {}

    def fake_write(out_dir, projected):
        seen["projected"] = projected
        paths = {
            "analyst_report": tmp_path / "HPFA_ANALYST_REPORT.txt",
            "bundle_manifest": tmp_path / "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json",
            "bundle_zip": tmp_path / "HPFA_ACTIVE_MATCH_BUNDLE.zip",
        }
        for path in paths.values():
            path.write_text("ok", encoding="utf-8")
        return {key: str(path) for key, path in paths.items()}

    monkeypatch.setattr(runner.canonical_runner, "write_standard_user_outputs", fake_write)
    result = runner._rewrite_standard_user_outputs_after_admission(
        out_dir=tmp_path,
        full_spine=_full_spine_with_legacy_sentence(),
        sequence=sequence,
        post_sequence={
            "status": "PASS",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
        },
    )

    assert result["status"] == "PASS"
    assert result["analyst_report_admission_gated"] is True
    assert result["bundle_includes_safe_finding_admission"] is True
    assert result["bundle_includes_analyst_output_claim"] is True
    assert seen["projected"]["intelligence_chains"][0]["safe_sentence"]["safe_sentence_candidate_tr"] == "Admitted safe meaning."


def test_user_output_gate_rejects_emit_ref_not_present_in_sequence(tmp_path: Path) -> None:
    admission = {
        **_admission(1),
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "missing",
                "decision": "EMIT",
                "claim_output_allowed": True,
            }
        ],
        "professional_finding_emitted_count": 1,
    }
    claim = {
        **_claim(1),
        "analyst_output_contracts": [
            {
                "source_safe_finding_handoff_ref": "missing",
                "safe_finding_admission_decision": "EMIT",
                "professional_emit_allowed": True,
            }
        ],
        "professional_emit_allowed_count": 1,
        "professional_emit_allowed": True,
    }

    result = runner._admission_gated_full_spine_for_user_outputs(
        out_dir=tmp_path,
        full_spine=_full_spine_with_legacy_sentence(),
        sequence={"safe_finding_handoff_candidates": []},
        post_sequence={
            "status": "PASS",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
        },
    )

    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "professional_emit_handoff_missing:missing"

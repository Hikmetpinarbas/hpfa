import importlib.util
import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[5]
RUNNER_PATH = PRODUCT_ROOT / "active_match_zfgv_full_runner.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("active_match_zfgv_full_runner_test", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_runner_finalizes_post_sequence_before_user_output(tmp_path, monkeypatch, capsys):
    runner = load_runner()
    active = tmp_path / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)
    out = tmp_path / "out"
    execution_root = tmp_path / "product"
    execution_root.mkdir()
    runtime_root = tmp_path / "runtime_authority"
    runtime_root.mkdir()

    monkeypatch.setattr(runner, "validate_split_active_match_authority", lambda path, root: active)
    monkeypatch.setattr(runner.entrypoint_module, "_bind_shared_snapshot_contract", lambda: None)
    monkeypatch.setattr(runner.entrypoint_module, "_bind_construct_admission_gate", lambda: None)
    monkeypatch.setattr(runner.entrypoint_module, "_bind_metric_governance_prerequisite_chain", lambda: None)
    monkeypatch.setattr(runner.entrypoint_module, "_bind_metric_governance_construct_gate", lambda: None)
    monkeypatch.setattr(runner.entrypoint_module, "_normalize_current_surface_evidence", lambda result: None)
    monkeypatch.setattr(runner, "snapshot_output_state", lambda path: {})

    def fake_full_spine(**kwargs):
        out.mkdir(parents=True, exist_ok=True)
        (out / "visible_action_sequence_candidates_lite_v1.json").write_text(
            json.dumps({"safe_finding_handoff_candidate_count": 1}), encoding="utf-8"
        )
        return {"status": "REVIEW_REQUIRED", "decision": "TEST_REVIEW"}

    monkeypatch.setattr(runner.full_spine_runner, "run_full_spine", fake_full_spine)

    calls = []
    def fake_finalize(path):
        calls.append("finalize")
        (out / "safe_finding_admission_projection_v1.json").write_text(
            json.dumps({"safe_finding_admission_decision_count": 1}), encoding="utf-8"
        )
        (out / "analyst_output_claim_contract_projection_v1.json").write_text(
            json.dumps({"analyst_output_contract_count": 1}), encoding="utf-8"
        )
        return {
            "status": "REVIEW_REQUIRED",
            "post_sequence_admission_finalized": True,
            "post_sequence_admission_count": 1,
            "post_sequence_claim_count": 1,
        }

    monkeypatch.setattr(runner, "materialize_variant_feature_challenge", fake_finalize, raising=False)

    def fake_bind_variant_feature_challenge_runtime(result, path):
        calls.append("bind")
        post = fake_finalize(path)
        result["variant_feature_challenge_runtime_binding"] = post
        result["current_invocation_artifacts"] = [
            str(out / "safe_finding_admission_projection_v1.json"),
            str(out / "analyst_output_claim_contract_projection_v1.json"),
        ]
        return result

    def fake_persist(path, result):
        calls.append("persist")
        (out / "active_match_full_spine_v1.json").write_text(
            json.dumps(result), encoding="utf-8"
        )

    monkeypatch.setattr(
        runner.entrypoint_module,
        "_bind_variant_feature_challenge_runtime",
        fake_bind_variant_feature_challenge_runtime,
    )
    monkeypatch.setattr(
        runner.entrypoint_module,
        "_persist_full_spine_result",
        fake_persist,
    )

    def fake_user_outputs(path, result, before_state=None):
        calls.append("user_output")
        assert (out / "safe_finding_admission_projection_v1.json").is_file()
        assert (out / "analyst_output_claim_contract_projection_v1.json").is_file()
        return {
            "analyst_report": "report_audit.txt",
            "analyst_report_tr": "report_football_tr.txt",
            "football_delivery_zip": "football_delivery.zip",
            "bundle_zip": "audit_bundle.zip",
            "bundle_manifest": "manifest.json",
        }

    monkeypatch.setattr(runner, "write_standard_user_outputs", fake_user_outputs)
    monkeypatch.setattr(sys, "argv", [
        str(RUNNER_PATH), str(active), "--out-dir", str(out),
        "--execution-root", str(execution_root), "--runtime-authority-root", str(runtime_root),
    ])

    rc = runner.main()
    assert rc == 0
    assert calls == ["bind", "finalize", "persist", "user_output"]
    persisted = json.loads((out / "active_match_full_spine_v1.json").read_text(encoding="utf-8"))
    artifact_names = {Path(value).name for value in persisted["current_invocation_artifacts"]}
    assert "safe_finding_admission_projection_v1.json" in artifact_names
    assert "analyst_output_claim_contract_projection_v1.json" in artifact_names
    payload = json.loads(capsys.readouterr().out)
    assert payload["post_sequence_admission_finalized"] is True
    assert payload["post_sequence_admission_count"] == 1
    assert payload["post_sequence_claim_count"] == 1
    assert payload["analyst_report"] == "report_football_tr.txt"
    assert payload["analyst_audit_report"] == "report_audit.txt"
    assert payload["bundle_zip"] == "football_delivery.zip"
    assert payload["audit_bundle_zip"] == "audit_bundle.zip"

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "full_system_match_diagnostic.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("hpfa_full_system_match_diagnostic_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(root: Path, name: str, payload: dict) -> None:
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def _minimal_runtime(tmp_path: Path) -> None:
    current = [
        str(tmp_path / "event_window_builder_lite_v1.json"),
        str(tmp_path / "active_match_full_spine_v1.json"),
    ]
    chain = {
        "packet": {"status": "SMOKE_PASS", "decision": "READY_FOR_FUSION_CONSUMER"},
        "fusion": {"decision": "READY_FOR_ARGUMENT_SUPPORT"},
        "argument": {"status": "ARGUMENT_SUPPORTED", "decision": "READY_FOR_SAFE_ROUTER"},
        "route": {"status": "SMOKE_PASS"},
        "graph": {"status": "SMOKE_PASS"},
        "lens": {"status": "REVIEW_REQUIRED"},
        "safe_sentence": {"status": "SMOKE_PASS"},
        "report_block": {"status": "SMOKE_PASS"},
        "output_contract": {"status": "SMOKE_PASS"},
        "assembly": {"status": "SMOKE_PASS"},
    }
    _write_json(tmp_path, "active_match_full_spine_v1.json", {
        "status": "REVIEW_REQUIRED",
        "active_match_authority": "/runtime/active_single_match/current",
        "current_invocation_artifacts": current,
        "intelligence_chain_count": 1,
        "intelligence_chains": [chain],
        "variant_feature_challenge_runtime_binding": {
            "artifact_materialized": True,
            "status": "REVIEW_REQUIRED",
            "variant_feature_challenge_record_count": 1,
        },
        "orphan_capability_sidecars": {
            "triplex_source_alignment_status": "NOT_APPLICABLE_PREREQUISITE_MISSING",
            "triplex_source_alignment_prerequisite_present": False,
            "triplex_source_alignment": {"reason": "source_mapping_contract_or_audit_not_currently_produced"},
        },
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    })
    _write_json(tmp_path, "event_window_builder_lite_v1.json", {
        "status": "PASS",
        "event_window_count": 2,
        "same_time_unordered_bucket_count": 1,
    })
    _write_json(tmp_path, "variant_feature_challenge_projection_v1.json", {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_record_count": 2,
    })
    _write_json(tmp_path, "safe_finding_admission_projection_v1.json", {
        "status": "REVIEW_REQUIRED",
        "safe_finding_admission_decision_count": 1,
        "finding_status_counts": {"DOWNGRADE": 1, "EMIT": 0, "ABSTAIN": 0},
        "professional_finding_emitted_count": 0,
    })
    (tmp_path / "HPFA_ANALYST_REPORT.txt").write_text("intelligence_chain_count=0\n", encoding="utf-8")


def test_diagnostic_enumerates_capabilities_spine_and_blocked_prerequisites(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_runtime(tmp_path)
    diagnostic = module.build_diagnostic(tmp_path, head="abc123", branch="feature/test", pr="359")

    assert [row["family"] for row in diagnostic["observation_capability_coverage"]] == [
        "ACTION/EVENT", "ENTITY/ACTOR", "TEMPORAL", "SPATIAL", "OUTCOME/QUALIFIER",
        "RELATIONAL", "PROCESS/PARTICIPATION", "AGGREGATE/TABULAR", "EXTERNAL CONTEXT",
        "TRACKING/VIDEO", "HPFA-DERIVED INTELLIGENCE",
    ]
    assert [row["node"] for row in diagnostic["evidence_spine_coverage"]] == [
        "SOURCE", "SURFACE", "OBSERVATION", "SEMANTICS", "IDENTITY/DEPENDENCY",
        "TIME/SPACE ADMISSION", "RELATION", "EPISODE/PROCESS", "FEATURE", "METRIC/MODEL",
        "SIGNAL", "HYPOTHESIS", "COUNTEREVIDENCE", "FINDING", "CLAIM", "ANALYST OUTPUT",
    ]
    statuses = {row["component"]: row["status"] for row in diagnostic["component_coverage"]}
    assert statuses["tracking_video_pipeline"] == "NOT_APPLICABLE"
    assert statuses["external_context_pipeline"] == "BLOCKED_BY_PREREQUISITE"
    assert statuses["triplex_source_alignment"] == "BLOCKED_BY_PREREQUISITE"


def test_diagnostic_separates_artifact_presence_from_current_execution(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_runtime(tmp_path)
    diagnostic = module.build_diagnostic(tmp_path)
    challenge = next(row for row in diagnostic["component_coverage"] if row["component"] == "variant_feature_challenge")

    assert challenge["invoked"] is True
    assert challenge["current_invocation_artifact"] is False
    assert challenge["status"] == "REVIEW_REQUIRED"
    assert "ledger_omits_artifact" in challenge["degraded_reason"]
    check = next(row for row in diagnostic["cross_artifact_consistency"] if row["check"] == "variant_feature_challenge_current_invocation_accounting")
    assert check["artifact_record_count"] == 2
    assert check["runtime_binding_record_count"] == 1
    assert check["status"] == "REVIEW_REQUIRED"


def test_human_report_cannot_hide_machine_execution_and_truth_locks_survive(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_runtime(tmp_path)
    diagnostic = module.build_diagnostic(tmp_path)
    check = next(row for row in diagnostic["cross_artifact_consistency"] if row["check"] == "machine_vs_human_intelligence_chain_count")

    assert check["machine_value"] == 1
    assert check["human_report_value"] == 0
    assert check["status"] == "REVIEW_REQUIRED"
    guards = diagnostic["diagnostic_safeguards"]
    assert guards["same_time_unordered_preserved"] is True
    assert guards["provider_process_annotation_is_tactical_truth"] is False
    assert guards["tracking_video_claims_without_surface_allowed"] is False
    assert guards["reflection_dependency_is_independence"] is False
    assert guards["absence_is_counterevidence"] is False
    assert guards["zero_professional_emit_is_valid"] is True
    assert guards["human_report_may_exceed_machine_claim_ceiling"] is False
    assert guards["diagnostic_creates_new_evidence"] is False


def test_not_evaluated_safe_finding_is_not_reported_as_downgrade(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_runtime(tmp_path)

    full_path = tmp_path / "active_match_full_spine_v1.json"
    full = json.loads(full_path.read_text(encoding="utf-8"))
    full["intelligence_chain_count"] = 1
    full["current_invocation_artifacts"].append(
        str(tmp_path / "analyst_output_claim_contract_projection_v1.json")
    )
    _write_json(tmp_path, "active_match_full_spine_v1.json", full)
    _write_json(tmp_path, "analyst_output_claim_contract_projection_v1.json", {
        "status": "PASS",
        "safe_finding_admission_consumed": False,
        "analyst_output_contract_count": 100,
        "safe_finding_admission_decision_counts": {
            "ABSTAIN": 0,
            "DOWNGRADE": 0,
            "EMIT": 0,
            "NOT_EVALUATED": 100,
        },
        "professional_emit_allowed_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    })
    (tmp_path / "HPFA_ANALYST_REPORT.txt").write_text(
        "intelligence_chain_count=1\n", encoding="utf-8"
    )

    diagnostic = module.build_diagnostic(tmp_path)
    components = {row["component"]: row for row in diagnostic["component_coverage"]}
    safe = diagnostic["match_football_intelligence"]["safe_findings"]
    check = next(
        row for row in diagnostic["cross_artifact_consistency"]
        if row["check"] == "safe_finding_current_run_accounting"
    )

    assert components["safe_finding_admission"]["runtime_execution_state"] == "NOT_BOUND_CURRENT_RUN"
    assert safe["evaluation_state"] == "NOT_BOUND_CURRENT_RUN"
    assert safe["decision_count"] is None
    assert safe["professional_finding_emitted_count"] is None
    assert safe["claim_contract_current_run"] is True
    assert safe["claim_contract_evaluation_state"] == "EXECUTED_SAFE_FINDING_NOT_EVALUATED"
    assert safe["claim_contract_decision_counts"]["NOT_EVALUATED"] == 100
    assert check["status"] == "PASS"
    assert diagnostic["diagnostic_safeguards"]["not_evaluated_is_downgrade"] is False
    symptoms = [row["current_symptom"] for row in diagnostic["gap_report"]]
    assert not any("100/100 safe findings DOWNGRADE" in value for value in symptoms)
    assert not any("machine full-spine and human report disagree" in value for value in symptoms)


def test_mechanism_diagnostic_preserves_all_eligible_candidates_without_fixed_top_five_cutoff(tmp_path: Path) -> None:
    module = _load_module()
    records = []
    for idx in range(7):
        records.append({
            "grammar_stable_variant_feature_delta_id": f"m{idx}",
            "resolved_variant_count": 10 + idx,
            "success_resolved_variant_count": 6 + idx,
            "failure_resolved_variant_count": 4,
            "grammar_signature_tokens": ["LAYER[PASS]", f"LAYER[{idx}]"],
            "process_context_feature_difference_candidates": [],
            "consequence_feature_difference_candidates": [],
        })
    _write_json(tmp_path, "grammar_stable_variant_feature_delta_projection_v1.json", {
        "grammar_stable_variant_feature_delta_records": records,
    })

    candidates = module._top_mechanism_candidates(tmp_path)

    assert len(candidates) == 7
    assert [row["candidate_id"] for row in candidates] == [
        "m6", "m5", "m4", "m3", "m2", "m1", "m0"
    ]
    assert module._top_mechanism_candidates(tmp_path, limit=3)[0]["candidate_id"] == "m6"
    assert len(module._top_mechanism_candidates(tmp_path, limit=3)) == 3

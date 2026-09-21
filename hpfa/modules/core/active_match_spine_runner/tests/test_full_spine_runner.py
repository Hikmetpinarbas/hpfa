import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import episode_lane_runner
import full_spine_runner
import reconstruction_intelligence_packet_adapter_current_v1 as current_bridge
from full_spine_runner import _first_failure, run_full_spine, run_intelligence_chain
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet


def _packet():
    return build_composite_packet({
        "packet_family": "sequence",
        "input_features": [{"feature_id": "feature_generic_001", "source_surface": "feature_surface"}],
        "input_windows": [{"window_id": "window_generic_001", "source_surface": "window_surface"}],
        "input_sequences": [], "input_metrics": [],
        "supporting_signals": [{"signal_id": "signal_generic_001", "source_surface": "signal_surface"}],
        "contradicting_signals": [], "claim_ceiling": "composite_candidate_only",
    })


def _episode_pass(_input_dir, _output_dir, _execution_root):
    return {
        "module_id": "active_match_episode_lane_adapter_v1", "status": "SMOKE_PASS",
        "episode_candidate_count": 2, "episode_feature_vector_count": 2,
        "temporal_episode_signature_status": "SMOKE_PASS", "temporal_episode_signature_count": 2,
        "shared_foundation_reused": True, "context_episode_feature_lane_executed": True,
        "context_episode_feature_lane_completed": True, "temporal_episode_signature_executed": True,
        "row_nucleus_recomputed_by_episode_lane": False,
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False,
    }


def test_full_spine_reuses_current_c4_chain_without_truth_promotion():
    chain = run_intelligence_chain(_packet())
    assert chain["fusion"]["packet_id"] == chain["packet"]["packet_id"]
    assert chain["argument"]["fusion_id"] == chain["fusion"]["fusion_id"]
    assert chain["route"]["argument_id"] == chain["argument"]["argument_id"]
    assert chain["graph"]["route_id"] == chain["route"]["route_id"]
    assert chain["report_block"]["safe_sentence_id"] == chain["safe_sentence"]["safe_sentence_id"]
    assert chain["assembly"]["contract_item_id"] == chain["output_contract"]["contract_item_id"]
    for record in chain.values():
        assert record.get("canonical_event_count") == "UNKNOWN"


def test_c4_stage_exception_is_contracted_into_fail_closed_record():
    def explode(_artifact):
        raise RuntimeError("synthetic")
    chain = run_intelligence_chain(_packet(), stage_overrides={"graph": explode})
    assert chain["graph"]["status"] == "FAIL_CLOSED"
    assert chain["graph"]["hard_block_hits"] == ["c4_stage_exception:graph:RuntimeError"]
    assert "lens" not in chain
    assert _first_failure([chain]) == ("graph", "c4_stage_exception:graph:RuntimeError")


def test_lens_failure_is_in_first_failure_order_without_rewiring_main_sentence_path():
    def blocked_lens(_artifact):
        return {"module_id": "lens_failure_fixture", "status": "FAIL_CLOSED", "decision": "BLOCK_LENS", "hard_block_hits": ["lens_specific_failure"], "review_hits": [], "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False}
    chain = run_intelligence_chain(_packet(), stage_overrides={"lens": blocked_lens})
    assert _first_failure([chain]) == ("lens", "lens_specific_failure")
    assert "safe_sentence" in chain
    assert chain["safe_sentence"].get("graph_id") == chain["graph"].get("graph_id")


def test_lens_exception_preserves_independent_safe_sentence_branch():
    def explode_lens(_artifact):
        raise RuntimeError("synthetic lens exception")
    chain = run_intelligence_chain(_packet(), stage_overrides={"lens": explode_lens})
    assert chain["lens"]["status"] == "FAIL_CLOSED"
    assert chain["lens"]["hard_block_hits"] == ["c4_stage_exception:lens:RuntimeError"]
    for stage in ("safe_sentence", "report_block", "output_contract", "assembly"):
        assert stage in chain
    assert _first_failure([chain]) == ("lens", "c4_stage_exception:lens:RuntimeError")


def test_full_spine_uses_single_active_match_authority_and_flat_outputs(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    out_dir = tmp_path / "out"
    packet = _packet()
    def fake_bridge(input_dir, output_dir):
        assert Path(input_dir).resolve() == active_match.resolve()
        output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
        (output / "composite_evidence_packet_builder_lite_v1.json").write_text(json.dumps({"module_id": "composite_evidence_packet_builder_lite_v1", "status": "SMOKE_PASS", "packet_count": 1, "blocked_packet_count": 0, "packets": [packet], "canonical_event_count": "UNKNOWN", "production_release": False}), encoding="utf-8")
        return {"module_id": "reconstruction_intelligence_packet_bridge_current_v1", "status": "SMOKE_PASS", "match_surface_binding_id": "msb_generic", "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False}
    report = run_full_spine(active_match_dir=active_match, out_dir=out_dir, execution_root=execution_root, bridge_runner=fake_bridge, episode_runner=_episode_pass)
    assert report["active_match_authority"] == str(active_match.resolve())
    assert report["episode_candidate_count"] == 2
    assert report["temporal_episode_signature_count"] == 2
    ev = report["engineering_evidence"]
    assert ev["single_active_match_authority_validated"] is True
    assert ev["reconstruction_bridge_executed"] is True
    assert ev["episode_lane_executed"] is True
    assert ev["shared_foundation_reused"] is True
    assert ev["current_context_episode_feature_lane_reused"] is True
    assert ev["current_temporal_episode_signature_reused"] is True
    assert ev["current_c4_producers_reused"] is True
    assert ev["parallel_reasoning_engine_created"] is False
    assert report["canonical_event_count"] == "UNKNOWN" and report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert (out_dir / "active_match_full_spine_v1.json").is_file()
    assert (out_dir / "active_match_full_spine_v1.txt").is_file()


def test_full_spine_fails_closed_when_bridge_fails(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    def failed_bridge(_input_dir, _output_dir):
        return {"module_id": "reconstruction_intelligence_packet_bridge_current_v1", "status": "FAIL_CLOSED", "hard_block_hits": ["synthetic_upstream_failure"], "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False}
    report = run_full_spine(active_match_dir=active_match, out_dir=tmp_path / "out", execution_root=execution_root, bridge_runner=failed_bridge, episode_runner=_episode_pass)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_node"] == "reconstruction_intelligence_bridge"
    assert report["first_failed_reason_code"] == "synthetic_upstream_failure"
    assert report["episode_lane_status"] == "NOT_EVALUATED"
    ev = report["engineering_evidence"]
    assert ev["episode_lane_executed"] is False and ev["shared_foundation_reused"] is False
    assert ev["current_context_episode_feature_lane_reused"] is False
    assert ev["current_temporal_episode_signature_reused"] is False
    assert ev["current_c4_producers_reused"] is False


def test_full_spine_does_not_run_episode_after_foundation_failure(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    def failed_bridge(_input_dir, _output_dir):
        return {"status": "FAIL_CLOSED", "hard_block_hits": ["foundation_failure"], "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False}
    def should_not_run_episode(*_args):
        raise AssertionError("episode lane must not run after shared foundation failure")
    report = run_full_spine(active_match_dir=active_match, out_dir=tmp_path / "out", execution_root=execution_root, bridge_runner=failed_bridge, episode_runner=should_not_run_episode)
    assert report["first_failed_reason_code"] == "foundation_failure"


def test_episode_lane_code_root_is_product_checkout_not_selected_execution_root():
    product_root = episode_lane_runner._product_root()
    assert product_root == ROOT
    assert (product_root / "active_match_full_run.py").is_file()


def _write_bridge_snapshot(active_match: Path, output: Path) -> dict:
    snapshot = episode_lane_runner._surface_snapshot(active_match)
    (output / episode_lane_runner.BRIDGE_OUTPUT).write_text(
        json.dumps({"input_surface_snapshot_id": snapshot["snapshot_id"]}),
        encoding="utf-8",
    )
    return snapshot


def _prepare_episode_fixture(tmp_path, monkeypatch, *, fail_run_step=False):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    surface = active_match / "surface.csv"
    surface.write_text("id,start\n1,0\n", encoding="utf-8")
    output = tmp_path / "out"; output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")
    _write_bridge_snapshot(active_match, output)
    monkeypatch.setattr(episode_lane_runner.current_episode, "run_provider_time_context_step", lambda *_a, **_k: {"command": ["internal:provider_time_semantic_admission_lite_v1"], "returncode": 0, "stdout": "", "stderr": "", "passed": True})
    monkeypatch.setattr(episode_lane_runner.current_episode, "run_step", lambda _r, command: {"command": command, "returncode": 17 if fail_run_step else 0, "stdout": "", "stderr": "synthetic failure" if fail_run_step else "", "passed": not fail_run_step})
    return active_match, output, surface


def test_episode_lane_preserves_first_failed_subprocess_stage_and_stops_dependents(tmp_path, monkeypatch):
    active_match, output, _surface = _prepare_episode_fixture(tmp_path, monkeypatch, fail_run_step=True)
    monkeypatch.setattr(episode_lane_runner.current_episode, "write_summary", lambda *_a, **_k: {"status": "FAIL_CLOSED", "analyst_evidence": {}})
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_episode_step"]["stage"] == "context_action_semantics_rebind.py"
    assert report["hard_block_hits"] == ["episode_step_failed:context_action_semantics_rebind.py:returncode_17"]
    assert len(report["step_statuses"]) == 2
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False


def test_episode_lane_missing_shared_foundation_does_not_claim_reuse(tmp_path):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    (active_match / "surface.csv").write_text("id,start\n1,0\n", encoding="utf-8")
    output = tmp_path / "out"; output.mkdir()
    _write_bridge_snapshot(active_match, output)
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert "shared_row_nucleus_output_missing" in report["hard_block_hits"]
    assert report["shared_foundation_reused"] is False
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False


def test_episode_lane_rejects_snapshot_mismatch_before_provider_time(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    (active_match / "surface.csv").write_text("id,start\n1,0\n", encoding="utf-8")
    output = tmp_path / "out"; output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")
    (output / episode_lane_runner.BRIDGE_OUTPUT).write_text(
        json.dumps({"input_surface_snapshot_id": "not-the-current-snapshot"}), encoding="utf-8"
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_provider_time_context_step",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider-time must not run")),
    )
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert "active_match_surface_snapshot_mismatch_before_episode" in report["hard_block_hits"]
    assert report["shared_foundation_reused"] is False
    assert report["step_statuses"] == []


def test_episode_lane_stops_if_surface_changes_during_provider_time(tmp_path, monkeypatch):
    active_match, output, surface = _prepare_episode_fixture(tmp_path, monkeypatch)
    def mutating_provider(*_args, **_kwargs):
        surface.write_text("id,start\n1,99\n", encoding="utf-8")
        return {"command": ["internal:provider_time_semantic_admission_lite_v1"], "returncode": 0, "stdout": "", "stderr": "", "passed": True}
    monkeypatch.setattr(episode_lane_runner.current_episode, "run_provider_time_context_step", mutating_provider)
    monkeypatch.setattr(episode_lane_runner.current_episode, "write_summary", lambda *_a, **_k: {"status": "FAIL_CLOSED", "analyst_evidence": {}})
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_episode_step"]["stage"] == "internal:provider_time_semantic_admission_lite_v1"
    assert report["first_failed_episode_step"]["returncode"] == 19
    assert len(report["step_statuses"]) == 1
    assert report["context_episode_feature_lane_executed"] is False
    assert report["surface_snapshot_bound"] is False


def test_episode_lane_preserves_temporal_hard_block_reason(tmp_path, monkeypatch):
    active_match, output, _surface = _prepare_episode_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(episode_lane_runner.current_episode, "write_summary", lambda *_a, **_k: {"status": "SMOKE_PASS", "analyst_evidence": {}})
    monkeypatch.setattr(episode_lane_runner, "write_temporal_episode_signature", lambda *_a, **_k: {"status": "FAIL_CLOSED", "hard_block_hits": ["temporal_specific_contract_failure"], "canonical_event_count": "UNKNOWN", "production_release": False})
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["first_failed_temporal_reason"] == "temporal_specific_contract_failure"
    assert report["hard_block_hits"] == ["temporal_specific_contract_failure"]
    assert report["context_episode_feature_lane_completed"] is True
    assert report["temporal_episode_signature_executed"] is True
    assert report["surface_snapshot_bound"] is True


def test_reconstruction_bridge_fails_closed_if_surface_changes_during_reconstruction(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    surface = active_match / "surface.csv"
    surface.write_text("id,start\n1,0\n", encoding="utf-8")
    output = tmp_path / "out"
    monkeypatch.setattr(current_bridge.adapter, "validate_out", lambda value: Path(value))
    def mutating_sequence(_input_dir, out_dir):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        surface.write_text("id,start\n1,42\n", encoding="utf-8")
        return {"status": "SMOKE_PASS"}
    monkeypatch.setattr(current_bridge.current_sequence, "runtime_write_outputs", mutating_sequence)
    monkeypatch.setattr(
        current_bridge.adapter,
        "write_outputs",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("adapter must not run on unstable snapshot")),
    )
    report = current_bridge.runtime_write_outputs(active_match, output)
    assert report["status"] == "FAIL_CLOSED"
    assert report["input_surface_snapshot_stable"] is False
    assert report["adapter_status"] == "NOT_EVALUATED"
    assert report["hard_block_hits"] == ["active_match_surface_snapshot_changed_during_reconstruction"]
    assert (output / current_bridge.OUTPUT_JSON).is_file()


def test_no_sample_match_identity_leak():
    for source_path in [SRC / "full_spine_runner.py", SRC / "episode_lane_runner.py"]:
        source = source_path.read_text(encoding="utf-8")
        for token in ["Genclerbirligi", "Fenerbahce", "Sturm Graz", "Heart of Midlothian", "Turkey", "Australia", "15.08.2026", "22.08.2026"]:
            assert token not in source



def test_p02_counterevidence_only_packet_stops_after_auxiliary_fusion(tmp_path, monkeypatch):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    out_dir = tmp_path / "out"

    base_packet = _packet()

    p02_candidate = {
        "packet_id": "p02_cmp_packet_fixture",
        "packet_family": "progression",
        "input_features": [],
        "input_windows": [
            {
                "window_id": "p02_population_fixture",
                "source_surface": "P02_PROCESS_UNIT_COMPARISON_POPULATION",
                "provenance_root": "p02_population_fixture",
                "dependency_group": "p02_population_fixture",
                "independent_support_vote": False,
            }
        ],
        "input_sequences": [
            {
                "sequence_id": "vasq_ref",
                "source_surface": "visible_action_sequence_candidates_lite_v1",
                "provenance_root": "vasq_ref",
                "dependency_group": "dep_ref",
                "independence_group": "vasq_ref",
                "independent_support_vote": False,
            },
            {
                "sequence_id": "vasq_cand",
                "source_surface": "visible_action_sequence_candidates_lite_v1",
                "provenance_root": "vasq_cand",
                "dependency_group": "dep_cand",
                "independence_group": "vasq_cand",
                "independent_support_vote": False,
            },
        ],
        "input_metrics": [],
        "supporting_signals": [],
        "contradicting_signals": [
            {
                "signal_id": "p02_counter_fixture",
                "relation_type": "CONTRADICTS",
                "contradiction_basis": "same_context_opposite_advanced_access",
                "comparison_question_id": "P02_VISIBLE_SEQUENCE_ADVANCED_ACCESS",
                "comparison_unit": "p02_process_unit_candidate",
                "exact_dimensions": ["team_identity_candidate_id", "period_candidate", "score_state_candidate", "process_start_zone_candidate"],
                "coarsened_dimensions": [],
                "test_dimensions": ["advanced_access_state_candidate"],
                "forbidden_leakage_dimensions": ["advanced_access_state_candidate"],
                "reference_context": {
                    "team_identity_candidate_id": "teamc_A",
                    "period_candidate": "1",
                    "score_state_candidate": "LEVEL",
                    "process_start_zone_candidate": "OWN_HALF",
                },
                "candidate_context": {
                    "team_identity_candidate_id": "teamc_A",
                    "period_candidate": "1",
                    "score_state_candidate": "LEVEL",
                    "process_start_zone_candidate": "OWN_HALF",
                },
                "reference_outcome": "ADVANCED_ACCESS_VISIBLE",
                "candidate_outcome": "NO_ADVANCED_ACCESS_VISIBLE_IN_ADMITTED_ZONE_PATH",
                "outcome_relation": "OPPOSITE",
                "provenance_root": "p02u_cand",
                "reference_provenance_root": "p02u_ref",
                "dependency_group": "dep_cand",
                "reference_dependency_group": "dep_ref",
                "independence_group": "vasq_cand",
                "reference_independence_group": "vasq_ref",
                "independence_admission_status": "ADMITTED",
                "independence_admission_basis": "distinct_visible_sequence_roots+disjoint_trace_roots+non_overlapping_admitted_time_intervals",
            }
        ],
        "claim_ceiling": "composite_candidate_only",
        "p02_packet_role": "POPULATION_COLLAPSED_COUNTEREVIDENCE_COMPARISON_PACKET_ONLY",
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "production_release": False,
    }

    def fake_bridge(_input_dir, output_dir):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "composite_evidence_packet_builder_lite_v1.json").write_text(
            json.dumps({
                "module_id": "composite_evidence_packet_builder_lite_v1",
                "status": "SMOKE_PASS",
                "packet_count": 1,
                "blocked_packet_count": 0,
                "packets": [base_packet],
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            }),
            encoding="utf-8",
        )
        return {
            "module_id": "reconstruction_intelligence_packet_bridge_current_v1",
            "status": "SMOKE_PASS",
            "input_surface_snapshot_id": "snapshot_fixture",
            "match_surface_binding_id": "msb_fixture",
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    monkeypatch.setattr(
        full_spine_runner,
        "run_rich_lane",
        lambda *_a, **_k: {
            "status": "REVIEW_REQUIRED",
            "constructs": {"C01": {"status": "REVIEW_REQUIRED", "c4_admission_status": "WITHHELD_PENDING_CONSTRUCT_ADMISSION"}},
            "progression_pool_p02": {"p02_counterevidence_population_count": 1},
            "c4_packet_candidates": [p02_candidate],
            "current_invocation_artifacts": [],
        },
    )
    monkeypatch.setattr(
        full_spine_runner,
        "run_sidecars",
        lambda *_a, **_k: {"status": "SMOKE_PASS", "current_invocation_artifacts": []},
    )

    report = run_full_spine(
        active_match_dir=active_match,
        out_dir=out_dir,
        execution_root=execution_root,
        bridge_runner=fake_bridge,
        episode_runner=_episode_pass,
    )

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["failed_intelligence_chain_count"] == 0
    assert report["intelligence_chain_count"] == 1
    assert report["P02_auxiliary_counterevidence_packet_count"] == 1
    assert report["P02_auxiliary_counterevidence_fusion_count"] == 1
    assert report["P02_admitted_counterevidence_count"] == 1
    assert report["engineering_evidence"]["P02_counterevidence_packets_enter_argument_route"] is False
    assert report["analyst_evidence"]["P02_auxiliary_counterevidence_safe_finding_emitted"] is False

    inventory = json.loads((out_dir / "active_match_fused_packet_inventory_v1.json").read_text(encoding="utf-8"))
    assert inventory["fused_packet_count"] == 1
    assert inventory["auxiliary_counterevidence_packet_count"] == 1
    assert inventory["auxiliary_counterevidence_fusion_count"] == 1

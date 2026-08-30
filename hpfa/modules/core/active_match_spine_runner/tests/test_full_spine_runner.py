import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import episode_lane_runner
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


def _prepare_episode_fixture(tmp_path, monkeypatch, *, fail_run_step=False):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    output = tmp_path / "out"; output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(episode_lane_runner.current_episode, "readable_surface_files", lambda _d: [active_match / "surface.csv"])
    monkeypatch.setattr(episode_lane_runner.current_episode, "run_provider_time_context_step", lambda *_a, **_k: {"command": ["internal:provider_time_semantic_admission_lite_v1"], "returncode": 0, "stdout": "", "stderr": "", "passed": True})
    monkeypatch.setattr(episode_lane_runner.current_episode, "run_step", lambda _r, command: {"command": command, "returncode": 17 if fail_run_step else 0, "stdout": "", "stderr": "synthetic failure" if fail_run_step else "", "passed": not fail_run_step})
    return active_match, output


def test_episode_lane_preserves_first_failed_subprocess_stage_and_stops_dependents(tmp_path, monkeypatch):
    active_match, output = _prepare_episode_fixture(tmp_path, monkeypatch, fail_run_step=True)
    monkeypatch.setattr(episode_lane_runner.current_episode, "write_summary", lambda *_a, **_k: {"status": "FAIL_CLOSED", "analyst_evidence": {}})
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_episode_step"]["stage"] == "context_action_semantics_rebind.py"
    assert report["hard_block_hits"] == ["episode_step_failed:context_action_semantics_rebind.py:returncode_17"]
    assert len(report["step_statuses"]) == 2
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False


def test_episode_lane_missing_shared_foundation_does_not_claim_reuse(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"; active_match.mkdir(parents=True)
    output = tmp_path / "out"; output.mkdir()
    monkeypatch.setattr(episode_lane_runner.current_episode, "readable_surface_files", lambda _d: [active_match / "surface.csv"])
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert "shared_row_nucleus_output_missing" in report["hard_block_hits"]
    assert report["shared_foundation_reused"] is False
    assert report["context_episode_feature_lane_executed"] is False
    assert report["temporal_episode_signature_executed"] is False


def test_episode_lane_preserves_temporal_hard_block_reason(tmp_path, monkeypatch):
    active_match, output = _prepare_episode_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(episode_lane_runner.current_episode, "write_summary", lambda *_a, **_k: {"status": "SMOKE_PASS", "analyst_evidence": {}})
    monkeypatch.setattr(episode_lane_runner, "write_temporal_episode_signature", lambda *_a, **_k: {"status": "FAIL_CLOSED", "hard_block_hits": ["temporal_specific_contract_failure"], "canonical_event_count": "UNKNOWN", "production_release": False})
    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["first_failed_temporal_reason"] == "temporal_specific_contract_failure"
    assert report["hard_block_hits"] == ["temporal_specific_contract_failure"]
    assert report["context_episode_feature_lane_completed"] is True
    assert report["temporal_episode_signature_executed"] is True


def test_no_sample_match_identity_leak():
    for source_path in [SRC / "full_spine_runner.py", SRC / "episode_lane_runner.py"]:
        source = source_path.read_text(encoding="utf-8")
        for token in ["Genclerbirligi", "Fenerbahce", "Sturm Graz", "Heart of Midlothian", "Turkey", "Australia", "15.08.2026", "22.08.2026"]:
            assert token not in source

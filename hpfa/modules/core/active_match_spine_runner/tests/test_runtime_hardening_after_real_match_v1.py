from __future__ import annotations

import importlib.util
from pathlib import Path

import reconstruction_intelligence_packet_adapter_current_v1 as reconstruction


def _load_entrypoint():
    root = Path(__file__).resolve().parents[5]
    path = root / "active_match_spine_runner.py"
    spec = importlib.util.spec_from_file_location("hpfa_active_match_entrypoint_runtime_hardening_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rich_owned_outputs_are_cleared_before_rich_call(tmp_path: Path, monkeypatch) -> None:
    entrypoint = _load_entrypoint()
    stale = tmp_path / "rich_multiformat_analysis_lattice_v1.json"
    stale.write_text('{"stale": true}\n', encoding="utf-8")

    def raises_before_any_output(*args, **kwargs):
        assert not stale.exists()
        raise OSError("simulated_preflight_failure")

    monkeypatch.setattr(entrypoint.full_spine_module, "run_rich_lane", raises_before_any_output)
    entrypoint.full_spine_module._hpfa_construct_admission_gate_bound = False
    entrypoint._bind_construct_admission_gate()

    try:
        entrypoint.full_spine_module.run_rich_lane(tmp_path / "match", tmp_path)
    except OSError:
        pass
    else:
        raise AssertionError("expected simulated failure")
    assert not stale.exists()


def test_metric_governance_fail_closed_is_scoped_construct_block(monkeypatch) -> None:
    entrypoint = _load_entrypoint()

    def sidecars(*args, **kwargs):
        return {
            "status": "REVIEW_REQUIRED",
            "metric_governance_bridge": {
                "status": "FAIL_CLOSED",
                "hard_block_hits": ["metric_definition_policy_fail_closed"],
            },
        }

    def packet_builder(candidate):
        return {"status": "SMOKE_PASS", "candidate": candidate}

    monkeypatch.setattr(entrypoint.full_spine_module, "run_sidecars", sidecars)
    monkeypatch.setattr(entrypoint.full_spine_module, "build_composite_packet", packet_builder)
    entrypoint.full_spine_module._hpfa_metric_governance_gate_bound = False
    entrypoint._bind_metric_governance_construct_gate()

    sidecar_report = entrypoint.full_spine_module.run_sidecars(None, None, None)
    assert sidecar_report["construct_path_blocked"] is True
    assert sidecar_report["construct_path_block_reason"] == "metric_definition_policy_fail_closed"

    blocked = entrypoint.full_spine_module.build_composite_packet({"packet_family": "progression"})
    assert blocked["status"] == "FAIL_CLOSED"
    assert blocked["hard_block_hits"] == [
        "metric_governance_blocks_construct_promotion:metric_definition_policy_fail_closed"
    ]


def test_reconstruction_owned_outputs_form_current_invocation_ledger(tmp_path: Path, monkeypatch) -> None:
    match = tmp_path / "current"
    match.mkdir()
    (match / "surface.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    stale_row = out / "row_nucleus_inventory_lite_v1.json"
    stale_row.write_text('{"stale": true}\n', encoding="utf-8")

    def sequence_runner(input_dir, output):
        # Stale owned output must already be gone before the first producer.
        assert not stale_row.exists()
        stale_row.write_text('{"current": true}\n', encoding="utf-8")
        sequence_path = output / "visible_action_sequence_candidates_lite_v1.json"
        sequence_path.write_text('{"status":"SMOKE_PASS"}\n', encoding="utf-8")
        return {
            "status": "SMOKE_PASS",
            "visible_action_sequence_candidates": [{"visible_action_sequence_candidate_id": "s1"}],
            "outputs": {"sequence_json": str(sequence_path)},
        }

    def adapter_writer(sequence_payload, output):
        path = output / "reconstruction_intelligence_packet_adapter_lite_v1.json"
        path.write_text('{"status":"SMOKE_PASS"}\n', encoding="utf-8")
        return {
            "status": "SMOKE_PASS",
            "match_surface_binding_id": "msb_test",
            "source_visible_action_sequence_candidate_count": 1,
            "packet_input_candidate_count": 1,
            "review_required_packet_input_candidate_count": 0,
            "packet_input_assignment_complete": True,
            "composite_packet_input_candidates": [{"packet_family": "progression"}],
            "outputs": {"adapter_json": str(path)},
            "hard_block_hits": [],
            "review_hits": [],
        }

    def packet_writer(candidates, output):
        path = output / "composite_evidence_packet_builder_lite_v1.json"
        path.write_text('{"status":"SMOKE_PASS"}\n', encoding="utf-8")
        return {
            "status": "SMOKE_PASS",
            "packet_count": 1,
            "blocked_packet_count": 0,
            "packets": [{"packet_family": "progression"}],
            "outputs": {"packet_json": str(path)},
        }

    monkeypatch.setattr(reconstruction.current_sequence, "runtime_write_outputs", sequence_runner)
    monkeypatch.setattr(reconstruction.adapter, "write_outputs", adapter_writer)
    monkeypatch.setattr(reconstruction.packet_builder, "write_outputs", packet_writer)

    report = reconstruction.runtime_write_outputs(match, out)
    assert report["status"] == "SMOKE_PASS"
    assert "row_nucleus_inventory_lite_v1.json" in report["cleared_stale_reconstruction_owned_outputs"]
    assert str(stale_row) in report["current_invocation_artifacts"]
    assert str(out / "visible_action_sequence_candidates_lite_v1.json") in report["current_invocation_artifacts"]
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False

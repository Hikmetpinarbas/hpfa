from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_entrypoint():
    root = Path(__file__).resolve().parents[5]
    path = root / "active_match_spine_runner.py"
    spec = importlib.util.spec_from_file_location("hpfa_metric_runtime_binding_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate(label: str) -> dict:
    return {
        "packet_family": "progression",
        "input_metrics": [{
            "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
            "raw_metric_label": label,
        }],
    }


def _sidecar_report() -> dict:
    return {
        "status": "SMOKE_PASS",
        "metric_governance_bridge": {
            "status": "SMOKE_PASS",
            "aggregate_definition_alignment": {
                "alignment_rows": [{
                    "aggregate_label": "Passes accurate, %",
                    "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
                    "metric_definition_bound": True,
                    "aggregate_label_observed": True,
                    "rate_calculation_admitted": True,
                }]
            },
        },
    }


def test_runtime_blocks_xlsx_label_navigation_without_metric_semantic_authority(monkeypatch):
    entrypoint = _load_entrypoint()
    monkeypatch.setattr(entrypoint.full_spine_module, "run_sidecars", lambda *_a, **_k: _sidecar_report())
    monkeypatch.setattr(
        entrypoint.full_spine_module,
        "build_composite_packet",
        lambda candidate: {"status": "SMOKE_PASS", "candidate": candidate},
    )
    entrypoint.full_spine_module._hpfa_metric_governance_gate_bound = False
    entrypoint._bind_metric_governance_construct_gate()
    entrypoint.full_spine_module.run_sidecars(None, None, None)

    blocked = entrypoint.full_spine_module.build_composite_packet(_candidate("Progressive passes"))
    assert blocked["status"] == "REVIEW_REQUIRED"
    assert blocked["hard_block_hits"] == [
        "aggregate_semantics_blocks_construct_promotion:aggregate_metric_semantic_authority_missing"
    ]
    assert blocked["canonical_event_count"] == "UNKNOWN"
    assert blocked["true_action_count"] == "UNKNOWN"
    assert blocked["production_release"] is False


def test_runtime_allows_definition_bound_xlsx_metric_without_truth_promotion(monkeypatch):
    entrypoint = _load_entrypoint()
    monkeypatch.setattr(entrypoint.full_spine_module, "run_sidecars", lambda *_a, **_k: _sidecar_report())
    monkeypatch.setattr(
        entrypoint.full_spine_module,
        "build_composite_packet",
        lambda candidate: {"status": "SMOKE_PASS", "candidate": candidate},
    )
    entrypoint.full_spine_module._hpfa_metric_governance_gate_bound = False
    entrypoint._bind_metric_governance_construct_gate()
    entrypoint.full_spine_module.run_sidecars(None, None, None)

    packet = entrypoint.full_spine_module.build_composite_packet(_candidate("Passes accurate, %"))
    assert packet["status"] == "SMOKE_PASS"
    admission = packet["metric_governance_admission"]
    assert admission["admitted"] is True
    assert admission["construct_truth"] is False
    assert admission["aggregate_equivalence_truth"] is False
    assert admission["same_provider_multiformat_is_independent_support"] is False


def test_runtime_rehydrates_current_rich_construct_after_sidecars_run_first(monkeypatch):
    entrypoint = _load_entrypoint()

    monkeypatch.setattr(entrypoint.full_spine_module, "run_sidecars", lambda *_a, **_k: _sidecar_report())
    monkeypatch.setattr(
        entrypoint.full_spine_module,
        "run_rich_lane",
        lambda *_a, **_k: {
            "status": "REVIEW_REQUIRED",
            "constructs": {
                "C01": {
                    "status": "REVIEW_REQUIRED",
                    "review_reason": "aggregate_pair_scope_aligned_same_provider_support_non_independent",
                    "construct_truth": False,
                }
            },
            "c4_packet_candidates": [_candidate("Passes accurate, %")],
            "review_hits": ["C01_progression_terminal_construct_review_required"],
            "hard_block_hits": [],
            "outputs": {},
        },
    )
    monkeypatch.setattr(
        entrypoint.full_spine_module,
        "build_composite_packet",
        lambda candidate: {"status": "SMOKE_PASS", "candidate": candidate},
    )

    entrypoint.RICH_CONSTRUCT_RUNTIME_STATE["report"] = None
    entrypoint.full_spine_module._hpfa_construct_admission_gate_bound = False
    entrypoint.full_spine_module._hpfa_metric_governance_gate_bound = False

    entrypoint._bind_construct_admission_gate()
    entrypoint._bind_metric_governance_construct_gate()

    sidecars = entrypoint.full_spine_module.run_sidecars(None, None, None)
    assert sidecars["rich_construct_governance_recheck"]["evaluated"] is False

    rich = entrypoint.full_spine_module.run_rich_lane(None, None)
    assert rich["rich_construct_governance_recheck"]["evaluated"] is True
    assert rich["rich_construct_governance_recheck"]["admitted_count"] == 1
    assert len(rich["c4_packet_candidates"]) == 1
    assert rich["constructs"]["C01"]["c4_admission_status"] == "ADMITTED"
    assert rich["construct_c4_promotion_state"] == "ADMITTED_BY_METRIC_GOVERNANCE"

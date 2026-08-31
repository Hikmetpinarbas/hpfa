from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_entrypoint():
    root = Path(__file__).resolve().parents[5]
    path = root / "active_match_spine_runner.py"
    spec = importlib.util.spec_from_file_location("hpfa_active_match_entrypoint_construct_gate_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_required_construct_is_withheld_from_c4_and_remains_visible(tmp_path: Path) -> None:
    entrypoint = _load_entrypoint()
    lattice_json = tmp_path / "rich_multiformat_analysis_lattice_v1.json"
    lattice_txt = tmp_path / "rich_multiformat_analysis_lattice_v1.txt"
    lattice_json.write_text("{}\n", encoding="utf-8")
    lattice_txt.write_text("HPFA RICH MULTIFORMAT ANALYSIS LATTICE V1\n", encoding="utf-8")
    report = {
        "status": "REVIEW_REQUIRED",
        "constructs": {
            "C01": {
                "status": "REVIEW_REQUIRED",
                "review_reason": "occurrence_progression_semantics_not_yet_admitted_same_provider_support_non_independent",
                "construct_truth": False,
                "packet_candidate": {"packet_family": "progression"},
            }
        },
        "c4_packet_candidates": [{"packet_family": "progression"}],
        "outputs": {
            "lattice_json": str(lattice_json),
            "lattice_txt": str(lattice_txt),
        },
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    gated = entrypoint._apply_construct_admission_gate(report)

    assert gated["status"] == "REVIEW_REQUIRED"
    assert gated["c4_packet_candidates"] == []
    assert gated["construct_c4_promotion_withheld_count"] == 1
    assert gated["constructs"]["C01"]["c4_admission_status"] == "WITHHELD_PENDING_CONSTRUCT_ADMISSION"
    assert gated["constructs"]["C01"]["construct_truth"] is False
    persisted = json.loads(lattice_json.read_text(encoding="utf-8"))
    assert persisted["c4_packet_candidates"] == []
    assert "C01_c4_admission_status=WITHHELD_PENDING_CONSTRUCT_ADMISSION" in lattice_txt.read_text(encoding="utf-8")


def test_only_explicitly_admitted_nonreview_construct_may_reach_c4() -> None:
    entrypoint = _load_entrypoint()
    packet = {"packet_family": "progression"}
    report = {
        "status": "SMOKE_PASS",
        "constructs": {
            "C01": {
                "status": "SMOKE_PASS",
                "c4_admission_status": "ADMITTED",
                "construct_truth": False,
            }
        },
        "c4_packet_candidates": [packet],
    }
    gated = entrypoint._apply_construct_admission_gate(report)
    assert gated["c4_packet_candidates"] == [packet]
    assert "construct_c4_promotion_withheld_count" not in gated


def test_metric_governance_construct_gate_resets_state_for_each_run(monkeypatch) -> None:
    entrypoint = _load_entrypoint()
    full_spine = entrypoint.full_spine_module
    reports = iter([
        {
            "metric_governance_bridge": {
                "status": "FAIL_CLOSED",
                "hard_block_hits": ["synthetic_governance_block"],
            }
        },
        {
            "metric_governance_bridge": {
                "status": "REVIEW_REQUIRED",
                "hard_block_hits": [],
            }
        },
    ])

    monkeypatch.setattr(full_spine, "_hpfa_metric_governance_gate_bound", False, raising=False)
    monkeypatch.setattr(full_spine, "run_sidecars", lambda *args, **kwargs: next(reports))
    monkeypatch.setattr(
        full_spine,
        "build_composite_packet",
        lambda candidate: {"status": "PASS", "candidate": candidate},
    )

    entrypoint._bind_metric_governance_construct_gate()

    first = full_spine.run_sidecars()
    assert first["construct_path_blocked"] is True
    assert full_spine.build_composite_packet({"id": "first"})["status"] == "FAIL_CLOSED"

    second = full_spine.run_sidecars()
    assert "construct_path_blocked" not in second
    assert full_spine.build_composite_packet({"id": "second"}) == {
        "status": "PASS",
        "candidate": {"id": "second"},
    }

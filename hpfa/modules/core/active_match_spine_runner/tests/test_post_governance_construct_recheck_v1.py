from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_entrypoint():
    root = Path(__file__).resolve().parents[5]
    path = root / "active_match_spine_runner.py"
    spec = importlib.util.spec_from_file_location("hpfa_active_match_entrypoint_post_governance_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pending_report(raw_label: str) -> dict:
    candidate = {
        "packet_family": "progression",
        "input_metrics": [
            {
                "source_surface": "xlsx_entity_metric_row_projection_lite_v1",
                "raw_metric_label": raw_label,
            }
        ],
    }
    return {
        "status": "REVIEW_REQUIRED",
        "review_hits": ["C01_progression_terminal_construct_review_required"],
        "constructs": {
            "C01": {
                "status": "REVIEW_REQUIRED",
                "review_reason": "occurrence_progression_semantics_not_yet_admitted_same_provider_support_non_independent",
                "c4_admission_status": "WITHHELD_PENDING_CONSTRUCT_ADMISSION",
                "construct_truth": False,
            }
        },
        "pending_c4_packet_candidates": [candidate],
        "c4_packet_candidates": [],
        "outputs": {},
    }


def test_pending_construct_is_rehydrated_only_after_metric_alignment() -> None:
    entrypoint = _load_entrypoint()
    report = _pending_report("Progressive passes")
    entrypoint.RICH_CONSTRUCT_RUNTIME_STATE["report"] = report
    governance = {
        "status": "REVIEW_REQUIRED",
        "aggregate_definition_alignment": {
            "alignment_rows": [
                {
                    "aggregate_label": "Progressive passes",
                    "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
                    "metric_definition_bound": True,
                    "aggregate_label_observed": True,
                    "rate_calculation_admitted": True,
                }
            ]
        },
    }

    result = entrypoint._rehydrate_governance_admitted_constructs(governance)

    assert result["evaluated"] is True
    assert result["admitted_count"] == 1
    assert len(report["c4_packet_candidates"]) == 1
    assert report["constructs"]["C01"]["c4_admission_status"] == "ADMITTED"
    assert report["constructs"]["C01"]["status"] == "SMOKE_PASS"
    assert report["constructs"]["C01"]["construct_truth"] is False
    assert report["status"] == "SMOKE_PASS"


def test_unaligned_pending_construct_remains_withheld() -> None:
    entrypoint = _load_entrypoint()
    report = _pending_report("Unknown aggregate label")
    entrypoint.RICH_CONSTRUCT_RUNTIME_STATE["report"] = report
    governance = {
        "status": "REVIEW_REQUIRED",
        "aggregate_definition_alignment": {
            "alignment_rows": [
                {
                    "aggregate_label": "Progressive passes",
                    "alignment_decision": "DEFINITION_ALIGNMENT_CANDIDATE",
                    "metric_definition_bound": True,
                    "aggregate_label_observed": True,
                    "rate_calculation_admitted": True,
                }
            ]
        },
    }

    result = entrypoint._rehydrate_governance_admitted_constructs(governance)

    assert result["evaluated"] is True
    assert result["admitted_count"] == 0
    assert report["c4_packet_candidates"] == []
    assert report["constructs"]["C01"]["c4_admission_status"] == "WITHHELD_PENDING_CONSTRUCT_ADMISSION"
    assert report["constructs"]["C01"]["construct_truth"] is False

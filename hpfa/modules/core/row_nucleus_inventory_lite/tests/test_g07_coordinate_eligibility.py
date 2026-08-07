from __future__ import annotations

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory import (
    apply_coordinate_eligibility_rollup,
    coordinate_is_required,
)


def base_report(nuclei: list[dict], *, g16: str = "PASS") -> dict:
    gates = [
        {"gate_id": f"G{i:02d}", "status": "PASS", "message": "fixture", "evidence": {}}
        for i in range(1, 19)
    ]
    gates[6] = {
        "gate_id": "G07",
        "status": "REVIEW_REQUIRED",
        "message": "Coordinate surface checked.",
        "evidence": {"coordinate_missing_nucleus_count": 1},
    }
    gates[15] = {
        "gate_id": "G16",
        "status": g16,
        "message": "Aggregate derivation dependency checked.",
        "evidence": {},
    }
    return {
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "row_nuclei": nuclei,
        "row_nucleus_review_required_count": 0,
        "hard_block_hits": [],
        "review_hits": [],
        "g01_g18_rollup": {
            "status": "REVIEW_REQUIRED",
            "gates": gates,
            "pass_count": 17 if g16 == "PASS" else 16,
            "review_required_count": 1 if g16 == "PASS" else 2,
            "fail_closed_count": 0,
            "not_applicable_count": 0,
        },
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def g07(report: dict) -> dict:
    return next(
        gate for gate in report["g01_g18_rollup"]["gates"] if gate["gate_id"] == "G07"
    )


def g16(report: dict) -> dict:
    return next(
        gate for gate in report["g01_g18_rollup"]["gates"] if gate["gate_id"] == "G16"
    )


def test_admin_only_period_meta_missing_coordinate_is_exempt() -> None:
    record = {
        "semantic_role_candidates": ["PERIOD_OR_META"],
        "downstream_eligibility_candidates": ["ADMIN_ONLY"],
        "pos_x_candidate": None,
        "pos_y_candidate": None,
    }
    assert coordinate_is_required(record) is False
    report = apply_coordinate_eligibility_rollup(base_report([record]))
    assert report["coordinate_missing_nucleus_count"] == 1
    assert report["coordinate_missing_exempt_nucleus_count"] == 1
    assert report["coordinate_missing_required_nucleus_count"] == 0
    assert g07(report)["status"] == "PASS"
    assert report["g01_g18_rollup"]["status"] == "PASS"
    assert report["status"] == "PASS"


def test_action_eligible_missing_coordinate_remains_review_required() -> None:
    record = {
        "semantic_role_candidates": ["ACTION_ANCHOR"],
        "downstream_eligibility_candidates": ["ACTION_BUNDLE_CANDIDATE"],
        "pos_x_candidate": None,
        "pos_y_candidate": "34",
    }
    assert coordinate_is_required(record) is True
    report = apply_coordinate_eligibility_rollup(base_report([record]))
    assert report["coordinate_missing_exempt_nucleus_count"] == 0
    assert report["coordinate_missing_required_nucleus_count"] == 1
    assert g07(report)["status"] == "REVIEW_REQUIRED"
    assert report["status"] == "REVIEW_REQUIRED"


def test_numeric_zero_is_not_missing() -> None:
    record = {
        "semantic_role_candidates": ["ACTION_ANCHOR"],
        "downstream_eligibility_candidates": ["ACTION_BUNDLE_CANDIDATE"],
        "pos_x_candidate": "0",
        "pos_y_candidate": "0",
    }
    report = apply_coordinate_eligibility_rollup(base_report([record]))
    assert report["coordinate_missing_nucleus_count"] == 0
    assert report["coordinate_missing_exempt_nucleus_count"] == 0
    assert report["coordinate_missing_required_nucleus_count"] == 0
    assert g07(report)["status"] == "PASS"


def test_g16_review_is_preserved_when_g07_false_positive_is_removed() -> None:
    record = {
        "semantic_role_candidates": ["PERIOD_OR_META"],
        "downstream_eligibility_candidates": ["ADMIN_ONLY"],
        "pos_x_candidate": None,
        "pos_y_candidate": None,
    }
    report = apply_coordinate_eligibility_rollup(
        base_report([record], g16="REVIEW_REQUIRED")
    )
    assert g07(report)["status"] == "PASS"
    assert g16(report)["status"] == "REVIEW_REQUIRED"
    assert report["g01_g18_rollup"]["review_required_count"] == 1
    assert report["g01_g18_rollup"]["status"] == "REVIEW_REQUIRED"
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_mixed_or_unknown_admin_route_is_not_exempt() -> None:
    mixed = {
        "semantic_role_candidates": ["PERIOD_OR_META", "ACTION_ANCHOR"],
        "downstream_eligibility_candidates": ["ADMIN_ONLY"],
    }
    unknown = {
        "semantic_role_candidates": [],
        "downstream_eligibility_candidates": ["ADMIN_ONLY"],
    }
    assert coordinate_is_required(mixed) is True
    assert coordinate_is_required(unknown) is True


def test_no_sample_match_identity_leak() -> None:
    from pathlib import Path

    source = Path(
        "hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "Galatasaray",
        "Fenerbahce",
        "Fenerbahçe",
        "Besiktas",
        "Beşiktaş",
        "match001",
    )
    assert not any(token in source for token in forbidden)

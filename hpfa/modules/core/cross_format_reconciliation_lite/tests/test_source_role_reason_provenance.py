from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
WRAPPER = ROOT / "cross_format_reconciliation_lite.py"
SPEC = importlib.util.spec_from_file_location("cross_format_reconciliation_runtime_wrapper", WRAPPER)
assert SPEC and SPEC.loader
wrapper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wrapper)


def test_admitted_relational_role_drops_superseded_insufficiency_reason() -> None:
    resolution = {
        "resolution_status": "ROLE_CANDIDATE_ADMITTED",
        "resolution_reasons": [
            "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
            "AGGREGATE_SEMANTIC_UNIQUE_BEST_SUPPORT",
        ],
    }
    assert wrapper.admitted_role_reasons(resolution) == [
        "AGGREGATE_SEMANTIC_UNIQUE_BEST_SUPPORT"
    ]


def test_unresolved_or_nonrelational_state_preserves_insufficiency_reason() -> None:
    unresolved = {
        "resolution_status": "REVIEW_REQUIRED",
        "resolution_reasons": ["CONTENT_ROLE_EVIDENCE_INSUFFICIENT"],
    }
    assert wrapper.admitted_role_reasons(unresolved) == [
        "CONTENT_ROLE_EVIDENCE_INSUFFICIENT"
    ]

    admitted_direct = {
        "resolution_status": "ROLE_CANDIDATE_ADMITTED",
        "resolution_reasons": [
            "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
            "REVIEWED_PROVIDER_ROLE_SEMANTICS",
        ],
    }
    assert wrapper.admitted_role_reasons(admitted_direct) == [
        "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
        "REVIEWED_PROVIDER_ROLE_SEMANTICS",
    ]


def test_overlay_uses_cleaned_reason_provenance_without_changing_role() -> None:
    payload = {
        "files": [
            {
                "relative_path": "generic.csv",
                "source_role": "UNRESOLVED_SOURCE_ROLE_CANDIDATE",
            }
        ]
    }
    role_index = {
        "generic.csv": {
            "resolution_status": "ROLE_CANDIDATE_ADMITTED",
            "resolved_source_role": "PLAYER_SURFACE_CANDIDATE",
            "resolution_reasons": [
                "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
                "CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT",
            ],
        }
    }
    result = wrapper._overlay_resolved_roles(payload, role_index)
    row = result["files"][0]
    assert row["source_role"] == "PLAYER_SURFACE_CANDIDATE"
    assert row["inventory_source_role"] == "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
    assert row["source_role_resolution_reasons"] == [
        "CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT"
    ]
    assert row["filename_support_used_for_role_admission"] is False

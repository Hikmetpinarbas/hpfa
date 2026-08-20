from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
WRAPPER = ROOT / "triangulated_event_reflection_resolver_lite.py"

spec = importlib.util.spec_from_file_location("reflection_runtime_wrapper", WRAPPER)
assert spec and spec.loader
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


def _role_report():
    return {
        "status": "PASS",
        "hard_block_hits": [],
        "role_resolution_applicable_file_count": 3,
        "role_candidate_admitted_file_count": 3,
        "unresolved_role_file_count": 0,
        "resolved_role_counts": {
            "PLAYER_SURFACE_CANDIDATE": 1,
            "GOALKEEPER_SURFACE_CANDIDATE": 1,
            "TEAM_SURFACE_CANDIDATE": 1,
        },
        "files": [
            {
                "relative_path": "generic-a.csv",
                "resolution": {
                    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
                    "resolved_source_role": "PLAYER_SURFACE_CANDIDATE",
                },
            },
            {
                "relative_path": "generic-b.xml",
                "resolution": {
                    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
                    "resolved_source_role": "GOALKEEPER_SURFACE_CANDIDATE",
                },
            },
            {
                "relative_path": "generic-c.csv",
                "resolution": {
                    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
                    "resolved_source_role": "TEAM_SURFACE_CANDIDATE",
                },
            },
        ],
    }


def test_content_roles_override_generic_filenames(monkeypatch, tmp_path):
    role_report = _role_report()
    monkeypatch.setattr(wrapper.role_resolver, "build_report", lambda *a, **k: role_report)

    def fake_core_build_report(*args, **kwargs):
        return {
            "module_id": wrapper.core.MODULE_ID,
            "status": "REVIEW_REQUIRED",
            "decision": "VISIBLE_FIELD_SERIALIZATION_DISCREPANCY",
            "observed_roles": [
                wrapper.core.source_role_from_name(Path("generic-a.csv")),
                wrapper.core.source_role_from_name(Path("generic-b.xml")),
                wrapper.core.source_role_from_name(Path("generic-c.csv")),
            ],
            "canonical_event_count": "UNKNOWN",
        }

    monkeypatch.setattr(wrapper, "_CORE_BUILD_REPORT", fake_core_build_report)
    result = wrapper.runtime_build_report(tmp_path, root=ROOT)

    assert result["observed_roles"] == ["PLAYER", "GOALKEEPER", "TEAM"]
    assert result["content_source_role_bridge"]["status"] == "PASS"
    assert result["filename_support_used_for_role_admission"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_unresolved_content_role_fails_closed(monkeypatch, tmp_path):
    report = _role_report()
    report["status"] = "REVIEW_REQUIRED"
    report["role_candidate_admitted_file_count"] = 2
    report["unresolved_role_file_count"] = 1
    monkeypatch.setattr(wrapper.role_resolver, "build_report", lambda *a, **k: report)

    result = wrapper.runtime_build_report(tmp_path, root=ROOT)

    assert result["status"] == "FAIL_CLOSED"
    assert "content_source_role_resolution_gate_not_pass" in result["hard_block_hits"]
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["physical_action_identity_truth"] is False
    assert result["production_release"] is False

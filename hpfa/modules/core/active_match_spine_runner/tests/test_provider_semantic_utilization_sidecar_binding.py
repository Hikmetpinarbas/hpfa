from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def test_sidecar_materializes_provider_semantic_utilization_as_support_only(tmp_path: Path):
    rows = [
        {
            "source_format": "csv",
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "surface_row_volume": 8,
            "semantic_role_candidate": "ACTION_ANCHOR",
            "action_family_candidate": "PASS",
            "downstream_eligibility": "ACTION_CANDIDATE",
        },
        {
            "source_format": "csv",
            "mapping_status": "TOKEN_FALLBACK_REVIEW_REQUIRED",
            "surface_row_volume": 2,
            "semantic_role_candidate": "UNKNOWN_UNREVIEWED",
            "downstream_eligibility": "ACTION_CANDIDATE",
        },
        {
            "source_format": "xml",
            "mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "surface_row_volume": 8,
            "semantic_role_candidate": "ACTION_ANCHOR",
            "action_family_candidate": "PASS",
            "downstream_eligibility": "ACTION_CANDIDATE",
        },
    ]
    (tmp_path / sidecars.PROVIDER_LABEL_SEMANTICS_OUTPUT).write_text(
        json.dumps({"provider_label_records": rows}),
        encoding="utf-8",
    )

    with patch.object(
        sidecars.report_lite,
        "write_report",
        return_value={"status": "PASS", "engineering_evidence": {}},
    ), patch.object(
        sidecars,
        "run_metric_governance_bridge",
        return_value={"status": "SMOKE_PASS", "current_invocation_artifacts": []},
    ):
        report = sidecars.run_sidecars(tmp_path, tmp_path, tmp_path)

    target = tmp_path / sidecars.PROVIDER_SEMANTIC_UTILIZATION_OUTPUT
    assert target.is_file()
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert report["provider_semantic_utilization_status"] == "PASS"
    assert report["provider_semantic_utilization_prerequisite_present"] is True
    assert payload["csv"]["surface_label_volume"] == 10
    assert payload["csv"]["mapped_semantic_label_volume"] == 8
    assert payload["csv"]["review_required_label_volume"] == 2
    assert payload["csv"]["mapped_semantic_label_volume_ratio"] == 0.8
    assert payload["csv_xml_combined_is_independent_evidence_count"] is False
    assert payload["cross_format_volume_must_not_be_interpreted_as_action_count"] is True
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False

    names = {Path(value).name for value in report["current_invocation_artifacts"]}
    assert sidecars.PROVIDER_SEMANTIC_UTILIZATION_OUTPUT in names

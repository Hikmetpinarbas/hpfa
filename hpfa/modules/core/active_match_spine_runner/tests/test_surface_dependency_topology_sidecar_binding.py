from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def test_sidecar_materializes_surface_dependency_topology_without_independence_promotion(tmp_path: Path):
    (tmp_path / "cross_format_reconciliation_lite_v1.json").write_text(
        json.dumps({
            "module_id": "cross_format_reconciliation_lite_v1",
            "status": "PASS",
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
            "hard_block_hits": [],
            "pair_reports": [{
                "pair_id": "pair_1",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "decision": "PASS_ALIGNMENT_CANDIDATE",
                "exact_surface_alignment_candidate_count": 2,
                "required_field_mismatch_candidate_count": 0,
                "xlsx_support": {},
            }],
        }),
        encoding="utf-8",
    )
    (tmp_path / "cross_role_relation_candidate_resolver_lite_v1.json").write_text(
        json.dumps({
            "module_id": "cross_role_relation_candidate_resolver_lite_v1",
            "status": "PASS",
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
            "hard_block_hits": [],
            "resolved_relation_candidates": [{
                "resolved_relation_candidate_id": "rel_1",
                "source_roles": ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
                "relation_record_status": "PASS_CANDIDATE_CLASSIFICATION",
            }],
        }),
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

    topology_path = tmp_path / sidecars.SURFACE_DEPENDENCY_TOPOLOGY_OUTPUT
    assert topology_path.is_file()
    topology = json.loads(topology_path.read_text(encoding="utf-8"))

    assert report["surface_dependency_topology_status"] == "PASS"
    assert report["surface_dependency_topology_prerequisite_present"] is True
    assert topology["surface_dependency_record_count"] == 2
    assert topology["dependency_type_counts"] == {
        "PARTIAL_SEMANTIC_PROJECTION": 1,
        "SERIALIZATION_REFLECTION": 1,
    }
    assert topology["independent_support_created"] is False
    assert topology["occurrence_identity_created"] is False
    assert topology["canonical_event_count"] == "UNKNOWN"
    assert topology["true_action_count"] == "UNKNOWN"
    assert topology["production_release"] is False

    artifact_names = {Path(value).name for value in report["current_invocation_artifacts"]}
    assert sidecars.SURFACE_DEPENDENCY_TOPOLOGY_OUTPUT in artifact_names

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "support" / "surface_inventory_interpretation_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from surface_inventory_interpretation_gate import build_gate, write_outputs


def write_inputs(out: Path):
    out.mkdir(parents=True)
    (out / "canonical_event_lite_audit_v1.json").write_text(json.dumps({
        "status": "PASS",
        "surface_row_inventory_total": 100,
        "surface_role_row_counts": {"players": 40, "teams": 50, "goalkeepers": 10},
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "primary_event_surface_candidate": "UNRESOLVED",
        "event_count_claim_allowed": False,
    }), encoding="utf-8")
    (out / "team_binding_lite_audit_v1.json").write_text(json.dumps({
        "status": "PASS",
        "surface_row_inventory_total": 100,
        "team_entity_count": 2,
        "player_entity_count": 5,
        "unresolved_team_rows": 20,
    }), encoding="utf-8")
    (out / "fitness_tactical_bridge_lite_v1.json").write_text(json.dumps({
        "status": "PASS",
        "cross_surface_review_candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}],
    }), encoding="utf-8")


def test_gate_translates_raw_counts_to_analyst_safe_language(tmp_path):
    out = tmp_path / "HPFA"
    write_inputs(out)

    report = build_gate(out)

    assert report["status"] == "PASS"
    assert report["surface_inventory_summary"]["surface_row_inventory_total"] == 100
    assert report["surface_inventory_summary"]["event_count_claim_allowed"] is False
    assert report["identity_binding_summary"]["uses_surface_inventory_semantics"] is True
    assert report["bridge_summary"]["candidate_count"] == 2
    assert report["pattern_structure_status"] == "NOT_BUILT_REQUIRES_LATER_GATES"
    rendered = json.dumps(report, ensure_ascii=False).lower()
    assert "not a deduplicated event count" in rendered
    assert "match event count" not in rendered


def test_gate_writes_flat_outputs(tmp_path):
    out = tmp_path / "HPFA"
    write_inputs(out)

    report = write_outputs(out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "surface_inventory_interpretation_gate_lite_v1.json").exists()
    assert (out / "surface_inventory_interpretation_gate_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/surface-gate", root=ROOT)

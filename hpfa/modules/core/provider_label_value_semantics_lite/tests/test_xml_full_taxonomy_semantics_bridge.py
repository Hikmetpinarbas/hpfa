from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "src"
REGISTRY = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "registry" / "sportsbase_label_semantics_seed_v1.json"
sys.path.insert(0, str(SRC))

from provider_label_value_semantics import load_registry, xml_label_records

SHA = "b" * 64


def test_full_xml_action_taxonomy_is_consumed_before_example_fallback() -> None:
    payload = {
        "module_id": "xml_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "production_release": False,
        "files": [
            {
                "relative_path": "raw/Players.xml",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "sha256": SHA,
                "action_taxonomy": [
                    {"raw_group": "Action", "raw_label": "Passes accurate", "surface_row_volume": 10},
                    {"raw_group": "Action", "raw_label": "Shots", "surface_row_volume": 4},
                ],
                "example_rows": [
                    {
                        "instance.label.group": ["Action", "Team"],
                        "instance.label.text": ["Passes accurate", "TEAM_A"],
                    }
                ],
            }
        ],
    }

    records = xml_label_records(payload, load_registry(REGISTRY))
    by_label = {row["raw_label"]: row for row in records}

    assert set(by_label) == {"Passes accurate", "Shots"}
    assert by_label["Passes accurate"]["surface_row_volume"] == 10
    assert by_label["Shots"]["surface_row_volume"] == 4
    assert all(
        row["evidence_scope"] == "FULL_XML_ACTION_LABEL_SURFACE_VOLUME_NOT_ROW_IDENTITY"
        for row in records
    )
    assert all(row["validated_semantics"] is False for row in records)

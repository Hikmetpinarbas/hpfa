from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from xml_rows import profile_rows


def test_full_xml_action_inventory_reaches_rows_after_preview_limit(tmp_path: Path) -> None:
    path = tmp_path / "match.xml"
    labels = ["Pass", "Pass", "Shot", "Carry", "Duel"]
    rows = "".join(
        f"<instance><label><group>Action</group><text>{label}</text></label></instance>"
        for label in labels
    )
    path.write_text(f"<file>{rows}</file>", encoding="utf-8")

    payload = profile_rows(path, "instance")
    taxonomy = {
        row["raw_label"]: row["surface_row_volume"]
        for row in payload["action_taxonomy"]
    }

    assert len(payload["example_rows"]) == 3
    assert payload["action_taxonomy_surface_row_volume"] == 5
    assert taxonomy == {"Pass": 2, "Shot": 1, "Carry": 1, "Duel": 1}
    assert payload["action_taxonomy_is_event_identity"] is False
    assert all(row["validated_semantics"] is False for row in payload["action_taxonomy"])
    assert all(
        row["claim_ceiling"] == "XML_ACTION_LABEL_SURFACE_VOLUME_ONLY"
        for row in payload["action_taxonomy"]
    )


def test_non_action_labels_do_not_enter_full_action_inventory(tmp_path: Path) -> None:
    path = tmp_path / "match.xml"
    path.write_text(
        "<file>"
        "<instance><label><group>Action</group><text>Pass</text></label></instance>"
        "<instance><label><group>Context</group><text>Possession</text></label></instance>"
        "</file>",
        encoding="utf-8",
    )

    payload = profile_rows(path, "instance")
    assert [row["raw_label"] for row in payload["action_taxonomy"]] == ["Pass"]
    assert payload["action_taxonomy_surface_row_volume"] == 1

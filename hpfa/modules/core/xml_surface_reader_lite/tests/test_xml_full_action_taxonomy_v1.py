from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from xml_rows import profile_rows  # noqa: E402


def _xml_with_actions(labels: list[str]) -> str:
    instances = []
    for index, label in enumerate(labels, start=1):
        instances.append(
            f"<instance id='{index}'><labels><label><group>Action</group><text>{label}</text></label></labels></instance>"
        )
    return "<file>" + "".join(instances) + "</file>"


def test_full_action_taxonomy_counts_all_rows_not_only_examples(tmp_path: Path) -> None:
    path = tmp_path / "match.xml"
    path.write_text(
        _xml_with_actions(["Pass", "Shot", "Pass", "Carry", "Pass"]),
        encoding="utf-8",
    )

    payload = profile_rows(path, "instance")
    taxonomy = {row["raw_label"]: row["surface_row_volume"] for row in payload["action_taxonomy"]}

    assert payload["row_candidate_count"] == 5
    assert len(payload["example_rows"]) == 3
    assert payload["action_taxonomy_surface_row_volume"] == 5
    assert taxonomy == {"Pass": 3, "Shot": 1, "Carry": 1}


def test_full_action_taxonomy_never_promotes_event_identity(tmp_path: Path) -> None:
    path = tmp_path / "match.xml"
    path.write_text(_xml_with_actions(["Pass", "Pass"]), encoding="utf-8")

    payload = profile_rows(path, "instance")

    assert payload["action_taxonomy_is_event_identity"] is False
    assert all(row["event_identity"] is False for row in payload["action_taxonomy"])
    assert all(
        row["claim_ceiling"] == "XML_ACTION_LABEL_SURFACE_VOLUME_ONLY"
        for row in payload["action_taxonomy"]
    )


def test_non_action_groups_do_not_enter_action_taxonomy(tmp_path: Path) -> None:
    path = tmp_path / "match.xml"
    path.write_text(
        "<file><instance><labels>"
        "<label><group>Context</group><text>Build Up</text></label>"
        "<label><group>Action</group><text>Pass</text></label>"
        "</labels></instance></file>",
        encoding="utf-8",
    )

    payload = profile_rows(path, "instance")

    assert payload["action_taxonomy_surface_row_volume"] == 1
    assert [row["raw_label"] for row in payload["action_taxonomy"]] == ["Pass"]


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "xml_rows.py").read_text(encoding="utf-8").casefold()
    forbidden = ["genclerbirligi", "fenerbahce", "galatasaray", "15.08.2026"]
    assert not any(token in text for token in forbidden)

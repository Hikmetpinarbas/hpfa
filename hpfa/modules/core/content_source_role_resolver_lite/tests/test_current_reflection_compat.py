from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.content_source_role_resolver_lite.src import (
    content_source_role_resolver as resolver,
)


def test_current_reflection_api_is_canonicalized_without_filename_role_truth(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "generic.csv"
    csv_path.write_text(
        "ID,start,end,code,action,half,pos_x,pos_y\n"
        "1,0.0,1.0,Club - PASS,PASS,1,10.0,20.0\n",
        encoding="utf-8",
    )
    xml_path = tmp_path / "generic.xml"
    xml_path.write_text(
        "<root><instance>"
        "<ID>1</ID><start>0</start><end>1</end><code>Club - PASS</code>"
        "<label><group>Action</group><text>PASS</text></label>"
        "<label><group>Half</group><text>1</text></label>"
        "<label><group>Team</group><text>Club</text></label>"
        "<label><group>pos_x</group><text>10</text></label>"
        "<label><group>pos_y</group><text>20</text></label>"
        "</instance></root>",
        encoding="utf-8",
    )

    csv_rows = resolver.surface_rows(csv_path)
    xml_rows = resolver.surface_rows(xml_path)

    assert len(csv_rows) == 1
    assert len(xml_rows) == 1
    assert xml_rows[0]["team"] == "club"
    assert xml_rows[0]["action"] == "pass"
    assert xml_rows[0]["half"] == "1"
    assert xml_rows[0]["pos_x"] == "10"
    assert xml_rows[0]["pos_y"] == "20"
    assert resolver.roleless_row_fingerprint(csv_rows[0]) == (
        resolver.roleless_row_fingerprint(xml_rows[0])
    )
    assert resolver.reflection.FINGERPRINT_FIELDS == (
        "provider_row_id",
        "start",
        "end",
        "code",
        "team",
        "action",
        "half",
        "pos_x",
        "pos_y",
    )

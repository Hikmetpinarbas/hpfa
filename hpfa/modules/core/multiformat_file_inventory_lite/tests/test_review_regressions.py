from __future__ import annotations

import codecs
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "multiformat_file_inventory_lite" / "src"
sys.path.insert(0, str(SRC))

from multiformat_file_inventory import build_inventory


def _encoded_xml(text: str, encoding: str) -> bytes:
    bom_by_encoding = {
        "utf-16-le": codecs.BOM_UTF16_LE,
        "utf-16-be": codecs.BOM_UTF16_BE,
        "utf-32-le": codecs.BOM_UTF32_LE,
        "utf-32-be": codecs.BOM_UTF32_BE,
    }
    return bom_by_encoding.get(encoding, b"") + text.encode(encoding)


def test_root_cli_wrapper_is_importable_without_self_import() -> None:
    wrapper = ROOT / "multiformat_file_inventory.py"
    spec = importlib.util.spec_from_file_location(
        "_hpfa_multiformat_file_inventory_wrapper_test",
        wrapper,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert module.main.__module__ != module.__name__
    assert module.main.__module__.startswith("_hpfa_multiformat_file_inventory_")


@pytest.mark.parametrize(
    ("encoding", "declaration"),
    [
        ("utf-8", "UTF-8"),
        ("utf-16-le", "UTF-16"),
        ("utf-16-be", "UTF-16"),
        ("utf-32-le", "UTF-32"),
        ("utf-32-be", "UTF-32"),
    ],
)
def test_encoded_xml_doctype_is_blocked_before_parse(
    tmp_path: Path,
    encoding: str,
    declaration: str,
) -> None:
    path = tmp_path / f"doctype-{encoding}.xml"
    text = (
        f'<?xml version="1.0" encoding="{declaration}"?>\n'
        "<!DOCTYPE root>\n"
        "<root><event id=\"1\" /></root>\n"
    )
    path.write_bytes(_encoded_xml(text, encoding))

    result = build_inventory(tmp_path)
    item = result["files"][0]

    assert item["parse_status"] == "FAIL_CLOSED"
    assert "external_entity_resolution_attempted" in item["hard_block_hits"]
    assert result["status"] == "FAIL_CLOSED"


def test_utf16_external_entity_is_blocked_before_parse(tmp_path: Path) -> None:
    path = tmp_path / "entity-utf16.xml"
    text = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
        "<root><event>&xxe;</event></root>\n"
    )
    path.write_bytes(_encoded_xml(text, "utf-16-le"))

    result = build_inventory(tmp_path)
    item = result["files"][0]

    assert item["parse_status"] == "FAIL_CLOSED"
    assert "external_entity_resolution_attempted" in item["hard_block_hits"]
    assert result["status"] == "FAIL_CLOSED"


def test_no_sample_match_identity_leak_across_split_source() -> None:
    source = "\n".join(
        (SRC / name).read_text(encoding="utf-8")
        for name in (
            "multiformat_file_inventory.py",
            "multiformat_file_inventory_impl.py",
        )
    )
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source for token in forbidden)

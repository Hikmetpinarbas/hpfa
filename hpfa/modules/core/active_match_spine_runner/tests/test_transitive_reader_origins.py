import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(SRC))

from spine_runner import _content_source_role_resolver_module  # noqa: E402


def test_product_transitive_reader_implementation_origins_are_exact():
    resolver = _content_source_role_resolver_module(ROOT)

    xlsx_native_reader = resolver.xlsx_surface_reader.native_reader
    expected_xlsx = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "xlsx_surface_reader_lite"
        / "src"
        / "xlsx_surface_reader"
        / "native_reader.py"
    )
    assert Path(xlsx_native_reader.__file__).resolve() == expected_xlsx.resolve()
    assert resolver.xlsx_surface_reader.inspect_xlsx_file is xlsx_native_reader.inspect_xlsx_file

    inventory_impl = resolver.multiformat_file_inventory._impl
    expected_inventory = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "multiformat_file_inventory_lite"
        / "src"
        / "multiformat_file_inventory_impl.py"
    )
    assert Path(inventory_impl.__file__).resolve() == expected_inventory.resolve()
    assert resolver.multiformat_file_inventory.build_inventory is inventory_impl.build_inventory

    assert resolver.xml_surface_reader.security_guard is sys.modules["xml_common"].security_guard
    assert resolver.xml_surface_reader.profile_rows is sys.modules["xml_rows"].profile_rows
    assert resolver.xml_surface_reader.scan_structure is sys.modules["xml_structure"].scan_structure
    assert resolver.xml_surface_reader.XmlSurfaceError is sys.modules["xml_common"].XmlSurfaceError

    xml_common = sys.modules["xml_common"]
    assert sys.modules["xml_rows"].local_name is xml_common.local_name
    assert sys.modules["xml_rows"].role_for_field is xml_common.role_for_field
    assert sys.modules["xml_structure"].local_name is xml_common.local_name
    assert sys.modules["xml_structure"].namespace_uri is xml_common.namespace_uri


def test_cached_xlsx_nested_reader_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    resolver = _content_source_role_resolver_module(ROOT)
    fake_native_reader = types.SimpleNamespace(
        __file__=str(tmp_path / "adversary" / "native_reader.py")
    )
    fake_native_reader.inspect_xlsx_file = lambda *_args, **_kwargs: {}

    monkeypatch.setattr(resolver.xlsx_surface_reader, "native_reader", fake_native_reader)
    monkeypatch.setattr(
        resolver.xlsx_surface_reader,
        "inspect_xlsx_file",
        fake_native_reader.inspect_xlsx_file,
    )
    monkeypatch.setitem(
        sys.modules,
        "hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader.native_reader",
        fake_native_reader,
    )

    with pytest.raises(
        ValueError,
        match=r"runtime_module_origin_mismatch:xlsx_surface_reader\.native_reader",
    ):
        _content_source_role_resolver_module(ROOT)


def test_cached_multiformat_inventory_impl_from_wrong_origin_fails_closed(
    monkeypatch,
    tmp_path,
):
    resolver = _content_source_role_resolver_module(ROOT)
    fake_inventory_impl = types.SimpleNamespace(
        __file__=str(tmp_path / "reflection" / "multiformat_file_inventory_impl.py")
    )
    fake_inventory_impl.build_inventory = lambda *_args, **_kwargs: {}

    monkeypatch.setattr(
        resolver.multiformat_file_inventory,
        "_impl",
        fake_inventory_impl,
    )
    monkeypatch.setattr(
        resolver.multiformat_file_inventory,
        "build_inventory",
        fake_inventory_impl.build_inventory,
    )
    monkeypatch.setitem(
        sys.modules,
        "_hpfa_multiformat_file_inventory_core",
        fake_inventory_impl,
    )

    with pytest.raises(
        ValueError,
        match=r"runtime_module_origin_mismatch:multiformat_file_inventory\._impl",
    ):
        _content_source_role_resolver_module(ROOT)


def test_stale_xml_reader_callable_binding_fails_closed_before_resolver_execution(
    monkeypatch,
):
    resolver = _content_source_role_resolver_module(ROOT)

    def adversarial_security_guard(*_args, **_kwargs):
        raise AssertionError("stale XML helper must never execute")

    monkeypatch.setattr(
        resolver.xml_surface_reader,
        "security_guard",
        adversarial_security_guard,
    )

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_callable_binding_mismatch:"
            r"xml_surface_reader\.security_guard"
        ),
    ):
        _content_source_role_resolver_module(ROOT)


@pytest.mark.parametrize(
    ("module_name", "attribute"),
    [
        ("xml_rows", "role_for_field"),
        ("xml_structure", "local_name"),
    ],
)
def test_stale_xml_common_binding_captured_inside_product_module_fails_closed(
    monkeypatch,
    module_name,
    attribute,
):
    _content_source_role_resolver_module(ROOT)
    implementation_module = sys.modules[module_name]
    xml_common = sys.modules["xml_common"]
    assert getattr(implementation_module, attribute) is getattr(xml_common, attribute)

    def adversarial_helper(*_args, **_kwargs):
        raise AssertionError("stale XML captured helper must never execute")

    monkeypatch.setattr(implementation_module, attribute, adversarial_helper)

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_import_binding_mismatch:"
            + rf"{module_name}\.{attribute}"
        ),
    ):
        _content_source_role_resolver_module(ROOT)

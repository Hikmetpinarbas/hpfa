import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(SRC))

from spine_runner import _content_source_role_resolver_module  # noqa: E402


NATIVE_READER_MODULE = (
    "hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader.native_reader"
)
NATIVE_OOXML_MODULE = "hpfa.modules.core.xlsx_surface_reader_lite.src.native_ooxml"
HEADER_SEMANTICS_MODULE = (
    "hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_header_semantics"
)

XML_SURFACE_READER_XML_COMMON_BINDINGS = (
    "CANONICAL_EVENT_COUNT",
    "CLAIM_CEILING",
    "MODULE_ID",
    "OUT",
    "XmlSurfaceError",
    "is_active",
    "representatives",
    "resolve_inventory_path",
    "security_guard",
    "validate_out",
)


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
    expected_ooxml = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "xlsx_surface_reader_lite"
        / "src"
        / "native_ooxml.py"
    )
    expected_header_semantics = (
        ROOT
        / "hpfa"
        / "modules"
        / "core"
        / "xlsx_surface_reader_lite"
        / "src"
        / "xlsx_header_semantics.py"
    )
    native_ooxml = sys.modules[NATIVE_OOXML_MODULE]
    header_semantics = sys.modules[HEADER_SEMANTICS_MODULE]

    assert Path(xlsx_native_reader.__file__).resolve() == expected_xlsx.resolve()
    assert Path(native_ooxml.__file__).resolve() == expected_ooxml.resolve()
    assert Path(header_semantics.__file__).resolve() == expected_header_semantics.resolve()
    assert resolver.xlsx_surface_reader.inspect_xlsx_file is xlsx_native_reader.inspect_xlsx_file
    assert xlsx_native_reader.load_workbook is native_ooxml.load_workbook
    assert xlsx_native_reader.InvalidFileException is native_ooxml.InvalidFileException
    assert xlsx_native_reader._semantic_header_norm is header_semantics.semantic_header_norm

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

    xml_common = sys.modules["xml_common"]
    for attribute in XML_SURFACE_READER_XML_COMMON_BINDINGS:
        assert getattr(resolver.xml_surface_reader, attribute) is getattr(xml_common, attribute)
    assert resolver.xml_surface_reader.profile_rows is sys.modules["xml_rows"].profile_rows
    assert resolver.xml_surface_reader.scan_structure is sys.modules["xml_structure"].scan_structure

    assert sys.modules["xml_rows"].local_name is xml_common.local_name
    assert sys.modules["xml_rows"].role_for_field is xml_common.role_for_field
    assert sys.modules["xml_structure"].local_name is xml_common.local_name
    assert sys.modules["xml_structure"].namespace_uri is xml_common.namespace_uri


def test_cached_xlsx_native_ooxml_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    resolver = _content_source_role_resolver_module(ROOT)
    xlsx_native_reader = resolver.xlsx_surface_reader.native_reader
    product_ooxml = sys.modules[NATIVE_OOXML_MODULE]
    fake_ooxml = types.SimpleNamespace(
        __file__=str(tmp_path / "adversary" / "native_ooxml.py"),
        load_workbook=product_ooxml.load_workbook,
        InvalidFileException=product_ooxml.InvalidFileException,
    )
    assert Path(xlsx_native_reader.__file__).resolve().name == "native_reader.py"

    monkeypatch.setitem(sys.modules, NATIVE_OOXML_MODULE, fake_ooxml)

    with pytest.raises(
        ValueError,
        match=r"runtime_module_origin_mismatch:xlsx_surface_reader\.native_ooxml",
    ):
        _content_source_role_resolver_module(ROOT)


def test_same_foreign_xlsx_reader_helper_tree_fails_against_product_package_anchor(
    monkeypatch,
    tmp_path,
):
    resolver = _content_source_role_resolver_module(ROOT)
    package = resolver.xlsx_surface_reader
    foreign_src = tmp_path / "foreign_checkout" / "xlsx_surface_reader_lite" / "src"

    class ForeignInvalidFileException(Exception):
        pass

    def foreign_load_workbook(*_args, **_kwargs):
        raise AssertionError("foreign XLSX parser must never execute")

    def foreign_header_norm(*_args, **_kwargs):
        raise AssertionError("foreign XLSX header helper must never execute")

    def foreign_inspect_xlsx_file(*_args, **_kwargs):
        raise AssertionError("foreign XLSX inspection must never execute")

    fake_reader = types.SimpleNamespace(
        __file__=str(foreign_src / "xlsx_surface_reader" / "native_reader.py"),
        load_workbook=foreign_load_workbook,
        InvalidFileException=ForeignInvalidFileException,
        _semantic_header_norm=foreign_header_norm,
        inspect_xlsx_file=foreign_inspect_xlsx_file,
    )
    fake_ooxml = types.SimpleNamespace(
        __file__=str(foreign_src / "native_ooxml.py"),
        load_workbook=foreign_load_workbook,
        InvalidFileException=ForeignInvalidFileException,
    )
    fake_header_semantics = types.SimpleNamespace(
        __file__=str(foreign_src / "xlsx_header_semantics.py"),
        semantic_header_norm=foreign_header_norm,
    )

    monkeypatch.setattr(package, "native_reader", fake_reader)
    monkeypatch.setattr(package, "inspect_xlsx_file", foreign_inspect_xlsx_file)
    monkeypatch.setattr(package, "_NATIVE_READER_IMPL", fake_reader)
    monkeypatch.setitem(sys.modules, NATIVE_READER_MODULE, fake_reader)
    monkeypatch.setitem(sys.modules, NATIVE_OOXML_MODULE, fake_ooxml)
    monkeypatch.setitem(sys.modules, HEADER_SEMANTICS_MODULE, fake_header_semantics)

    with pytest.raises(
        ValueError,
        match=r"runtime_module_origin_mismatch:xlsx_surface_reader\.native_reader",
    ):
        resolver.resolve_xlsx(Path("unused-foreign-tree.xlsx"), {})


def test_product_native_reader_with_stale_load_workbook_capture_fails_closed(monkeypatch):
    resolver = _content_source_role_resolver_module(ROOT)
    xlsx_native_reader = resolver.xlsx_surface_reader.native_reader
    product_ooxml = sys.modules[NATIVE_OOXML_MODULE]
    assert xlsx_native_reader.load_workbook is product_ooxml.load_workbook

    def adversarial_load_workbook(*_args, **_kwargs):
        raise AssertionError("stale XLSX load_workbook must never execute")

    monkeypatch.setattr(xlsx_native_reader, "load_workbook", adversarial_load_workbook)

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_import_binding_mismatch:"
            r"xlsx_surface_reader\.native_reader\.load_workbook"
        ),
    ):
        _content_source_role_resolver_module(ROOT)


def test_direct_resolver_xlsx_entrypoint_rejects_stale_load_workbook_before_execution(
    monkeypatch,
):
    resolver = _content_source_role_resolver_module(ROOT)
    xlsx_native_reader = resolver.xlsx_surface_reader.native_reader
    product_ooxml = sys.modules[NATIVE_OOXML_MODULE]
    assert xlsx_native_reader.load_workbook is product_ooxml.load_workbook

    def adversarial_load_workbook(*_args, **_kwargs):
        raise AssertionError("direct resolver must not execute stale XLSX helper")

    monkeypatch.setattr(xlsx_native_reader, "load_workbook", adversarial_load_workbook)

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_import_binding_mismatch:"
            r"xlsx_surface_reader\.native_reader\.load_workbook"
        ),
    ):
        resolver.resolve_xlsx(Path("unused-adversarial.xlsx"), {})


def test_product_native_reader_with_stale_header_normalizer_capture_fails_closed(
    monkeypatch,
):
    resolver = _content_source_role_resolver_module(ROOT)
    xlsx_native_reader = resolver.xlsx_surface_reader.native_reader
    header_semantics = sys.modules[HEADER_SEMANTICS_MODULE]
    assert xlsx_native_reader._semantic_header_norm is header_semantics.semantic_header_norm

    def adversarial_header_norm(*_args, **_kwargs):
        raise AssertionError("stale XLSX header normalizer must never execute")

    monkeypatch.setattr(
        xlsx_native_reader,
        "_semantic_header_norm",
        adversarial_header_norm,
    )

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_import_binding_mismatch:"
            r"xlsx_surface_reader\.native_reader\._semantic_header_norm"
        ),
    ):
        _content_source_role_resolver_module(ROOT)


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
        NATIVE_READER_MODULE,
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
            r"runtime_transitive_import_binding_mismatch:"
            r"xml_surface_reader\.security_guard"
        ),
    ):
        _content_source_role_resolver_module(ROOT)


@pytest.mark.parametrize("attribute", XML_SURFACE_READER_XML_COMMON_BINDINGS)
def test_every_xml_surface_reader_xml_common_capture_fails_closed_when_stale(
    monkeypatch,
    attribute,
):
    resolver = _content_source_role_resolver_module(ROOT)
    xml_common = sys.modules["xml_common"]
    assert getattr(resolver.xml_surface_reader, attribute) is getattr(xml_common, attribute)

    stale_capture = object()
    monkeypatch.setattr(resolver.xml_surface_reader, attribute, stale_capture)

    with pytest.raises(
        ValueError,
        match=(
            r"runtime_transitive_import_binding_mismatch:"
            + rf"xml_surface_reader\.{attribute}"
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

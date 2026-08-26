from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from . import native_reader
from .native_reader import *

_NATIVE_READER_IMPL = native_reader
_NATIVE_OOXML_MODULE = "hpfa.modules.core.xlsx_surface_reader_lite.src.native_ooxml"
_HEADER_SEMANTICS_MODULE = "hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_header_semantics"


def _resolved_module_file(module: Any) -> Path | None:
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return None
    return Path(module_file).expanduser().resolve(strict=False)


def _validated_helper_module(module_name: str, expected_file: Path, label: str) -> Any:
    module = sys.modules.get(module_name)
    if module is None:
        raise ValueError(f"runtime_transitive_module_missing:xlsx_surface_reader.{label}")
    if _resolved_module_file(module) != expected_file.resolve(strict=False):
        raise ValueError(f"runtime_module_origin_mismatch:xlsx_surface_reader.{label}")
    return module


def _validate_native_reader_helper_bindings() -> None:
    native_file = _resolved_module_file(_NATIVE_READER_IMPL)
    if native_file is None:
        raise ValueError("runtime_module_origin_mismatch:xlsx_surface_reader.native_reader")
    src_root = native_file.parents[1]

    native_ooxml = _validated_helper_module(
        _NATIVE_OOXML_MODULE,
        src_root / "native_ooxml.py",
        "native_ooxml",
    )
    for attribute in ("InvalidFileException", "load_workbook"):
        if getattr(_NATIVE_READER_IMPL, attribute, None) is not getattr(
            native_ooxml, attribute, None
        ):
            raise ValueError(
                "runtime_transitive_import_binding_mismatch:"
                f"xlsx_surface_reader.native_reader.{attribute}"
            )

    header_semantics = _validated_helper_module(
        _HEADER_SEMANTICS_MODULE,
        src_root / "xlsx_header_semantics.py",
        "xlsx_header_semantics",
    )
    if getattr(_NATIVE_READER_IMPL, "_semantic_header_norm", None) is not getattr(
        header_semantics, "semantic_header_norm", None
    ):
        raise ValueError(
            "runtime_transitive_import_binding_mismatch:"
            "xlsx_surface_reader.native_reader._semantic_header_norm"
        )


class _RuntimeGuardedXlsxSurfaceReaderModule(ModuleType):
    def __getattribute__(self, name: str) -> Any:
        if name == "native_reader":
            namespace = ModuleType.__getattribute__(self, "__dict__")
            current = namespace.get("native_reader")
            expected = namespace.get("_NATIVE_READER_IMPL")
            if current is expected:
                namespace["_validate_native_reader_helper_bindings"]()
            return current
        return ModuleType.__getattribute__(self, name)


sys.modules[__name__].__class__ = _RuntimeGuardedXlsxSurfaceReaderModule

__all__ = [name for name in dir(_NATIVE_READER_IMPL) if not name.startswith("_")]

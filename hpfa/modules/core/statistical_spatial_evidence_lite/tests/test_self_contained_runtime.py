from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]

RUNTIME_CHAIN_FILES = (
    "hpfa/modules/core/statistical_spatial_evidence_lite/src/statistical_spatial_evidence.py",
    "hpfa/modules/core/row_nucleus_content_role_bridge_lite/src/row_nucleus_content_role_bridge.py",
    "hpfa/modules/core/content_source_role_resolver_lite/src/content_source_role_resolver.py",
    "hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py",
    "hpfa/modules/core/triangulated_event_reflection_resolver_lite/src/triangulated_event_reflection_resolver.py",
    "hpfa/modules/core/csv_surface_reader_lite/src/csv_surface_reader.py",
    "hpfa/modules/core/xml_surface_reader_lite/src/xml_surface_reader.py",
    "hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader.py",
    "hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader/native_reader.py",
    "hpfa/modules/core/xlsx_surface_reader_lite/src/native_ooxml.py",
    "hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_header_semantics.py",
    "hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory.py",
    "hpfa/modules/core/active_match_spine_runner/src/spine_runner.py",
)

# These are HPFA-owned local modules that older spine modules load after adding
# their own repository subdirectory to sys.path. They are not third-party
# dependencies and are kept explicit so new dynamic local imports are reviewed.
LOCAL_DYNAMIC_IMPORTS = {
    "spine_runner",
    "surface_manifest",
    "boundary_analysis_scorer",
    "xml_common",
    "xml_rows",
    "xml_structure",
}

FORBIDDEN_NETWORK_MODULES = {
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "ftplib",
    "smtplib",
}

FORBIDDEN_NETWORK_IMPORTS = {
    "urllib.request",
    "http.client",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_statistical_runtime_chain_has_no_unadmitted_third_party_imports() -> None:
    stdlib = set(sys.stdlib_module_names)
    violations: dict[str, list[str]] = {}

    for relative in RUNTIME_CHAIN_FILES:
        path = REPO_ROOT / relative
        assert path.is_file(), f"runtime_chain_file_missing:{relative}"
        bad: list[str] = []
        for imported in sorted(_imports(path)):
            root = imported.split(".", 1)[0]
            if root == "hpfa" or root in stdlib or root in LOCAL_DYNAMIC_IMPORTS:
                continue
            bad.append(imported)
        if bad:
            violations[relative] = bad

    assert violations == {}, f"unadmitted_runtime_dependencies:{violations}"


def test_statistical_runtime_chain_has_no_network_import_surface() -> None:
    violations: dict[str, list[str]] = {}

    for relative in RUNTIME_CHAIN_FILES:
        path = REPO_ROOT / relative
        bad: list[str] = []
        for imported in sorted(_imports(path)):
            root = imported.split(".", 1)[0]
            if root in FORBIDDEN_NETWORK_MODULES or imported in FORBIDDEN_NETWORK_IMPORTS:
                bad.append(imported)
        if bad:
            violations[relative] = bad

    assert violations == {}, f"network_runtime_imports_forbidden:{violations}"


def test_scientific_runtime_policy_is_present() -> None:
    policy = REPO_ROOT / "docs/contracts/self_contained_runtime_dependency_policy_v1.md"
    registry = REPO_ROOT / "docs/research/eventonly/autonomous_scientific_capability_registry_v1.md"
    assert policy.is_file()
    assert registry.is_file()
    policy_text = policy.read_text(encoding="utf-8")
    assert "NO_NETWORK_RUNTIME" in policy_text
    assert "NO_DYNAMIC_CODE_FETCH" in policy_text
    assert "ADAPT_NOT_COPY" in policy_text

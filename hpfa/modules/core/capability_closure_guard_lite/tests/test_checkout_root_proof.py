import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "capability_closure_guard_lite" / "src"
sys.path.insert(0, str(SRC))

import capability_closure_guard as guard  # noqa: E402


MODULE_DIR = Path("hpfa/modules/core/sample_lite")


def _current_src(root: Path) -> Path:
    src = root / MODULE_DIR / "src"
    src.mkdir(parents=True, exist_ok=True)
    return src


def test_trusted_current_repo_root_exact_src_is_consumer_binding(tmp_path):
    _current_src(tmp_path)
    source_path = tmp_path / "consumer.py"
    text = (
        "ROOT = Path(__file__).resolve().parent\n"
        "src = ROOT / 'hpfa/modules/core/sample_lite/src'\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is True


def test_vendor_root_same_suffix_is_not_trusted_checkout_root(tmp_path):
    _current_src(tmp_path)
    vendor_root = tmp_path.parent / "vendor"
    foreign_src = vendor_root / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"vendor_root = Path({str(vendor_root)!r})\n"
        "src = validate_runtime_surface(vendor_root, vendor_root / 'hpfa/modules/core/sample_lite/src')\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is False


def test_nested_file_parent_cannot_impersonate_checkout_root(tmp_path):
    _current_src(tmp_path)
    source_path = tmp_path / "tools" / "consumer.py"
    source_path.parent.mkdir(parents=True)
    text = (
        "HERE = Path(__file__).resolve().parent\n"
        "src = HERE / 'hpfa/modules/core/sample_lite/src'\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is False


def test_actual_root_level_current_consumer_remains_bound():
    implementations = guard.discover_implementations(ROOT)
    consumers, _tests = guard.discover_consumers_and_tests(ROOT, implementations)

    assert "active_match_full_run.py" in consumers["active_match_spine_runner"]


def test_validate_runtime_surface_foreign_root_same_suffix_fails_closed(tmp_path):
    _current_src(tmp_path)
    foreign_root = tmp_path.parent / "foreign_checkout"
    (foreign_root / MODULE_DIR / "src").mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"foreign_root = Path({str(foreign_root)!r})\n"
        "src = validate_runtime_surface(foreign_root, foreign_root / 'hpfa/modules/core/sample_lite/src')\n"
        "_ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is False


def test_validate_runtime_surface_trusted_root_exact_src_passes(tmp_path):
    _current_src(tmp_path)
    source_path = tmp_path / "consumer.py"
    text = (
        "ROOT = Path(__file__).resolve().parent\n"
        "src = validate_runtime_surface(ROOT, ROOT / 'hpfa/modules/core/sample_lite/src')\n"
        "_ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is True


def test_symlink_escape_cannot_become_current_product_binding(tmp_path):
    _current_src(tmp_path)
    external_root = tmp_path.parent / "external_checkout"
    external_src = external_root / MODULE_DIR / "src"
    external_src.mkdir(parents=True, exist_ok=True)
    linked = tmp_path / "linked_src"
    linked.symlink_to(external_src, target_is_directory=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(linked)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is False


def test_reassigned_trusted_src_to_foreign_path_invalidates_binding(tmp_path):
    _current_src(tmp_path)
    foreign_root = tmp_path.parent / "vendor_reassigned"
    foreign_src = foreign_root / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        "ROOT = Path(__file__).resolve().parent\n"
        "src = ROOT / 'hpfa/modules/core/sample_lite/src'\n"
        f"src = Path({str(foreign_src)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text,
        MODULE_DIR,
        tmp_path,
        source_path=source_path,
    ) is False


def test_foreign_call_then_current_reassignment_stays_false(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "foreign_before_call" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(foreign_src)!r})\n"
        "ensure_module_path(src)\n"
        f"src = Path({str(current_src)!r})\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is False


def test_current_call_then_foreign_reassignment_stays_true(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "foreign_after_call" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        "ensure_module_path(src)\n"
        f"src = Path({str(foreign_src)!r})\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is True


def test_current_then_foreign_before_call_is_false(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "foreign_before_binding" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        f"src = Path({str(foreign_src)!r})\n"
        "_ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is False


def test_foreign_then_current_before_call_is_true_for_sys_path(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "foreign_then_current" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(foreign_src)!r})\n"
        f"src = Path({str(current_src)!r})\n"
        "sys.path.insert(0, str(src))\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is True

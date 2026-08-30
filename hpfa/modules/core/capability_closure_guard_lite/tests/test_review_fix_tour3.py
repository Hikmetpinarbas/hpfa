import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "capability_closure_guard_lite" / "src"
sys.path.insert(0, str(SRC))

import capability_closure_guard as guard  # noqa: E402


def test_planning_prefix_delimiter_family_is_exact():
    assert guard.normalize_capability_id("P2-Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("P2 – Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("P2/Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("P2: Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("P2 Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("p2h_event_time_space_lite") == "p2h_event_time_space_lite"
    assert guard.normalize_capability_id("p1_internal_surface") == "p1_internal_surface"


def test_bare_import_binding_requires_exact_current_checkout_src(tmp_path):
    module_dir = Path("hpfa/modules/core/sample_lite")
    current_src = tmp_path / module_dir / "src"
    current_src.mkdir(parents=True)

    current_text = (
        f"src = Path({str(current_src)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )
    assert guard._has_explicit_product_src_binding(current_text, module_dir, tmp_path) is True

    foreign_src = tmp_path.parent / "vendor" / module_dir / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    foreign_text = (
        f"src = Path({str(foreign_src)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )
    assert guard._has_explicit_product_src_binding(foreign_text, module_dir, tmp_path) is False

    external_target = tmp_path.parent / "external_sample_src"
    external_target.mkdir(parents=True, exist_ok=True)
    symlink_src = tmp_path / "linked_external_src"
    symlink_src.symlink_to(external_target, target_is_directory=True)
    symlink_text = (
        f"src = Path({str(symlink_src)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )
    assert guard._has_explicit_product_src_binding(symlink_text, module_dir, tmp_path) is False


def test_both_existing_module_path_helpers_share_exact_path_guard(tmp_path):
    module_dir = Path("hpfa/modules/core/sample_lite")
    current_src = tmp_path / module_dir / "src"
    current_src.mkdir(parents=True)

    for helper_name in ("ensure_module_path", "_ensure_module_path"):
        text = (
            f"src = Path({str(current_src)!r})\n"
            f"{helper_name}(src)\n"
            "import client\n"
        )
        assert guard._has_explicit_product_src_binding(text, module_dir, tmp_path) is True

    foreign_src = tmp_path.parent / "vendor_helper" / module_dir / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    foreign_text = (
        f"src = Path({str(foreign_src)!r})\n"
        "ensure_module_path(src)\n"
        "import client\n"
    )
    assert guard._has_explicit_product_src_binding(foreign_text, module_dir, tmp_path) is False

    implementations = guard.discover_implementations(ROOT)
    consumers, _tests = guard.discover_consumers_and_tests(ROOT, implementations)
    assert "active_match_full_run.py" in consumers["active_match_spine_runner"]

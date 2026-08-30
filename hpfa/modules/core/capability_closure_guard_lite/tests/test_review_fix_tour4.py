import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "capability_closure_guard_lite" / "src"
sys.path.insert(0, str(SRC))

import capability_closure_guard as guard  # noqa: E402


MODULE_DIR = Path("hpfa/modules/core/sample_lite")


def _current_src(root: Path) -> Path:
    src = root / MODULE_DIR / "src"
    src.mkdir(parents=True, exist_ok=True)
    return src


def test_nested_function_local_foreign_binding_does_not_inherit_outer_trust(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "nested_function_foreign" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        "def bind():\n"
        f"    src = Path({str(foreign_src)!r})\n"
        "    ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is False


def test_nested_class_local_foreign_binding_does_not_inherit_outer_trust(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "nested_class_foreign" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        "class Binder:\n"
        f"    src = Path({str(foreign_src)!r})\n"
        "    ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is False


def test_lambda_parameter_shadows_outer_trusted_binding(tmp_path):
    current_src = _current_src(tmp_path)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        "binder = lambda src: ensure_module_path(src)\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is False


def test_legitimate_outer_current_binding_remains_admitted(tmp_path):
    current_src = _current_src(tmp_path)
    source_path = tmp_path / "consumer.py"
    text = (
        f"src = Path({str(current_src)!r})\n"
        "ensure_module_path(src)\n"
        "def unrelated():\n"
        "    return None\n"
        "import client\n"
    )

    assert guard._has_explicit_product_src_binding(
        text, MODULE_DIR, tmp_path, source_path=source_path
    ) is True


def test_established_alphanumeric_planning_prefixes_reconcile_to_canonical_ids():
    assert guard.normalize_capability_id("P0B-G3 Football Time Foundation Lite V1") == "football_time_foundation_lite"
    assert guard.normalize_capability_id("P0B-G9 Active Match Identity Guard Lite V1") == "active_match_identity_guard_lite"
    assert guard.normalize_capability_id("P2D Event Physical Cost Surface Lite V1") == "event_physical_cost_surface_lite"
    assert guard.normalize_capability_id("P2-Canonical Event Lite V1") == "canonical_event_lite"
    assert guard.normalize_capability_id("p2h_event_time_space_lite") == "p2h_event_time_space_lite"
    assert guard.normalize_capability_id("p1_internal_surface") == "p1_internal_surface"


def test_machine_report_and_text_summary_emit_complete_claim_locks():
    report = guard.build_report(ROOT)
    for field in ("phase_truth", "possession_truth", "sequence_truth", "tactical_truth"):
        assert report[field] is False
    summary = guard.render_summary(report)
    for field in ("phase_truth", "possession_truth", "sequence_truth", "tactical_truth"):
        assert f"{field}=false" in summary


def test_active_match_evidence_cannot_promote_locked_claim_fields(tmp_path):
    base = {
        "evidence_kind": "ACTIVE_MATCH_RUNTIME_EVIDENCE",
        "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
        "product_tree_sha": "a" * 40,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    for field in ("phase_truth", "possession_truth", "sequence_truth", "tactical_truth"):
        payload = dict(base)
        payload[field] = True
        path = tmp_path / f"{field}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(guard.ClosureGuardError, match=f"active_match_evidence_{field}_promoted"):
            guard.load_active_match_evidence(path, "a" * 40)


def test_no_sample_match_identity_leak():
    source = (SRC / "capability_closure_guard.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in source


def test_compound_statement_rebinds_are_evaluated_before_helper_calls(tmp_path):
    current_src = _current_src(tmp_path)
    foreign_src = tmp_path.parent / "compound_foreign" / MODULE_DIR / "src"
    foreign_src.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "consumer.py"
    bodies = [
        "if True:\n    src = Path({foreign!r})\n    ensure_module_path(src)\n",
        "for _ in [1]:\n    src = Path({foreign!r})\n    ensure_module_path(src)\n",
        "try:\n    src = Path({foreign!r})\n    ensure_module_path(src)\nexcept Exception:\n    pass\n",
        "with open(__file__):\n    src = Path({foreign!r})\n    ensure_module_path(src)\n",
    ]
    for body in bodies:
        text = (
            f"src = Path({str(current_src)!r})\n"
            + body.format(foreign=str(foreign_src))
            + "import client\n"
        )
        assert guard._has_explicit_product_src_binding(
            text, MODULE_DIR, tmp_path, source_path=source_path
        ) is False


def test_foreign_qualified_entrypoint_import_cannot_seed_current_module(tmp_path):
    current_src = _current_src(tmp_path)
    (current_src / "client.py").write_text("def run(root):\n    return root\n", encoding="utf-8")
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent\n"
        f"src = Path({str(current_src)!r})\n"
        "ensure_module_path(src)\n"
        "from vendor.client import run\n"
        "run(root=ROOT)\n",
        encoding="utf-8",
    )
    implementations = guard.discover_implementations(tmp_path)
    seeds = guard._trusted_entrypoint_root_seeds(tmp_path, implementations)
    assert (current_src / "client.py").resolve() not in seeds


def test_exact_current_qualified_entrypoint_import_can_seed_current_module(tmp_path):
    current_src = _current_src(tmp_path)
    (current_src / "client.py").write_text("def run(root):\n    return root\n", encoding="utf-8")
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent\n"
        "from hpfa.modules.core.sample_lite.src.client import run\n"
        "run(root=ROOT)\n",
        encoding="utf-8",
    )
    implementations = guard.discover_implementations(tmp_path)
    seeds = guard._trusted_entrypoint_root_seeds(tmp_path, implementations)
    assert seeds[(current_src / "client.py").resolve()]["run"] == {"root"}

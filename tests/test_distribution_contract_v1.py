from __future__ import annotations

from pathlib import Path
import ast
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_distribution_package_discovers_hpfa_and_excludes_non_product_roots() -> None:
    config = _pyproject()
    find = config["tool"]["setuptools"]["packages"]["find"]
    assert {"hpfa", "hpfa.*", "canon", "canon.*"} <= set(find["include"])
    assert "hpfa*" not in find["include"]
    assert "canon*" not in find["include"]
    assert "vendor*" not in find["include"]
    assert "runtime*" not in find["include"]
    assert "out*" not in find["include"]
    assert "hpfa.modules.*.tests*" in find["exclude"]
    assert "hpfa-main*" in find["exclude"]
    assert "build*" in find["exclude"]


def test_core_has_no_mandatory_third_party_runtime_dependency() -> None:
    config = _pyproject()
    assert config["project"]["dependencies"] == []
    optional = config["project"]["optional-dependencies"]
    assert {"xls", "reference", "dev", "legacy-tools"} <= set(optional)


def test_distribution_is_private_until_release_governance_changes() -> None:
    config = _pyproject()
    assert "Private :: Do Not Upload" in config["project"]["classifiers"]
    assert (ROOT / "LICENSE").is_file()
    assert (ROOT / "THIRD_PARTY_NOTICES.md").is_file()
    assert (ROOT / "NOTICE").is_file()


def test_generated_runtime_and_out_roots_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/runtime/" in ignored
    assert "/out/" in ignored

def test_current_full_spine_compatibility_closure_is_packaged() -> None:
    config = _pyproject()
    modules = set(config["tool"]["setuptools"]["py-modules"])
    required = {
        "active_match_spine_runner",
        "active_match_full_run",
        "analyst_episode_locator",
        "axis_integrity_tagger",
        "context_action_semantics_rebind",
        "episode_feature_vector",
        "event_window_builder",
        "row_nucleus_inventory",
        "time_scale_router",
        "reconstruction_intelligence_packet_adapter_current_v1",
        "post_sequence_admission_finalizer_current_v1",
    }
    assert required <= modules
    assert config["project"]["scripts"]["hpfa-active-match"] == "active_match_spine_runner:main"
    for module in modules:
        assert (ROOT / f"{module}.py").is_file()


def test_declared_root_modules_cover_transitive_root_imports() -> None:
    config = _pyproject()
    declared = set(config["tool"]["setuptools"]["py-modules"])
    closure = set(declared)
    queue = list(declared)
    while queue:
        module = queue.pop()
        path = ROOT / f"{module}.py"
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in sys.stdlib_module_names or name == "hpfa":
                    continue
                if (ROOT / f"{name}.py").is_file() and name not in closure:
                    closure.add(name)
                    queue.append(name)
    assert closure == declared


def test_repository_root_does_not_keep_superseded_unowned_report_and_health_tools() -> None:
    forbidden = {
        "match_reading_export.py",
        "numeric_match_report.py",
        "repo_full_health_audit_v1.py",
    }
    present = {path.name for path in ROOT.iterdir() if path.is_file()}
    assert forbidden.isdisjoint(present)


def test_repository_does_not_keep_next_player_receiver_proxy_pass_network_tools() -> None:
    forbidden = {
        ROOT / "tools" / "hpfa_passnet_v1.py",
        ROOT / "tools" / "hpfa_passnet_105x68_v2.py",
    }
    assert not any(path.exists() for path in forbidden)


def test_full_repo_health_audit_is_maintained_tool_not_root_entrypoint() -> None:
    assert not (ROOT / "repo_full_health_audit_v1.py").exists()
    assert (ROOT / "tools" / "repo_full_health_audit_v1.py").is_file()
    fail_local = (ROOT / "repo_fail_local_product_test_audit_v1.py").read_text(encoding="utf-8")
    assert '"tools/repo_full_health_audit_v1.py"' in fail_local

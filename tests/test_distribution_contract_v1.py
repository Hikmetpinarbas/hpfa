from __future__ import annotations

from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_distribution_package_discovers_hpfa_and_excludes_non_product_roots() -> None:
    config = _pyproject()
    find = config["tool"]["setuptools"]["packages"]["find"]
    assert "hpfa*" in find["include"]
    assert "canon*" in find["include"]
    assert "vendor*" not in find["include"]
    assert "runtime*" not in find["include"]
    assert "out*" not in find["include"]
    assert "hpfa.modules.*.tests*" in find["exclude"]


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
    }
    assert required <= modules
    assert config["project"]["scripts"]["hpfa-active-match"] == "active_match_spine_runner:main"
    for module in modules:
        assert (ROOT / f"{module}.py").is_file()

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[str]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item for item in raw.decode("utf-8", "surrogateescape").split("\0") if item]


def test_product_tree_excludes_runtime_history_and_nested_legacy_assets() -> None:
    tracked = _tracked_files()
    forbidden_prefixes = (
        "out/",
        "_out/",
        "_diag/",
        "data/matches/",
        "data/quarantine/",
        "data/keepbox/",
        "data_inbox/",
        "runtime_evidence/",
        "graphics_pack/",
        "vendor/",
        "hpfa-main/",
    )
    hits = [path for path in tracked if path.startswith(forbidden_prefixes)]
    assert hits == []


def test_product_tree_excludes_backup_compiled_and_generated_binary_files() -> None:
    tracked = _tracked_files()
    forbidden_suffixes = (
        ".pyc",
        ".bak",
        ".err",
        ".xlsx",
        ".xls",
        ".png",
        ".zip",
    )
    hits = [path for path in tracked if path.lower().endswith(forbidden_suffixes)]
    assert hits == []


def test_product_code_has_no_real_match_or_team_identity_hardcoding() -> None:
    tracked = _tracked_files()
    source_paths = []
    for path in tracked:
        p = Path(path)
        if "/tests/" in f"/{path}/":
            continue
        if path.startswith(("hpfa/", "tools/", "bin/", "configs/", "canon/")) or (
            len(p.parts) == 1 and p.suffix in {".py", ".sh"}
        ):
            source_paths.append(path)

    forbidden = (
        "rz-gs-20260208",
        "caykur rizespor",
        "rizespor",
        "galatasaray",
        "fenerbahce",
        "fenerbahçe",
        "trabzonspor",
        "juventus",
        "basaksehir",
        "başakşehir",
        "genclerbirligi",
        "gençlerbirliği",
    )

    hits: list[str] = []
    for path in source_paths:
        p = ROOT / path
        try:
            text = p.read_text(encoding="utf-8").casefold()
        except (UnicodeDecodeError, OSError):
            continue
        if any(token.casefold() in text for token in forbidden):
            hits.append(path)

    assert hits == []


def test_product_code_has_no_named_ai_authority_trace() -> None:
    tracked = _tracked_files()
    source_paths = []
    for path in tracked:
        if "/tests/" in f"/{path}/":
            continue
        if path.startswith(("hpfa/", "tools/", "bin/", "configs/", "canon/")) or (
            "/" not in path and Path(path).suffix in {".py", ".sh"}
        ):
            source_paths.append(path)

    forbidden = (
        "chatgpt",
        "claude opus",
        "gemini",
        "grok",
        "manus",
        "qwen",
        "kimi",
        "microsoft copilot",
    )

    hits: list[str] = []
    for path in source_paths:
        p = ROOT / path
        try:
            text = p.read_text(encoding="utf-8").casefold()
        except (UnicodeDecodeError, OSError):
            continue
        if any(token in text for token in forbidden):
            hits.append(path)

    assert hits == []


def test_termux_bootstraps_are_branch_and_head_parameterized() -> None:
    bootstraps = sorted((ROOT / "tools").glob("bootstrap_termux_*.sh"))
    assert bootstraps, "no_termux_bootstraps_found"

    violations: list[str] = []
    for path in bootstraps:
        text = path.read_text(encoding="utf-8")
        if 'BRANCH="${HPFA_EXPECTED_BRANCH:-}"' not in text:
            violations.append(f"{path.name}:branch_not_parameterized")
        if "HPFA_EXPECTED_HEAD" not in text:
            violations.append(f"{path.name}:expected_head_missing")
        if "reset --hard" in text:
            violations.append(f"{path.name}:destructive_reset_present")

    assert violations == []


def test_history_and_operator_checkpoint_directories_do_not_return() -> None:
    tracked = _tracked_files()
    forbidden_prefixes = (
        "docs/project_knowledge_base/",
        "docs/logbook/",
        "docs/project_log/",
        "docs/prompts/",
        "docs/runtime/",
    )
    hits = [path for path in tracked if path.startswith(forbidden_prefixes)]
    assert hits == []


def test_historical_snapshot_workflow_names_do_not_return() -> None:
    tracked = _tracked_files()
    hits = [
        path
        for path in tracked
        if path.startswith(".github/workflows/")
        and "final-snapshot" in path
    ]
    assert hits == []


def test_runtime_tools_do_not_embed_historical_branch_names() -> None:
    tracked = _tracked_files()
    tool_paths = [
        ROOT / path
        for path in tracked
        if path.startswith("tools/") and path.endswith((".sh", ".py"))
    ]
    forbidden = (
        "foundation-tranche-a-v1",
        "rz-gs-20260208",
    )
    hits: list[str] = []
    for path in tool_paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in forbidden):
            hits.append(path.name)
    assert hits == []


def test_runtime_tools_do_not_use_destructive_git_reset() -> None:
    tracked = _tracked_files()
    tool_paths = [
        ROOT / path
        for path in tracked
        if path.startswith("tools/") and path.endswith((".sh", ".py"))
    ]
    hits = [
        path.name
        for path in tool_paths
        if "reset --hard" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert hits == []


def test_bin_entrypoints_reference_existing_hpfa_modules() -> None:
    import ast
    import importlib.util

    violations: list[str] = []
    for path in sorted((ROOT / "bin").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("hpfa."):
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("hpfa."):
                        modules.add(alias.name)
        for module in sorted(modules):
            if importlib.util.find_spec(module) is None:
                violations.append(f"{path.name}:{module}")

    assert violations == []

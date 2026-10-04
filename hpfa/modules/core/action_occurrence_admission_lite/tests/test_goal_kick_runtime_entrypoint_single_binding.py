from __future__ import annotations

import ast
from pathlib import Path


def test_current_runtime_binds_goal_kick_only_through_public_action_grammar_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    entrypoint = repo_root / "action_occurrence_admission_current_v1.py"
    source = entrypoint.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    called_names = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert "bind_goal_kick_restart_pass_grammar" not in imported_names
    assert "bind_goal_kick_restart_pass_grammar" not in called_names
    assert called_names.count("bind_intra_actor_action_grammar") == 1

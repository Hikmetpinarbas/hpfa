from __future__ import annotations

from pathlib import Path

from spine_runner import (
    ACTIVE_MATCH_RELATIVE_PATH,
    _absolute_lexical_path,
    _authority_symlink_component,
    _forbidden_authority_ancestry_token,
    _resolve_path,
    _validate_resolved_authority_containment,
)


def validate_split_active_match_authority(
    path: str | Path,
    runtime_authority_root: str | Path,
) -> Path:
    """Validate ACTIVE_MATCH against an explicit runtime authority root.

    Product code and runtime authority are intentionally allowed to live in
    separate roots. This function preserves the existing path, ancestry,
    symlink and containment protections while binding ACTIVE_MATCH to the
    declared runtime authority root instead of the product checkout root.
    """
    selected_runtime_root = _resolve_path(Path(runtime_authority_root))
    lexical_candidate = _absolute_lexical_path(Path(path))
    lexical_expected = selected_runtime_root / ACTIVE_MATCH_RELATIVE_PATH

    if tuple(lexical_candidate.parts[-3:]) != tuple(ACTIVE_MATCH_RELATIVE_PATH.parts):
        raise ValueError(f"runtime_authority_path_invalid:{lexical_candidate}")

    forbidden_token = _forbidden_authority_ancestry_token(lexical_candidate)
    if forbidden_token is not None:
        raise ValueError(
            f"runtime_authority_forbidden_ancestry:{forbidden_token}:{lexical_candidate}"
        )

    if lexical_candidate != lexical_expected:
        raise ValueError(
            "runtime_authority_root_binding_mismatch:"
            f"{lexical_candidate}:expected:{lexical_expected}"
        )

    symlink_component = _authority_symlink_component(selected_runtime_root)
    if symlink_component is not None:
        raise ValueError(f"runtime_authority_symlink_rejected:{symlink_component}")

    resolved = _resolve_path(lexical_candidate)
    resolved_forbidden_token = _forbidden_authority_ancestry_token(resolved)
    if resolved_forbidden_token is not None:
        raise ValueError(
            "runtime_authority_forbidden_ancestry:"
            f"{resolved_forbidden_token}:{resolved}"
        )

    _validate_resolved_authority_containment(resolved, selected_runtime_root)
    return resolved

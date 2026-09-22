from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.capability_closure_guard_lite.src.capability_closure_guard import (
    load_governance_seed,
    normalize_capability_id,
)

MODULE_ID = "active_match_capability_coverage_lite_v1"
OUTPUT_JSON = "HPFA_ACTIVE_MATCH_CAPABILITY_COVERAGE.json"
OUTPUT_TXT = "HPFA_ACTIVE_MATCH_CAPABILITY_COVERAGE.txt"

CONTROL_ONLY_FAMILIES = {
    "active_match_spine_runner",
    "capability_closure_guard_lite",
    "core_pipeline_orchestrator_lite",
    "metric_definition_policy_lite",
    "metric_governance_lite",
}

ARTIFACT_FAMILY_HINTS = {
    "g01_g18_data_quality_rollup_v1.json": "data_quality_gate",
    "g01_g18_data_quality_rollup_v1.txt": "data_quality_gate",
}

NON_CURRENT_HINT_TOKENS = ("SUPERSEDED", "HISTORICAL")
WAIT_HINT_TOKENS = (
    "INTENTIONAL_WAIT",
    "SPEC_ONLY",
    "WAITING",
    "EXECUTION_PENDING",
    "NEXT_PRODUCT_NODE",
    "READINESS",
)


def _module_dirs(root: Path) -> list[tuple[str, str, Path]]:
    modules = root / "hpfa" / "modules"
    result: list[tuple[str, str, Path]] = []
    if not modules.is_dir():
        return result
    for group in sorted(path for path in modules.iterdir() if path.is_dir()):
        for module_dir in sorted(path for path in group.iterdir() if path.is_dir()):
            result.append((group.name, normalize_capability_id(module_dir.name), module_dir))
    return result


def _declared_module_ids(module_dir: Path) -> set[str]:
    values: set[str] = set()
    src = module_dir / "src"
    if not src.is_dir():
        return values
    for path in src.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            target = None
            value = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            elif isinstance(node, ast.AnnAssign):
                target, value = node.target, node.value
            if (
                isinstance(target, ast.Name)
                and target.id == "MODULE_ID"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                values.add(str(value.value))
    return values


def _collect_module_ids(value: Any, result: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "module_id" and isinstance(item, str) and item.strip():
                result.add(item.strip())
            _collect_module_ids(item, result)
    elif isinstance(value, list):
        for item in value:
            _collect_module_ids(item, result)


def _current_json_artifacts(output: Path, full_spine_result: dict[str, Any]) -> list[Path]:
    values = full_spine_result.get("current_invocation_artifacts")
    values = values if isinstance(values, list) else []
    result: list[Path] = []
    seen: set[str] = set()
    for raw in values:
        candidate = Path(str(raw)).expanduser().resolve(strict=False)
        if candidate.parent != output or candidate.suffix.casefold() != ".json" or not candidate.is_file():
            continue
        if candidate.name in seen:
            continue
        seen.add(candidate.name)
        result.append(candidate)
    return sorted(result, key=lambda item: item.name.casefold())


def _observed_execution_evidence(
    output: Path,
    full_spine_result: dict[str, Any],
) -> tuple[set[str], dict[str, list[str]]]:
    observed_ids: set[str] = set()
    _collect_module_ids(full_spine_result, observed_ids)
    by_artifact: dict[str, list[str]] = {}
    for path in _current_json_artifacts(output, full_spine_result):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        local: set[str] = set()
        _collect_module_ids(payload, local)
        observed_ids.update(local)
        if local:
            by_artifact[path.name] = sorted(local)
    for name, family in ARTIFACT_FAMILY_HINTS.items():
        if (output / name).is_file():
            by_artifact.setdefault(name, []).append(f"family_hint:{family}")
    return observed_ids, by_artifact


def _classify_unproven(group: str, governance_hint: str, declared_ids: set[str]) -> tuple[str, str]:
    hint = governance_hint.upper()
    if any(token in hint for token in NON_CURRENT_HINT_TOKENS):
        return "SUPERSEDED_NOT_CURRENT", "governance_hint_marks_non_current"
    if any(token in hint for token in WAIT_HINT_TOKENS):
        return "INTENTIONAL_WAIT_CLAIM_GATE", "governance_hint_marks_wait_or_spec_state"
    if group == "support":
        return "SUPPORT_ONLY_NOT_EVENT_TRUTH", "support_module_not_proven_in_current_event_run"
    if not declared_ids:
        return "NOT_EVIDENCED_REQUIRES_REVIEW", "module_has_no_declared_runtime_module_id"
    return "UNWIRED_CURRENT_CAPABILITY", "no_current_invocation_execution_evidence"


def build_active_match_capability_coverage(
    *,
    product_root: str | Path,
    output_root: str | Path,
    full_spine_result: dict[str, Any],
) -> dict[str, Any]:
    root = Path(product_root).expanduser().resolve(strict=False)
    output = Path(output_root).expanduser().resolve(strict=False)
    governance = load_governance_seed(root)
    observed_ids, by_artifact = _observed_execution_evidence(output, full_spine_result)
    normalized_observed = {normalize_capability_id(value): value for value in observed_ids}

    records: list[dict[str, Any]] = []
    for group, family, module_dir in _module_dirs(root):
        declared_ids = _declared_module_ids(module_dir)
        normalized_declared = {normalize_capability_id(value) for value in declared_ids}
        matched_ids = sorted(
            observed
            for normalized, observed in normalized_observed.items()
            if normalized in normalized_declared
        )
        hinted_artifacts = sorted(
            name
            for name, values in by_artifact.items()
            if any(value == f"family_hint:{family}" for value in values)
        )
        proven = bool(matched_ids or hinted_artifacts)
        governance_hint = str((governance.get(family) or {}).get("current_status_hint") or "")

        if proven:
            if family in CONTROL_ONLY_FAMILIES:
                state = "EXECUTED_CONTROL_ONLY"
                reason = "current_invocation_execution_evidence_control_or_governance"
                contributes = False
            else:
                state = "EXECUTED_CONTRIBUTED"
                reason = "current_invocation_execution_evidence"
                contributes = True
        else:
            state, reason = _classify_unproven(group, governance_hint, declared_ids)
            contributes = False

        records.append({
            "capability_family": family,
            "module_group": group,
            "module_dir": module_dir.relative_to(root).as_posix(),
            "declared_module_ids": sorted(declared_ids),
            "observed_module_ids": matched_ids,
            "artifact_family_hints": hinted_artifacts,
            "coverage_state": state,
            "analysis_contribution": contributes,
            "reason": reason,
            "governance_status_hint": governance_hint or None,
        })

    state_counts = Counter(record["coverage_state"] for record in records)
    review_states = {"UNWIRED_CURRENT_CAPABILITY", "NOT_EVIDENCED_REQUIRES_REVIEW"}
    review_records = [
        record["capability_family"]
        for record in records
        if record["coverage_state"] in review_states
    ]
    status = "REVIEW_REQUIRED" if review_records else "SMOKE_PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "CAPABILITY_COVERAGE_REVIEW_REQUIRED" if review_records else "CAPABILITY_COVERAGE_COMPLETE",
        "coverage_scope": "ALL_TOP_LEVEL_HPFA_MODULE_FAMILIES",
        "coverage_semantics": (
            "PRODUCER_EVIDENCE_COVERAGE_ONLY; module existence is not runtime proof; "
            "non-execution must have an explicit state"
        ),
        "module_family_count": len(records),
        "proven_execution_family_count": sum(
            1 for record in records if record["coverage_state"].startswith("EXECUTED_")
        ),
        "analysis_contributing_family_count": sum(
            1 for record in records if record["analysis_contribution"] is True
        ),
        "control_only_executed_family_count": sum(
            1 for record in records if record["coverage_state"] == "EXECUTED_CONTROL_ONLY"
        ),
        "unwired_or_not_evidenced_family_count": len(review_records),
        "state_counts": dict(sorted(state_counts.items())),
        "unwired_or_not_evidenced_families": sorted(review_records),
        "observed_runtime_module_id_count": len(observed_ids),
        "observed_runtime_module_ids": sorted(observed_ids),
        "capabilities": records,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "production_release": False,
    }


def write_active_match_capability_coverage(
    *,
    product_root: str | Path,
    output_root: str | Path,
    full_spine_result: dict[str, Any],
) -> dict[str, Any]:
    output = Path(output_root).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    payload = build_active_match_capability_coverage(
        product_root=product_root,
        output_root=output,
        full_spine_result=full_spine_result,
    )
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "HPFA ACTIVE_MATCH CAPABILITY COVERAGE V1",
        "========================================",
        f"status={payload['status']}",
        f"module_family_count={payload['module_family_count']}",
        f"proven_execution_family_count={payload['proven_execution_family_count']}",
        f"analysis_contributing_family_count={payload['analysis_contributing_family_count']}",
        f"control_only_executed_family_count={payload['control_only_executed_family_count']}",
        f"unwired_or_not_evidenced_family_count={payload['unwired_or_not_evidenced_family_count']}",
        f"state_counts={json.dumps(payload['state_counts'], ensure_ascii=False, sort_keys=True)}",
        "",
        "UNWIRED_OR_NOT_EVIDENCED",
    ]
    lines.extend(f"- {value}" for value in payload["unwired_or_not_evidenced_families"])
    lines.extend([
        "",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "possession_truth=false",
        "sequence_truth=false",
        "tactical_truth=false",
        "production_release=false",
        "",
    ])
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    payload["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return payload

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_metric_governance_prerequisite_chain_v1"

STEP_OUTPUTS = {
    "inventory": "multiformat_file_inventory_lite_v1.json",
    "csv": "csv_surface_audit_lite_v1.json",
    "xlsx": "xlsx_surface_audit_lite_v1.json",
    "xml": "xml_surface_audit_lite_v1.json",
    "field_semantics": "provider_alias_field_semantics_lite_v1.json",
    "label_semantics": "provider_label_value_semantics_lite_v1.json",
    "reconciliation": "cross_format_reconciliation_lite_v1.json",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _run(root: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "passed": completed.returncode == 0,
    }


def run_metric_governance_prerequisite_chain(
    active_match_dir: str | Path,
    out_dir: str | Path,
    product_root: str | Path,
) -> dict[str, Any]:
    active = Path(active_match_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    root = Path(product_root).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)

    registry = root / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "registry" / "sportsbase_label_semantics_seed_v1.json"
    xml_group_registry = root / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "registry" / "sportsbase_xml_group_semantics_v1.json"

    commands = [
        ("inventory", [sys.executable, str(root / "multiformat_file_inventory.py"), "--input-root", str(active), "--runtime-authority", str(active), "--active-match-execution", "--out", str(output)]),
        ("csv", [sys.executable, str(root / "csv_surface_reader_lite.py"), "--input-root", str(active), "--inventory", str(output / STEP_OUTPUTS["inventory"]), "--out", str(output)]),
        ("xlsx", [sys.executable, str(root / "xlsx_surface_reader_lite.py"), "--input-root", str(active), "--inventory", str(output / STEP_OUTPUTS["inventory"]), "--out", str(output)]),
        ("xml", [sys.executable, str(root / "xml_surface_reader_lite.py"), "--input-root", str(active), "--inventory", str(output / STEP_OUTPUTS["inventory"]), "--out", str(output)]),
        ("field_semantics", [sys.executable, str(root / "provider_alias_field_semantics_lite.py"), "--input-root", str(active), "--csv-audit", str(output / STEP_OUTPUTS["csv"]), "--xlsx-audit", str(output / STEP_OUTPUTS["xlsx"]), "--xml-audit", str(output / STEP_OUTPUTS["xml"]), "--out", str(output)]),
        ("label_semantics", [sys.executable, str(root / "provider_label_value_semantics_lite.py"), "--runtime-authority", str(active), "--expected-runtime-authority", str(active), "--csv-audit", str(output / STEP_OUTPUTS["csv"]), "--xlsx-audit", str(output / STEP_OUTPUTS["xlsx"]), "--xml-audit", str(output / STEP_OUTPUTS["xml"]), "--field-semantics", str(output / STEP_OUTPUTS["field_semantics"]), "--registry", str(registry), "--out", str(output)]),
        ("reconciliation", [sys.executable, str(root / "cross_format_reconciliation_lite.py"), "--input-root", str(active), "--expected-runtime-authority", str(active), "--inventory", str(output / STEP_OUTPUTS["inventory"]), "--csv-audit", str(output / STEP_OUTPUTS["csv"]), "--xlsx-audit", str(output / STEP_OUTPUTS["xlsx"]), "--xml-audit", str(output / STEP_OUTPUTS["xml"]), "--field-semantics", str(output / STEP_OUTPUTS["field_semantics"]), "--label-semantics", str(output / STEP_OUTPUTS["label_semantics"]), "--xml-group-registry", str(xml_group_registry), "--out", str(output)]),
    ]

    steps: list[dict[str, Any]] = []
    hard_blocks: list[str] = []
    review_hits: list[str] = []
    artifacts: list[str] = []

    for name, command in commands:
        step = _run(root, command)
        step["name"] = name
        steps.append(step)
        if not step["passed"]:
            hard_blocks.append(f"metric_governance_prerequisite_step_failed:{name}")
            break
        artifact = output / STEP_OUTPUTS[name]
        if not artifact.is_file():
            hard_blocks.append(f"metric_governance_prerequisite_output_missing:{name}")
            break
        artifacts.append(str(artifact))
        payload = _load_json(artifact)
        status = str(payload.get("status") or payload.get("module_status") or "UNKNOWN").upper()
        step["artifact_status"] = status
        if status == "FAIL_CLOSED":
            hard_blocks.append(f"metric_governance_prerequisite_fail_closed:{name}")
            break
        if status in {"REVIEW_REQUIRED", "UNKNOWN"}:
            review_hits.append(f"metric_governance_prerequisite_review_required:{name}")

    required_ready = all((output / STEP_OUTPUTS[name]).is_file() for name in ("xlsx", "label_semantics", "reconciliation"))
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "SMOKE_PASS"),
        "required_governance_inputs_ready": required_ready,
        "steps": steps,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "current_invocation_artifacts": artifacts,
        "same_provider_multiformat_is_independent_support": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

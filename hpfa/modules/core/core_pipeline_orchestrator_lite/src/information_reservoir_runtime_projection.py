from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "information_reservoir_runtime_projection_v1"
OUTPUT_JSON = "information_reservoir_runtime_projection_v1.json"
MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "registry"
    / "information_reservoir_manifest_v1.json"
)

STRICT_EXACT_CEILING_OWNERS = {
    "evidence_atom_inventory_lite_v1",
    "context_action_semantics_rebind_lite_v1",
    "analyst_episode_locator_lite_v1",
    "episode_feature_vector_lite_v1",
    "temporal_episode_signature_lite_v1",
    "multi_signal_evidence_fusion_lite_v1",
    "analyst_report_block_composer_lite_v1",
    "report_output_contract_lite_v1",
    "final_report_assembly_gate_lite_v1",
    "rich_multiformat_analysis_lattice_v1",
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path.name}")
    return payload


def _fingerprint(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in manifest.get("artifacts") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("artifact_name") or "").strip()
        if name:
            rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("artifact_name") or ""),
            str(row.get("object_path") or ""),
            str(row.get("stage_id") or ""),
        ),
    )


def _object_at_path(payload: dict[str, Any], object_path: str) -> tuple[Any, bool]:
    if not object_path:
        return payload, True
    current: Any = payload
    for part in object_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def _value_fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def project_information_reservoir(
    output_dir: str | Path,
    *,
    current_invocation_artifacts: Iterable[str] | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(output_dir).expanduser().resolve(strict=False)
    manifest_file = Path(manifest_path) if manifest_path else MANIFEST_PATH
    manifest = _load_object(manifest_file)
    rows = _manifest_rows(manifest)

    declared_current = {
        Path(str(value)).name
        for value in (current_invocation_artifacts or [])
        if str(value or "").strip()
    }
    if current_invocation_artifacts is None:
        declared_current = {
            path.name for path in root.glob("*.json") if path.is_file()
        }

    records: list[dict[str, Any]] = []
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    for row in rows:
        artifact_name = str(row.get("artifact_name") or "").strip()
        object_path = str(row.get("object_path") or "").strip()
        path = root / artifact_name
        present = path.is_file()
        current = artifact_name in declared_current
        payload: dict[str, Any] = {}
        read_error = ""
        if present:
            try:
                payload = _load_object(path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                read_error = type(exc).__name__
                if current:
                    hard_blocks.append(f"current_manifest_artifact_unreadable:{artifact_name}")

        target: Any = payload
        object_present = bool(payload)
        if payload and object_path:
            target, object_present = _object_at_path(payload, object_path)
        if (
            current
            and row.get("required_when_artifact_current") is True
            and not object_present
        ):
            hard_blocks.append(
                f"manifest_required_object_missing:{artifact_name}:{object_path}"
            )

        expected_owner = str(row.get("owner_id") or "")
        observed_module = str(payload.get("module_id") or "") if payload else ""
        owner_match_state = (
            "MATCH"
            if observed_module and observed_module == expected_owner
            else "NOT_DECLARED"
            if not observed_module
            else "MISMATCH"
        )
        if current and owner_match_state == "MISMATCH":
            review_hits.append(f"manifest_owner_mismatch:{artifact_name}")

        expected_ceiling = str(row.get("claim_ceiling") or "")
        observed_ceiling = (
            str(target.get("claim_ceiling") or "")
            if isinstance(target, dict)
            else ""
        )
        if not present or not observed_ceiling:
            ceiling_match_state = "NOT_DECLARED"
        elif observed_ceiling == expected_ceiling:
            ceiling_match_state = "MATCH"
        else:
            ceiling_match_state = "MISMATCH"

        if (
            current
            and expected_owner in STRICT_EXACT_CEILING_OWNERS
            and ceiling_match_state == "MISMATCH"
        ):
            hard_blocks.append(f"manifest_claim_ceiling_mismatch:{artifact_name}")

        records.append(
            {
                "artifact_name": artifact_name,
                "object_path": object_path or None,
                "binding_id": f"{artifact_name}#{object_path or '                "owner_id": expected_owner,
                "epistemic_type": row.get("epistemic_type"),
                "expected_claim_ceiling": expected_ceiling or None,
                "allowed_downstream_stage_classes": list(
                    row.get("allowed_downstream_stage_classes") or []
                ),
                "present_in_output_root": present,
                "object_present": object_present,
                "declared_current_invocation": current,
                "source_fingerprint": _fingerprint(path) if present and not read_error else None,
                "object_fingerprint": (
                    _value_fingerprint(target)
                    if object_present and target is not None and not read_error
                    else None
                ),
                "observed_module_id": observed_module or None,
                "owner_match_state": owner_match_state,
                "observed_claim_ceiling": observed_ceiling or None,
                "claim_ceiling_match_state": ceiling_match_state,
                "source_status": payload.get("status") if payload else None,
                "read_error": read_error or None,
            }
        )

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    if hard_blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_INFORMATION_RESERVOIR_PROJECTION"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "INFORMATION_RESERVOIR_PROJECTION_REVIEW_REQUIRED"
    else:
        status = "PASS"
        decision = "INFORMATION_RESERVOIR_PROJECTION_BUILT"

    return {
        "module_id": MODULE_ID,
        "manifest_id": manifest.get("manifest_id"),
        "status": status,
        "decision": decision,
        "artifact_binding_count": len(records),
        "present_artifact_count": sum(row["present_in_output_root"] for row in records),
        "current_invocation_binding_count": sum(
            row["declared_current_invocation"] for row in records
        ),
        "records": records,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "pool_membership_creates_new_evidence": False,
        "final_tank_can_strengthen_claim_ceiling": False,
        "report_text_is_evidence": False,
        "visualization_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_information_reservoir_projection(
    output_dir: str | Path,
    *,
    current_invocation_artifacts: Iterable[str] | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    report = project_information_reservoir(
        root,
        current_invocation_artifacts=current_invocation_artifacts,
        manifest_path=manifest_path,
    )
    (root / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
}",
                "stage_id": row.get("stage_id"),
                "owner_id": expected_owner,
                "epistemic_type": row.get("epistemic_type"),
                "expected_claim_ceiling": expected_ceiling or None,
                "allowed_downstream_stage_classes": list(
                    row.get("allowed_downstream_stage_classes") or []
                ),
                "present_in_output_root": present,
                "declared_current_invocation": current,
                "source_fingerprint": _fingerprint(path) if present and not read_error else None,
                "observed_module_id": observed_module or None,
                "owner_match_state": owner_match_state,
                "observed_claim_ceiling": observed_ceiling or None,
                "claim_ceiling_match_state": ceiling_match_state,
                "source_status": payload.get("status") if payload else None,
                "read_error": read_error or None,
            }
        )

    hard_blocks = sorted(set(hard_blocks))
    review_hits = sorted(set(review_hits))
    if hard_blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_INFORMATION_RESERVOIR_PROJECTION"
    elif review_hits:
        status = "REVIEW_REQUIRED"
        decision = "INFORMATION_RESERVOIR_PROJECTION_REVIEW_REQUIRED"
    else:
        status = "PASS"
        decision = "INFORMATION_RESERVOIR_PROJECTION_BUILT"

    return {
        "module_id": MODULE_ID,
        "manifest_id": manifest.get("manifest_id"),
        "status": status,
        "decision": decision,
        "artifact_binding_count": len(records),
        "present_artifact_count": sum(row["present_in_output_root"] for row in records),
        "current_invocation_binding_count": sum(
            row["declared_current_invocation"] for row in records
        ),
        "records": records,
        "hard_block_hits": hard_blocks,
        "review_hits": review_hits,
        "pool_membership_creates_new_evidence": False,
        "final_tank_can_strengthen_claim_ceiling": False,
        "report_text_is_evidence": False,
        "visualization_is_evidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_information_reservoir_projection(
    output_dir: str | Path,
    *,
    current_invocation_artifacts: Iterable[str] | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    report = project_information_reservoir(
        root,
        current_invocation_artifacts=current_invocation_artifacts,
        manifest_path=manifest_path,
    )
    (root / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report

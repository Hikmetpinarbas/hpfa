#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ACTIVE_MATCH_PASS = "ACTIVE_MATCH_EVIDENCE_PASS"
ACTIVE_MATCH_REVIEW = "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
ACTIVE_MATCH_NOT_COMPLETED = "ACTIVE_MATCH_EXECUTION_NOT_COMPLETED"


def load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(code) from exc
    if not isinstance(payload, dict):
        raise SystemExit(code)
    return payload


def gate_record(rollup: dict[str, Any], gate_id: str) -> dict[str, Any] | None:
    candidates: list[Any] = []
    if isinstance(rollup.get("gates"), list):
        candidates.extend(rollup["gates"])
    nested = rollup.get("g01_g18_rollup")
    if isinstance(nested, dict) and isinstance(nested.get("gates"), list):
        candidates.extend(nested["gates"])
    for row in candidates:
        if isinstance(row, dict) and row.get("gate_id") == gate_id:
            return row
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attach exact-head ACTIVE_MATCH provenance to Coordinate Frame Precondition Lite V1 output."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime-authority", required=True)
    parser.add_argument("--expected-runtime-authority", required=True)
    parser.add_argument("--runtime-head", required=True)
    parser.add_argument("--run-rc", required=True, type=int)
    parser.add_argument("--rollup", required=True)
    parser.add_argument("--aggregate-alignment", required=True)
    parser.add_argument("--dependency-audit-out", required=True)
    args = parser.parse_args()

    output_path = Path(args.output)
    rollup_path = Path(args.rollup)
    aggregate_path = Path(args.aggregate_alignment)
    dependency_out = Path(args.dependency_audit_out)

    payload = load_object(output_path, "coordinate_frame_output_invalid")
    rollup = load_object(rollup_path, "g01_g18_rollup_invalid")
    aggregate = load_object(aggregate_path, "aggregate_definition_alignment_invalid")

    hard_blocks = payload.get("hard_block_hits") or []
    if not isinstance(hard_blocks, list):
        raise SystemExit("coordinate_frame_hard_block_inventory_invalid")

    module_status = payload.get("module_status") or payload.get("status")
    authority_equal = args.runtime_authority == args.expected_runtime_authority
    execution_completed = (
        args.run_rc in {0, 1}
        and authority_equal
        and not hard_blocks
    )
    active_match_evidence_pass = (
        execution_completed
        and module_status == "PASS"
        and payload.get("progression_metric_recheck_allowed") is True
    )

    payload["runtime_authority"] = args.runtime_authority
    payload["runtime_authority_equal"] = authority_equal
    payload["runtime_code_head_sha"] = args.runtime_head
    payload["run_rc"] = args.run_rc
    payload["active_match_execution_completed"] = execution_completed
    payload["active_match_evidence_pass"] = active_match_evidence_pass
    payload["runtime_evidence_status"] = (
        ACTIVE_MATCH_PASS
        if active_match_evidence_pass
        else ACTIVE_MATCH_REVIEW
        if execution_completed
        else ACTIVE_MATCH_NOT_COMPLETED
    )
    payload["release_status"] = "NOT_PRODUCTION"
    payload["production_release"] = False
    payload["canonical_event_count"] = "UNKNOWN"

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    g07 = gate_record(rollup, "G07")
    g16 = gate_record(rollup, "G16")
    aggregate_review_hits = aggregate.get("review_hits") or []
    if not isinstance(aggregate_review_hits, list):
        aggregate_review_hits = []

    dependency_payload = {
        "schema": "hpfa.coordinate_frame_precondition_dependency_audit",
        "version": "1.0.0",
        "source_role": "ACTIVE_MATCH_EXACT_RUN_AUDIT",
        "runtime_authority": args.runtime_authority,
        "runtime_code_head_sha": args.runtime_head,
        "g07_coordinate_surface_gate": g07,
        "g16_aggregate_derivation_gate": g16,
        "aggregate_definition_alignment_status": aggregate.get("status"),
        "aggregate_definition_alignment_review_hits": aggregate_review_hits,
        "interpretation_rule": "Exact-run upstream evidence is copied for dependency visibility only; it does not override coordinate-frame admission or create metric truth.",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    dependency_out.write_text(
        json.dumps(dependency_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("HPFA COORDINATE FRAME PRECONDITION ACTIVE_MATCH AUDIT")
    for key in (
        "status",
        "module_status",
        "runtime_evidence_status",
        "release_status",
        "runtime_code_head_sha",
        "match_surface_binding_id",
        "coordinate_frame_candidate",
        "expected_team_period_group_count",
        "multi_anchor_pass_group_count",
        "multi_anchor_conflict_group_count",
        "progression_metric_recheck_allowed",
        "hard_block_hits",
        "review_hits",
        "active_match_execution_completed",
        "active_match_evidence_pass",
        "canonical_event_count",
        "production_release",
    ):
        print(f"{key}={payload.get(key)}")
    print(f"g07_coordinate_surface_gate={g07}")
    print(f"g16_aggregate_derivation_gate={g16}")
    print(f"aggregate_definition_alignment_status={aggregate.get('status')}")
    print(f"aggregate_definition_alignment_review_hits={aggregate_review_hits}")
    print(f"dependency_audit_file={dependency_out}")


if __name__ == "__main__":
    main()

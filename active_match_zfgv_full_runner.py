#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import active_match_spine_runner as entrypoint_module
import full_spine_runner
from runtime_authority_split_adapter import validate_split_active_match_authority
from user_output_bundle import snapshot_output_state, write_standard_user_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPFA ZFGV full spine with split product/runtime roots.")
    parser.add_argument("active_match_dir")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--runtime-authority-root", required=True)
    args = parser.parse_args()

    execution_root = Path(args.execution_root).expanduser().resolve(strict=False)
    runtime_authority_root = Path(args.runtime_authority_root).expanduser().resolve(strict=False)

    active_match = validate_split_active_match_authority(
        args.active_match_dir,
        runtime_authority_root,
    )

    entrypoint_module._bind_shared_snapshot_contract()
    entrypoint_module._bind_construct_admission_gate()
    entrypoint_module._bind_metric_governance_prerequisite_chain()
    entrypoint_module._bind_metric_governance_construct_gate()

    original_validator = full_spine_runner.validate_active_match_authority
    full_spine_runner.validate_active_match_authority = (
        lambda path, _execution_root: validate_split_active_match_authority(
            path,
            runtime_authority_root,
        )
    )
    try:
        before_state = snapshot_output_state(args.out_dir)
        result = full_spine_runner.run_full_spine(
            active_match_dir=active_match,
            out_dir=args.out_dir,
            execution_root=execution_root,
        )
        entrypoint_module._normalize_current_surface_evidence(result)
        user_outputs = write_standard_user_outputs(
            args.out_dir,
            result,
            before_state=before_state,
        )
    finally:
        full_spine_runner.validate_active_match_authority = original_validator

    payload = {
        "status": result.get("status"),
        "decision": result.get("decision"),
        "full_spine": True,
        "product_execution_root": str(execution_root),
        "runtime_authority_root": str(runtime_authority_root),
        "active_match": str(active_match),
        "out_json": str(Path(args.out_dir) / "active_match_full_spine_v1.json"),
        "out_txt": str(Path(args.out_dir) / "active_match_full_spine_v1.txt"),
        "analyst_report": user_outputs.get("analyst_report"),
        "bundle_zip": user_outputs.get("bundle_zip"),
        "bundle_manifest": user_outputs.get("bundle_manifest"),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
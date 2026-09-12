from __future__ import annotations

import argparse
import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    build_analyst_output_claim_contract,
)

OUTPUT_NAME = "analyst_output_claim_contract_projection_v1.json"


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def runtime_write_outputs(
    sequence_json: str | Path,
    admission_json: str | Path,
    out_dir: str | Path,
) -> dict:
    sequence_path = Path(sequence_json).expanduser().resolve()
    admission_path = Path(admission_json).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    sequence_payload = _load(sequence_path)
    admission_payload = _load(admission_path)
    if not sequence_payload or not admission_payload:
        result = {
            "status": "FAIL_CLOSED",
            "analyst_output_contracts": [],
            "analyst_output_contract_count": 0,
            "professional_emit_allowed": False,
            "professional_emit_allowed_count": 0,
            "hard_block_hits": ["required_sequence_or_admission_payload_missing_or_invalid"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        result = build_analyst_output_claim_contract(sequence_payload, admission_payload)

    target = output / OUTPUT_NAME
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    result["output"] = str(target)
    result["source_sequence_json"] = str(sequence_path)
    result["source_admission_json"] = str(admission_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA compact Safe Finding admission to analyst-claim micro-gear")
    parser.add_argument("--sequence-json", required=True)
    parser.add_argument("--admission-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    result = runtime_write_outputs(args.sequence_json, args.admission_json, args.out_dir)
    print(json.dumps({
        "status": result.get("status"),
        "analyst_output_contract_count": result.get("analyst_output_contract_count"),
        "safe_finding_admission_decision_counts": result.get("safe_finding_admission_decision_counts") or {},
        "professional_emit_allowed": result.get("professional_emit_allowed"),
        "professional_emit_allowed_count": result.get("professional_emit_allowed_count"),
        "hard_block_hits": result.get("hard_block_hits") or [],
        "review_hits": result.get("review_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "output": result.get("output"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())

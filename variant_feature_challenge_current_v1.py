from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)

FEATURE_DELTA_JSON = "grammar_stable_variant_feature_delta_projection_v1.json"
PROCESS_VARIANT_JSON = "observable_process_variant_binding_projection_v1.json"
OUTPUT_JSON = "variant_feature_challenge_projection_v1.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_input_not_object:{path.name}")
    return payload


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = Path(out_dir).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)

    feature_delta_path = source / FEATURE_DELTA_JSON
    process_variant_path = source / PROCESS_VARIANT_JSON
    missing = [
        path.name
        for path in (feature_delta_path, process_variant_path)
        if not path.is_file()
    ]
    if missing:
        report = {
            "status": "FAIL_CLOSED",
            "variant_feature_challenge_records": [],
            "variant_feature_challenge_record_count": 0,
            "hard_block_hits": ["required_input_missing:" + name for name in sorted(missing)],
            "review_hits": [],
            "projection_creates_new_evidence": False,
            "projection_reconstructs_sequences": False,
            "professional_finding_emit_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }
    else:
        report = build_variant_feature_challenge_projection(
            _load(feature_delta_path),
            _load(process_variant_path),
        )

    (output / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = runtime_write_outputs(args.input_dir, args.out_dir)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())

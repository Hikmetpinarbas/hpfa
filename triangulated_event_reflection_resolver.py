from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "triangulated_event_reflection_resolver_lite" / "src"
    sys.path.insert(0, str(src))
    from triangulated_event_reflection_resolver import write_outputs

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = write_outputs(args.input_dir, args.out_dir, root=root)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "claim_safety": report.get("claim_safety"),
        "surface_row_count": report.get("surface_row_count"),
        "reflection_group_count": report.get("reflection_group_count"),
        "multi_surface_group_count": report.get("multi_surface_group_count"),
        "true_action_count": report.get("true_action_count"),
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

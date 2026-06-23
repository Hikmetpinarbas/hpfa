from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def main() -> int:
    root = repo_root()
    src = root / "hpfa" / "modules" / "core" / "source_conflict_registry_lite" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from source_conflict_registry import write_outputs

    parser = argparse.ArgumentParser(description="HPFA Source Conflict Registry Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    registry = write_outputs(args.input_dir, args.out_dir, root=root)
    print(json.dumps({
        "status": registry.get("status"),
        "claim_safety": registry.get("claim_safety"),
        "source_count": registry.get("source_count"),
        "conflict_count": registry.get("conflict_count"),
        "conflict_class_counts": registry.get("conflict_class_counts"),
        "outputs": registry.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

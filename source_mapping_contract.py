from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def main() -> int:
    root = repo_root()
    src = root / "hpfa" / "modules" / "core" / "source_mapping_contract_lite" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from source_mapping_contract import write_outputs

    parser = argparse.ArgumentParser(description="HPFA Source Mapping Contract Lite V1")
    parser.add_argument("--active-match-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--strict-required", action="store_true")
    args = parser.parse_args()

    audit = write_outputs(args.active_match_dir, args.out_dir, strict_required=args.strict_required, root=root)
    print(json.dumps({
        "status": audit.get("status"),
        "claim_safety": audit.get("claim_safety"),
        "source_count": audit.get("source_count"),
        "mapping_record_count": audit.get("mapping_record_count"),
        "mapped_column_count": audit.get("mapped_column_count"),
        "unmapped_column_count": audit.get("unmapped_column_count"),
        "decision_counts": audit.get("decision_counts"),
        "outputs": audit.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

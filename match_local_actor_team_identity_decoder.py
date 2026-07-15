from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    src = root / "hpfa" / "modules" / "core" / "match_local_actor_team_identity_decoder_lite" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from match_local_actor_team_identity_decoder import write_outputs

    parser = argparse.ArgumentParser(description="HPFA Match-Local Actor and Team Identity Decoder Lite V1")
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result = write_outputs(args.evidence_json, args.out)
    print(json.dumps({
        "decision_state": result.get("decision_state"),
        "team_identity_candidate_count": result.get("team_identity_candidate_count"),
        "actor_identity_candidate_count": result.get("actor_identity_candidate_count"),
        "identity_bound_atom_count": result.get("identity_bound_atom_count"),
        "identity_unresolved_atom_count": result.get("identity_unresolved_atom_count"),
        "canonical_event_count": result.get("canonical_event_count"),
        "production_release": result.get("production_release"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

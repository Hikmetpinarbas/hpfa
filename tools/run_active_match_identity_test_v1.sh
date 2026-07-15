#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HPFA_REPO:-$HOME/hpfa_claim_integrity/hpfa}"
ACTIVE="$REPO/runtime/active_single_match/current"
OUT="/sdcard/Download/HPFA"
EXPECTED_BRANCH="match-local-identity-decoder-lite-v1"

fail() {
  printf 'FAIL: %s\n' "$1" | tee "$OUT/match_local_identity_active_match_v1.txt" >&2
  exit 1
}

mkdir -p "$OUT"
[[ -d "$REPO/.git" ]] || fail "repository_not_found:$REPO"
[[ -d "$ACTIVE" ]] || fail "active_match_runtime_not_found:$ACTIVE"

cd "$REPO"
ACTUAL_BRANCH="$(git branch --show-current)"
ACTUAL_HEAD="$(git rev-parse HEAD)"
[[ "$ACTUAL_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "unexpected_branch:$ACTUAL_BRANCH expected:$EXPECTED_BRANCH"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || fail "tracked_worktree_not_clean"

python -m py_compile \
  hpfa/modules/core/evidence_atom_contract_lite/src/evidence_atom_contract.py \
  hpfa/modules/core/match_local_identity_decoder_lite/src/match_local_identity_decoder.py

python -m pytest -q \
  hpfa/modules/core/evidence_atom_contract_lite/tests/test_evidence_atom_contract.py \
  hpfa/modules/core/match_local_identity_decoder_lite/tests/test_match_local_identity_decoder.py \
  | tee "$OUT/match_local_identity_pytest_v1.txt"

CANONICAL_JSON="${HPFA_CANONICAL_JSON:-}"
if [[ -z "$CANONICAL_JSON" ]]; then
  CANONICAL_JSON="$(find "$ACTIVE" -type f \( -iname '*canonical*.json' -o -iname 'canonical_event_lite*.json' \) | sort | head -n 1 || true)"
fi
[[ -n "$CANONICAL_JSON" && -f "$CANONICAL_JSON" ]] || fail "canonical_json_not_found_set_HPFA_CANONICAL_JSON"

PYTHONPATH="$REPO" python - "$CANONICAL_JSON" "$OUT" "$ACTUAL_HEAD" <<'PY'
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from hpfa.modules.core.evidence_atom_contract_lite.src.evidence_atom_contract import (
    build_evidence_atom_contract,
)
from hpfa.modules.core.match_local_identity_decoder_lite.src.match_local_identity_decoder import (
    build_match_local_identity_decoder,
)

canonical_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
git_head = sys.argv[3]
canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
evidence = build_evidence_atom_contract(canonical)
identity = build_match_local_identity_decoder(evidence)

binding_counts = Counter(
    binding.get("decision_state", "UNKNOWN")
    for binding in identity.get("identity_bindings", [])
)

result = {
    "test_id": "active_match_identity_test_v1",
    "git_head": git_head,
    "canonical_input": str(canonical_path),
    "evidence_decision_state": evidence["decision_state"],
    "identity_decision_state": identity["decision_state"],
    "evidence_atom_count": identity["evidence_atom_count"],
    "team_identity_candidate_count": len(identity["team_identity_candidates"]),
    "actor_identity_candidate_count": len(identity["actor_identity_candidates"]),
    "identity_bound_atom_count": identity["identity_bound_atom_count"],
    "unresolved_atom_count": identity["unresolved_atom_count"],
    "binding_state_counts": dict(sorted(binding_counts.items())),
    "action_bundle_candidate_count": identity["action_bundle_candidate_count"],
    "event_instance_count": identity["event_instance_count"],
    "canonical_event_count": identity["canonical_event_count"],
    "production_release": identity["production_release"],
}

assert result["evidence_atom_count"] > 0
assert result["identity_bound_atom_count"] + result["unresolved_atom_count"] == result["evidence_atom_count"]
assert result["action_bundle_candidate_count"] == 0
assert result["event_instance_count"] == 0
assert result["canonical_event_count"] == "UNKNOWN"
assert result["production_release"] is False

(out_dir / "match_local_identity_active_match_v1.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
summary = [
    "HPFA ACTIVE_MATCH IDENTITY TEST V1",
    *(f"{key}={value}" for key, value in result.items() if key != "binding_state_counts"),
    "binding_state_counts=" + json.dumps(result["binding_state_counts"], ensure_ascii=False, sort_keys=True),
]
(out_dir / "match_local_identity_active_match_v1.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
PY

printf 'PASS: outputs written flat to %s\n' "$OUT"
